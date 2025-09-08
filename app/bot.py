
"""app/bot.py — Core FikrFree Assistant logic (RAG over CSVs with Roman Urdu support)."""

from dotenv import load_dotenv
from pathlib import Path
import time, json, random, re
from typing import List, Optional, Dict, Tuple
import pandas as pd

# LlamaIndex / OpenAI
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.memory import ChatMemoryBuffer

# Safety (optional)
from llm_guard import scan_prompt
from llm_guard.input_scanners import Anonymize, PromptInjection, TokenLimit, Toxicity
from llm_guard.vault import Vault

# Embeddings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# Project-specific index init
from app.index_generator import init_indexes

load_dotenv()

# --- Safety setup ---
vault = Vault()  # not used directly but can be wired if needed
input_scanners = [Toxicity(), TokenLimit(), PromptInjection()]

# --- Embedding + LLM configuration ---
Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
llm = OpenAI(model="gpt-4o-mini")
Settings.llm = llm

# --- Load or build the unified index (defer heavy work to index_generator) ---
persist_dir = Path("main_index")
if not persist_dir.exists():
    print("[bot] main_index not found, building …")
    init_indexes()

index = load_index_from_storage(StorageContext.from_defaults(persist_dir=persist_dir))

# --- Memory buffer for chat ---
memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

# --- Lightweight text streaming helper ---
def stream_text(text: str, chunk_size: int = 10):
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]

DEFAULT_RESPONSES = [
    "Hello! How can I help you today?",
    "Hi there! What would you like to know?",
    "Greetings! How can I assist you?",
    "Hello! I'm here to answer your questions. What can I help you with?",
    "Agar aap Roman Urdu mein sawal poochain to main Roman Urdu mein hi jawab doonga.",
]

MAX_MESSAGES = 20
MAX_HISTORY_LENGTH = 2000

conversation_history: Optional[List[ChatMessage]] = None

# --- CSV Catalog (for precise lookups when user specifies variant/product) ---

def _read_csv_robust(csv_path: Path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(csv_path, encoding=enc, sep=None, engine="python")
            if df is not None and df.shape[1] > 0:
                df.columns = [str(c).lstrip("\ufeff").strip() for c in df.columns]
                return df
        except Exception:
            continue
    return None


def _norm(s: str) -> str:
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s()/+]+", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s


VARIANTS = {
    "bronze": "bronze",
    "silver": "silver",
    "gold": "gold",
    "platinum": "platinum",
    "diamond": "diamond",
    "ace": "ace",
    "crown": "crown",
    "default": "default",
}


def _extract_variant(prompt: str) -> Optional[str]:
    p = _norm(prompt)
    for v in VARIANTS.keys():
        if re.search(rf"\b{re.escape(v)}\b", p):
            return v
    return None


def _build_catalog() -> Tuple[Dict[Tuple[str, str], Dict[str, str]], List[str]]:
    catalog: Dict[Tuple[str, str], Dict[str, str]] = {}
    product_names: set = set()
    data_dir = Path("./data")
    for csv_path in data_dir.glob("*.csv"):
        df = _read_csv_robust(csv_path)
        if df is None or df.empty:
            continue
        # Normalize column names we rely on
        cols = {c.lower(): c for c in df.columns}
        get = lambda key: cols.get(key.lower())
        for _, row in df.iterrows():
            product_name = str(row.get(get("ProductName"), "") or "")
            variant = str(row.get(get("Variant"), "") or "")
            if not product_name or not variant:
                continue
            # Create a simple, consistent row dict of strings
            r = {k: ("" if pd.isna(v) else str(v)) for k, v in row.items()}
            key = (_norm(product_name), _norm(variant))
            catalog[key] = r
            product_names.add(product_name)
    return catalog, sorted(product_names)


CATALOG, PRODUCT_NAME_LIST = _build_catalog()


def _best_product_match(prompt: str) -> Optional[str]:
    if not PRODUCT_NAME_LIST:
        return None
    q = set(_norm(prompt).split())
    best = None
    best_score = 0
    for name in PRODUCT_NAME_LIST:
        tokens = set(_norm(name).split())
        if not tokens:
            continue
        inter = len(q & tokens)
        score = inter / max(len(tokens), 1)
        if score > best_score:
            best_score = score
            best = name
    # Heuristic threshold: at least 30% token overlap
    return best if best and best_score >= 0.3 else None


def _lookup_variant_row(product_name: str, variant: str) -> Optional[Dict[str, str]]:
    key = (_norm(product_name), _norm(variant))
    return CATALOG.get(key)


