
import faiss
from sentence_transformers import SentenceTransformer
import json

def init_cache():
    # Embedding dim for all-mpnet-base-v2 is 768
    d = 768
    M = 16
    efConstruction = 100

    index = faiss.IndexHNSWFlat(d, M, faiss.METRIC_L2)
    index.hnsw.efConstruction = efConstruction

    encoder = SentenceTransformer("all-mpnet-base-v2")

    json_file = "cache_file.json"
    try:
        with open(json_file, "r") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {"questions": [], "embeddings": [], "answers": [], "response_text": []}

    return index, encoder, cache

def retrieve_cache(json_file):
    try:
        with open(json_file, "r") as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {"questions": [], "embeddings": [], "answers": [], "response_text": []}
    return cache

def store_cache(json_file, cache):
    with open(json_file, "w") as f:
        json.dump(cache, f)
