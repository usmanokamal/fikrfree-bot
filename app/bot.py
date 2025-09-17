
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

def _trim(s: str, n: int = 140) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"

def _format_sources(nodes) -> str:
    """Return a simple list of links only, deduplicated."""
    if not nodes:
        return ""
    links = []
    seen = set()
    for n in nodes:
        md = getattr(n, "metadata", None) or {}
        link = (md.get("deep_link") or "").strip()
        if link and link not in seen:
            seen.add(link)
            links.append(link)
        if len(links) >= 5:
            break
    if not links:
        return ""
    lines = ["**Sources:**"]
    lines.extend(f"- {u}" for u in links)
    return "\n".join(lines)

def _style_tail(ctas: bool = True, disclaimer: bool = True) -> str:
    bits = []
    if ctas:
        bits.append("\n**Next:** Compare plans | Start quote")
    if disclaimer:
        bits.append("\n**Disclaimer:** Information is for guidance only; benefits depend on policy terms and insurer approval.")
    return "".join(bits)

def _is_emergency(text: str) -> bool:
    t = text.lower()
    keywords = ["emergency", "bleeding", "heart attack", "stroke", "unconscious", "ambulance", "choking", "severe pain"]
    return any(k in t for k in keywords)

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
    # Preserve newlines so explicit compare lists survive processing
    if prompt is None:
        return ""
    p = str(prompt).replace("\r\n", "\n").replace("\r", "\n")
    # Normalize spaces per line but keep line breaks
    lines = [" ".join(line.split()) for line in p.split("\n")]
    return "\n".join(lines).strip()

# --- Shortlist intent helpers ---
def _parse_budget(text: str) -> Optional[float]:
    m = re.search(r"(?:pkr|rs\.?|rupees)?\s*([\d,.]{3,})\s*(?:per\s*month|monthly|/mo|mo)?", text, flags=re.I)
    if not m:
        return None
    try:
        val = float(m.group(1).replace(",", ""))
        # Heuristic: if value likely daily (< 200), convert to monthly
        if val < 200:
            return val * 30
        return val
    except Exception:
        return None

def _price_monthly_from_row(row: Dict[str, str]) -> Optional[float]:
    def _num(s: str) -> Optional[float]:
        s = (s or "").strip()
        if not s:
            return None
        m = re.search(r"([\d,.]+)", s)
        if not m:
            return None
        try:
            return float(m.group(1).replace(",", ""))
        except Exception:
            return None
    monthly = _num(row.get("MonthlyPrice", ""))
    if monthly:
        return monthly
    postpaid = _num(row.get("PostpaidMonthly", ""))
    if postpaid:
        return postpaid
    prepaid_daily = _num(row.get("PrepaidDaily", ""))
    if prepaid_daily:
        return prepaid_daily * 30
    return None

def _collect_candidates(budget: Optional[float]=None, max_items: int=3) -> List[Dict[str, str]]:
    items = []
    for (pn_norm, variant_norm), row in CATALOG.items():
        price = _price_monthly_from_row(row)
        if price is None:
            continue
        row_copy = dict(row)
        row_copy["_price_monthly"] = price
        items.append(row_copy)
    if not items:
        return []
    if budget:
        # Rank by closeness to budget, prefer <= budget
        def score(r):
            p = r["_price_monthly"]
            penalty = 0 if p <= budget else 0.2  # small penalty if above budget
            return abs(p - budget) + penalty * budget
        items.sort(key=score)
    else:
        items.sort(key=lambda r: r["_price_monthly"])  # low to high
    # Deduplicate by product+variant (already unique) and take top
    return items[:max_items]