def _format_row_answer(row: Dict[str, str]) -> str:
    po = row.get("ProductOwner", "").strip()
    pn = row.get("ProductName", "").strip()
    variant = row.get("Variant", "").strip()
    pid = (row.get("ProductID", "") or "").strip()
    # Try to find deep link in ProductID field
    m = re.search(r"https?://\S+", pid)
    link = m.group(0) if m else ""

    prepaid = (row.get("PrepaidDaily", "") or "").strip()
    postpaid = (row.get("PostpaidMonthly", "") or "").strip()
    monthly = (row.get("MonthlyPrice", "") or "").strip()
    yearly = (row.get("YearlyPrice", "") or "").strip()
    desc = (row.get("ProductDescription", "") or "").strip()

    benefits = []
    for i in range(1, 6):
        b = (row.get(f"Benefit{i}", "") or "").strip()
        d = (row.get(f"Description{i}", "") or "").strip()
        if b:
            if d:
                benefits.append(f"- {b}: {d}")
            else:
                benefits.append(f"- {b}")

    lines = []
    # Title as heading for emphasis
    lines.append(f"### {pn} — {variant} variant")
    if po:
        lines.append(f"**Provider:** {po}")
    if prepaid or postpaid or monthly or yearly:
        price_bits = []
        if prepaid:
            price_bits.append(f"Prepaid Daily: PKR {prepaid}")
        if postpaid:
            price_bits.append(f"Postpaid Monthly: PKR {postpaid}")
        if monthly:
            price_bits.append(f"Monthly Price: PKR {monthly}")
        if yearly:
            price_bits.append(f"Yearly Price: PKR {yearly}")
        lines.append("**Pricing:** " + "; ".join(price_bits))
    if desc:
        lines.append(f"**Overview:** {desc}")
    if benefits:
        lines.append("**Key Benefits:**")
        lines.extend(benefits[:6])
    if link:
        lines.append(f"**Learn more:** {link}")
    return "\n".join(lines)

def preprocess_prompt(prompt: str) -> str:
    prompt = prompt.strip()
    prompt = " ".join(prompt.split())
    return prompt

# --- Language detection tuned for Roman Urdu vs English ---
def detect_language(text: str) -> str:
    roman_urdu_indicators = [
        "aap","hai","hay","hain","kar","main","yeh","woh","kya","kyun","kab","kahan","kaisa","kitna",
        "mera","tera","hamara","tumhara","unka","iska","uska","nahi","nahin","bilkul","bohot","bahut",
        "thoda","zyada","paani","pani","khana","ghar","kaam","waqt","saal","mahina","din","raat",
        "subah","sham","achha","bura","sundar","khoobsurat","mushkil","aasan","shukriya","maaf",
        "ji","han","haan"
    ]
    text_lower = text.lower()
    words = re.findall(r"\b\w+\b", text_lower)
    if not words:
        return "english"
    ru_count = sum(1 for w in words if w in roman_urdu_indicators)
    en_count = sum(1 for w in words if re.fullmatch(r"[a-z]+", w))
    total = len(words)
    if total <= 6:
        if ru_count >= 1: return "roman_urdu"
        if en_count / max(total,1) > 0.6: return "english"
        return "roman_urdu"
    if ru_count >= 2 and (en_count / total) < 0.7: return "roman_urdu"
    if (en_count / total) > 0.7: return "english"
    return "roman_urdu" if ru_count >= 2 else "english"

def is_roman_urdu(prompt: str) -> bool:
    urdu_words = [
        "kya","kaise","tum","mein","aap","mera","apna","hai","ho","kar","ki","se","ko","ka","raha","rahi",
        "kuch","nahi","haan","acha","theek","batao","kyun","kahan","kon","kaun","par","aur","magar",
    ]
    p = prompt.lower()
    words = re.findall(r"\b\w+\b", p)
    urdu_count = sum(1 for w in words if w in urdu_words)
    en_count = sum(1 for w in words if re.match(r"^[a-z]{3,}$", w) and w not in urdu_words)
    return urdu_count >= 2 and urdu_count > en_count

# --- Use the model itself to translate Roman Urdu to English for retrieval ---
async def translate_to_english(prompt: str):
    instruction = (
        "Translate the following Roman Urdu (Urdu written with English letters) to clear English. "
        "Respond with only the English translation:\n\n" + prompt
    )
    temp_engine = index.as_chat_engine(
        streaming=False,
        chat_mode="condense_plus_context",
        memory=None,
        context_prompt=instruction,
    )
    response = await temp_engine.achat(prompt)
    return response.strip()

