
"""app/bot.py — Core FikrFree Assistant logic (RAG over CSVs with Roman Urdu support)."""

from dotenv import load_dotenv
from pathlib import Path
import time, json, random, re
from typing import List, Optional

# LlamaIndex / OpenAI
from llama_index.llms.openai import OpenAI
from llama_index.core import VectorStoreIndex, Settings
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core import SimpleDirectoryReader, StorageContext, load_index_from_storage
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

# --- Load or build the unified index from app/data/*.csv ---
documents = SimpleDirectoryReader("./data").load_data()
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
        "eligibility, and SOPs. If a user asks 'Who are you?' introduce yourself and capabilities.\n\n"
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
                "4) If answer is not in context, say: 'Maazrat, mujhay is barey mein maloomat nahi mili.'\n\n"
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