def _format_shortlist_table(rows: List[Dict[str, str]]) -> str:
    if not rows:
        return "Sorry, I couldn't find plans to recommend right now."
    lines = []
    lines.append("### Recommended Plans")
    lines.append("| Plan | Variant | Monthly (PKR) | Highlight |")
    lines.append("|---|---:|---:|---|")
    for r in rows:
        plan = (r.get("ProductName", "").strip() or "–")
        variant = (r.get("Variant", "").strip() or "–")
        price = int(round(r.get("_price_monthly", 0)))
        hi = (r.get("Benefit1", "").strip() or r.get("Description1", "").strip() or "–")
        lines.append(f"| {plan} | {variant} | {price:,} | {hi} |")
    lines.append("")
    lines.append("**Why these:** Based on your prompt and pricing signals.")
    lines.append("**Disclaimer:** Estimated pricing; confirm details before purchase.")
    lines.append("\n**Refine:** Tell me your city, dependents, and monthly budget to tailor suggestions.")
    # Add links
    links = []
    for r in rows:
        pid = (r.get("ProductID", "") or "")
        m = re.search(r"https?://\S+", pid)
        link = m.group(0) if m else ""
        if link:
            links.append(f"- {r.get('ProductName','').strip()} {r.get('Variant','').strip()}: {link}")
    if links:
        lines.append("\n**Learn more:**\n" + "\n".join(links))
    return "\n".join(lines)

def _looks_like_shortlist_intent(prompt: str) -> bool:
    p = prompt.lower()
    # Show shortlist (3+) for explicit recommendation or generic plan discovery
    keywords = [
        "recommend", "suggest", "shortlist", "best plan",
        "within", "under", "budget", "plans", "plan", "insurance plans",
        "options", "packages"
    ]
    return any(k in p for k in keywords)

def _find_row_fuzzy(product_hint: str, variant_hint: str) -> Optional[Dict[str, str]]:
    """Lightweight fuzzy lookup used by suggestion flow."""
    pnorm = _norm(product_hint)
    vnorm = _norm(variant_hint.replace("plan", "").strip()) if variant_hint else ""
    # exact product
    product_rows = [(var, row) for (p, var), row in CATALOG.items() if p == pnorm]
    if not product_rows:
        best = _best_product_match(product_hint)
        if not best:
            return None
        pnorm = _norm(best)
        product_rows = [(var, row) for (p, var), row in CATALOG.items() if p == pnorm]
        if not product_rows:
            return None
    # prefer requested variant, else pick cheapest
    for var, row in product_rows:
        if vnorm and var == vnorm:
            return row
    best_row, best_price = None, None
    for var, row in product_rows:
        price = _price_monthly_from_row(row) or 0
        if best_row is None or price < best_price:
            best_row, best_price = row, price
    return best_row

def _suggest_alternative(product_name: str, variant: str) -> Optional[Dict[str, str]]:
    """Suggest an alternative row: next variant in same product, else closest price from another product."""
    base = _find_row_fuzzy(product_name, variant)
    if not base:
        return None
    pn = (base.get("ProductName") or "").strip()
    cur_var = _norm(base.get("Variant") or variant)
    cur_price = _price_monthly_from_row(base) or 0
    # Same product variants sorted by price
    variants = [(var, row) for (p, var), row in CATALOG.items() if p == _norm(pn)]
    variants = [(var, row, _price_monthly_from_row(row) or 0) for var, row in variants]
    higher = sorted([r for r in variants if r[2] > cur_price], key=lambda x: x[2])
    lower = sorted([r for r in variants if r[2] < cur_price], key=lambda x: -x[2])
    for var, row, price in higher + lower:
        if var != cur_var:
            return row
    # Otherwise, pick nearest price from another product
    best_row, best_gap = None, 1e9
    for (p, var), row in CATALOG.items():
        if p == _norm(pn):
            continue
        price = _price_monthly_from_row(row)
        if price is None:
            continue
        gap = abs(price - cur_price)
        if gap < best_gap:
            best_row, best_gap = row, gap
    return best_row