# --- Primary chat engines (English default; Roman Urdu enforced when needed) ---
chat_engine = index.as_chat_engine(
    streaming=True,
    chat_mode="condense_plus_context",
    memory=memory,
    context_prompt=(
        "You are FikrFree Assistant, a helpful RAG chatbot for FikrFree (fikrfree.com.pk). "
        "Use the provided documents to answer questions about healthcare plans, insurance coverage, partner platforms "
        "(e.g., OlaDoc, MedIQ, BIMA, EFU, Waada, WedDoc), doctor consultation/booking, telemedicine, claims, pricing, "
        "eligibility, and SOPs. If a user asks 'Who are you?' introduce yourself and capabilities. "
        "Format responses in Markdown: use short headings, bold field labels, and bullet points for lists. Keep links as plain URLs.\n\n"
        "Documents:\n{context_str}\n\n"
        "Instruction: If user asks something relevant that is not in the documents, you can answer provided it is related to insurance, healthcare or FikrFree' "
        "If the user gives a short code or identifier, map it from context if available. Keep answers concise (<=150 words)."
    ),
)

async def chat(prompt: str):
    global conversation_history
    if conversation_history is None:
        conversation_history = []

    try:
        preprocessed_prompt = preprocess_prompt(prompt)
        sanitized_prompt, results_valid, results_score = scan_prompt(
            input_scanners, preprocessed_prompt
        )
        if any(not ok for ok in results_valid.values()):
            response = "We're sorry, but our content safety system has flagged this content as potentially inappropriate or harmful."
            for chunk in stream_text(response):
                yield chunk
            return

        # Language logging (optional prints)
        lang = detect_language(preprocessed_prompt)
        print(f"Detected language: {lang}")

        user_message = ChatMessage(role=MessageRole.USER, content=preprocessed_prompt)
        conversation_history.append(user_message)
        if len(conversation_history) > 8:
            conversation_history[:] = conversation_history[-8:]

        # --- Precise product/variant lookup (CSV-backed) ---
        try:
            variant = _extract_variant(preprocessed_prompt)
            prod = _best_product_match(preprocessed_prompt)
            if variant and prod:
                row = _lookup_variant_row(prod, variant)
                if row:
                    answer = _format_row_answer(row)
                    for chunk in stream_text(answer):
                        yield chunk
                    conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=answer))
                    print("Response source: CSV catalog (exact match)")
                    return
        except Exception:
            pass

        # --- Roman Urdu flow ---
        if is_roman_urdu(preprocessed_prompt):
            translated_query = await translate_to_english(preprocessed_prompt)
            nodes = index.as_query_engine(similarity_top_k=3).retrieve(translated_query)
            if not nodes or all(not n.get_content().strip() for n in nodes):
                response = "Maazrat, mujhay is barey mein maloomat nahi mili."
                for chunk in stream_text(response):
                    yield chunk
                conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=response))
                print("Response language: Roman Urdu")
                return

            ru_prompt = (
                "You are FikrFree Assistant. The user asked in Roman Urdu (English letters). "
                "INSTRUCTIONS:\n"
                "1) Respond ONLY in Roman Urdu using A–Z letters.\n"
                "2) No Urdu script.\n"
                "3) Keep it natural and concise (<=150 words).\n"
                "4) Format in Markdown: short headings, bold labels, and bullet points.\n"
                "5) If answer is not in context, say: 'Maazrat, mujhay is barey mein maloomat nahi mili.'\n\n"
                "Context:\n{context_str}\n"
            )
            ru_engine = index.as_chat_engine(
                streaming=True,
                chat_mode="condense_plus_context",
                memory=memory,
                context_prompt=ru_prompt,
            )
            stream = await ru_engine.astream_chat(preprocessed_prompt)
            full = ""
            async for t in stream.async_response_gen():
                full += t
                yield t
            conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=full.strip()))
            print("Response language: Roman Urdu")
            return

        # --- English flow ---
        nodes = index.as_query_engine(similarity_top_k=3).retrieve(preprocessed_prompt)
        if not nodes or all(not n.get_content().strip() for n in nodes):
            response = "Sorry, I don't have that information."
            for chunk in stream_text(response):
                yield chunk
            conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=response))
            print("Response language: English")
            return

        stream = await chat_engine.astream_chat(prompt)
        full = ""
        async for t in stream.async_response_gen():
            full += t
            yield t
        conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=full.strip()))
        print("Response language: English")

    except Exception as e:
        yield f"Error processing your request: {e}"
