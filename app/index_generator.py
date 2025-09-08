# app/index_generator.py

from pathlib import Path
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage, Document
import pandas as pd
import re
from typing import Optional, List

def _read_csv_robust(csv_path: Path):
    """Try encodings + sniff delimiter; return DataFrame or None.

    Also strips BOM from the first column name if present and trims header whitespace.
    """
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    for enc in encodings:
        try:
            # sep=None with engine='python' lets pandas sniff commas/semicolons/tabs
            df = pd.read_csv(csv_path, encoding=enc, sep=None, engine="python")
            if df is not None and df.shape[1] > 0:
                # Normalize/clean column names
                df.columns = [str(c).lstrip("\ufeff").strip() for c in df.columns]
                return df
        except Exception:
            continue
    print(f"Failed to load file {csv_path} with error: No columns to parse from file. Skipping...")
    return None

def _extract_product_id(value: str) -> Optional[str]:
    if not isinstance(value, str):
        return None
    m = re.search(r"\b(\d{1,6})\b", value)
    return m.group(1) if m else None


def _extract_deep_link(value: str) -> Optional[str]:
    if not isinstance(value, str):
        return None
    m = re.search(r"https?://\S+", value)
    return m.group(0) if m else None


def csv_to_documents(csv_path):
    df = _read_csv_robust(Path(csv_path))
    if df is None or df.shape[1] == 0 or df.shape[0] == 0:
        return []
    docs: List[Document] = []
    for i, row in df.iterrows():
        # Build a clean content dict for readability in retrieval
        content = {k: ("" if pd.isna(v) else str(v)) for k, v in row.items()}

        # Rich metadata for targeted retrieval
        product_id_raw = content.get("ProductID", "")
        metadata = {
            "source": Path(csv_path).name,
            "row": int(i),
            "product_owner": content.get("ProductOwner", ""),
            "product_name": content.get("ProductName", ""),
            "variant": content.get("Variant", ""),
            "product_id": _extract_product_id(product_id_raw) or "",
            "deep_link": _extract_deep_link(product_id_raw) or "",
        }

        docs.append(Document(text=str(content), metadata=metadata))
    return docs

def get_index(data, index_name):
    index_dir = Path(index_name)
    if index_dir.exists():
        print(f"[index-generator] index {index_name} exists. Rebuilding …")
        for f in index_dir.glob("*"):
            f.unlink()
    else:
        print(f"[index-generator] building index {index_name}")
    index = VectorStoreIndex.from_documents(data, show_progress=True)
    index.storage_context.persist(persist_dir=index_name)
    return index

def generate_indexes(csv_path):
    path = Path(csv_path)
    if not path.exists() or path.suffix.lower() != ".csv":
        print(f"[index-generator] {csv_path} not found or not a CSV file.")
        return None
    docs = csv_to_documents(path)
    if not docs:
        print(f"[index-generator] {path.name} produced no documents; skipped.")
        return None
    print(f"[index-generator] loaded: {path.name} ({len(docs)} rows)")
    index_name = path.stem + "_index"
    return get_index(docs, index_name)

def _dir_latest_mtime(path: Path) -> float:
    if not path.exists():
        return 0.0
    mtimes = [f.stat().st_mtime for f in path.glob("**/*") if f.is_file()]
    return max(mtimes) if mtimes else 0.0


def init_indexes() -> None:
    """Build or refresh a unified index from all CSVs in ./data into main_index/.

    Rebuilds if the index is missing or any CSV is newer than the persisted index.
    """
    data_dir = Path("./data").resolve()
    persist_dir = Path("main_index")

    csv_paths = list(data_dir.glob("*.csv"))
    if not csv_paths:
        print("[index-generator] No CSV files found under ./data — skipping.")
        return

    latest_csv_mtime = max(p.stat().st_mtime for p in csv_paths)
    latest_index_mtime = _dir_latest_mtime(persist_dir)

    if persist_dir.exists() and latest_index_mtime >= latest_csv_mtime:
        print("[index-generator] index up-to-date → nothing to rebuild.")
        return

    print(f"[index-generator] building unified index from {len(csv_paths)} CSV files …")
    all_docs = []
    for p in csv_paths:
        docs = csv_to_documents(p)
        if docs:
            all_docs.extend(docs)
            print(f"[index-generator] loaded: {p.name} ({len(docs)} rows)")
        else:
            print(f"[index-generator] warning: no usable rows in {p.name}")

    if not all_docs:
        print("[index-generator] No data found in any CSVs, skipping index creation.")
        return

    # Clean existing dir (if any) to avoid stale shards
    if persist_dir.exists():
        for f in persist_dir.glob("*"):
            try:
                f.unlink()
            except Exception:
                pass

    index = VectorStoreIndex.from_documents(all_docs, show_progress=True)
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"[index-generator] index saved to {persist_dir}/")

def load_index() -> VectorStoreIndex:
    persist_dir = Path("main_index")
    if not persist_dir.exists():
        print("[index-generator] No index found. Building now …")
        init_indexes()
    return load_index_from_storage(StorageContext.from_defaults(persist_dir=persist_dir))

if __name__ == "__main__":
    init_indexes()