def _dominant_product_from_nodes(nodes) -> Optional[str]:
    counts: Dict[str, int] = {}
    for n in nodes or []:
        name = (getattr(n, 'metadata', None) or {}).get('product_name') or ''
        name = str(name).strip()
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    if not counts:
        return None
    # Return the most frequent product name
    return max(counts.items(), key=lambda kv: kv[1])[0]

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
        "Format responses in Markdown: use short headings, bold field labels, and bullet points for lists. Keep links as plain URLs. "
        "When listing or recommending plans, ALWAYS include the product name and variant together in the form '{ProductName} — {Variant}'. Avoid listing variants alone.\n\n"
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

        # --- Suggestion trigger (from UI) ---
        try:
            if preprocessed_prompt.startswith("SUGGEST_ALTERNATIVE:"):
                m = re.search(r"SUGGEST_ALTERNATIVE:\s*(.+?)\s*[—-]\s*(Bronze|Silver|Gold|Platinum|Diamond|Ace|Crown|Default)\b", preprocessed_prompt, flags=re.I)
                if m:
                    prod = m.group(1).strip()
                    var = m.group(2).strip()
                    alt = _suggest_alternative(prod, var)
                    if alt:
                        answer = "### Suggested Alternative\n" + _format_row_answer(alt) + _style_tail(ctas=True, disclaimer=True)
                    else:
                        answer = "Sorry, I couldn't find a similar alternative right now."
                    for chunk in stream_text(answer):
                        yield chunk
                    return
        except Exception:
            pass

        # --- Precise product/variant lookup (CSV-backed) ---
        try:
            variant = _extract_variant(preprocessed_prompt)
            prod = _best_product_match(preprocessed_prompt)
            if variant and prod:
                row = _lookup_variant_row(prod, variant)
                if row:
                    answer = _format_row_answer(row) + _style_tail(ctas=True, disclaimer=True)
                    for chunk in stream_text(answer):
                        yield chunk
                    conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=answer))
                    print("Response source: CSV catalog (exact match)")
                    return
        except Exception:
            pass

        # --- Shortlist/compare intent ---
        try:
            if _is_emergency(preprocessed_prompt):
                resp = (
                    "This sounds urgent. Please call 1122 immediately or go to the nearest emergency department. "
                    "I’ll pause here to keep you safe."
                )
                for chunk in stream_text(resp):
                    yield chunk
                return
            if _looks_like_shortlist_intent(preprocessed_prompt):
                # If explicit list of plans is provided (Compare button), honor it
                explicit = _parse_explicit_plan_list(preprocessed_prompt)
                if explicit:
                    candidates = _collect_by_explicit_list(explicit)
                    if not candidates:
                        # fall back to generic scoring
                        budget = _parse_budget(preprocessed_prompt)
                        max_items = 5 if re.search(r"monthly\s+plans?|per\s*month", preprocessed_prompt, flags=re.I) else 3
                        candidates = _collect_candidates(budget=budget, max_items=max_items)
                else:
                    budget = _parse_budget(preprocessed_prompt)
                    # If user asked broadly for monthly plans, show more rows
                    max_items = 5 if re.search(r"monthly\s+plans?|per\s*month", preprocessed_prompt, flags=re.I) else 3
                    candidates = _collect_candidates(budget=budget, max_items=max_items)
                answer = _format_shortlist_table(candidates) + _style_tail(ctas=True, disclaimer=True)
                for chunk in stream_text(answer):
                    yield chunk
                conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=answer))
                print("Response type: Shortlist")
                return
        except Exception as e:
            # Fail open to general flow
            print(f"Shortlist intent error: {e}")

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
                "5) When listing or recommending plans, ALWAYS include the product name and variant together in the form '{ProductName} — {Variant}'.\n"
                "6) If answer is not in context, say: 'Maazrat, mujhay is barey mein maloomat nahi mili.'\n\n"
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
            # Append product + sources + tail after answer
            # If the answer lists variants but not product, add a product line
            dom = _dominant_product_from_nodes(nodes)
            if dom:
                tail_prod = f"\n\n**Product:** {dom}"
                for chunk in stream_text(tail_prod):
                    yield chunk
            src_block = _format_sources(nodes)
            if src_block:
                for chunk in stream_text("\n\n" + src_block):
                    yield chunk
            for chunk in stream_text(_style_tail(ctas=True, disclaimer=True)):
                yield chunk
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
        # Append product + sources + tail after answer
        dom = _dominant_product_from_nodes(nodes)
        if dom:
            tail_prod = f"\n\n**Product:** {dom}"
            for chunk in stream_text(tail_prod):
                yield chunk
        src_block = _format_sources(nodes)
        if src_block:
            for chunk in stream_text("\n\n" + src_block):
                yield chunk
        for chunk in stream_text(_style_tail(ctas=True, disclaimer=True)):
            yield chunk
        conversation_history.append(ChatMessage(role=MessageRole.SYSTEM, content=full.strip()))
        print("Response language: English")

    except Exception as e:
        yield f"Error processing your request: {e}"
