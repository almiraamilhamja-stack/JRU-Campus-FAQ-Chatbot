"""ChromaDB initialization, rebuilding, and retrieval. The index is persisted in chroma_db/ and is only rebuilt
when the documents or chunk settings change (or when a rebuild is requested), never on every message."""
import json
import threading
import time
from datetime import datetime

import config
from document_loader import list_pdf_files, fingerprint_files, load_documents, split_documents

MANIFEST = config.CHROMA_DIR / "manifest.json"
_lock = threading.Lock()
_embeddings = None
_store = None


def current_signature():
    files = list_pdf_files()
    return {"documents": fingerprint_files(files) if files else None, "chunk_size": config.CHUNK_SIZE,
            "chunk_overlap": config.CHUNK_OVERLAP, "embedding_model": config.EMBEDDING_MODEL,
            "collection": config.COLLECTION_NAME}


def _read_manifest():
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        return None


def index_status():
    """Cheap status check (does not load any model): missing, stale, or ready."""
    m = _read_manifest()
    sig = current_signature()
    if sig["documents"] is None:
        return {"state": "no_documents", "chunks": 0, "built_at": None}
    if not m:
        return {"state": "missing", "chunks": 0, "built_at": None}
    if m.get("signature") != sig:
        return {"state": "stale", "chunks": m.get("chunks", 0), "built_at": m.get("built_at")}
    return {"state": "ready", "chunks": m.get("chunks", 0), "built_at": m.get("built_at")}


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        import torch
        from langchain_huggingface import HuggingFaceEmbeddings
        device = "cuda" if torch.cuda.is_available() and config.DEVICE_MAP != "cpu" else "cpu"
        from langchain_core.embeddings import Embeddings
        inner = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL, model_kwargs={"device": device})

        class TimedEmbeddings(Embeddings):
            """Delegates to the real embedding model and records how long the last query embedding took."""
            def __init__(self, wrapped):
                self.inner, self.query_seconds = wrapped, 0.0
            def embed_documents(self, texts):
                return self.inner.embed_documents(texts)
            def embed_query(self, text):
                t0 = time.perf_counter()
                vec = self.inner.embed_query(text)
                self.query_seconds = time.perf_counter() - t0
                return vec

        _embeddings = TimedEmbeddings(inner)
    return _embeddings


def _open_store():
    from langchain_chroma import Chroma
    return Chroma(collection_name=config.COLLECTION_NAME, persist_directory=str(config.CHROMA_DIR),
                  embedding_function=get_embeddings())


def rebuild_index(progress=None):
    """Re-read the PDFs, re-chunk, re-embed, and replace the Chroma collection."""
    global _store
    from langchain_chroma import Chroma
    with _lock:
        if progress: progress("Reading PDF documents...")
        documents, problems = load_documents()
        if progress: progress(f"Splitting {len(documents)} pages into chunks...")
        chunks = split_documents(documents, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
        if progress: progress(f"Embedding {len(chunks)} chunks (this can take a while on a CPU)...")
        try:
            _open_store().delete_collection()
        except Exception:
            pass
        _store = Chroma.from_documents(documents=chunks, embedding=get_embeddings(),
                                       collection_name=config.COLLECTION_NAME,
                                       persist_directory=str(config.CHROMA_DIR))
        MANIFEST.write_text(json.dumps({"signature": current_signature(), "chunks": len(chunks),
                                        "built_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                        "problems": problems}), encoding="utf-8")
        return {"chunks": len(chunks), "problems": problems}


def ensure_index(progress=None):
    """Open the persistent index, building it first when it is missing or out of date."""
    global _store
    with _lock:
        status = index_status()["state"]
    if status == "no_documents":
        raise FileNotFoundError("No PDF reference documents are available. Add a PDF to the data folder.")
    if status in ("missing", "stale"):
        rebuild_index(progress)
    with _lock:
        if _store is None:
            _store = _open_store()
        return _store


def retrieve_timed(query: str, k: int):
    """Return ([(Document, relevance in [0,1] or None)], {"embed": s, "search": s}). The persistent index is opened
    once and reused: no fingerprinting, no rebuild and no model reload happens per question."""
    store = _store if _store is not None else ensure_index()
    emb = get_embeddings()
    t0 = time.perf_counter()
    try:
        pairs = [(d, float(s)) for d, s in store.similarity_search_with_relevance_scores(query, k=k)]
    except Exception:                                       # score function unavailable: plain similarity search
        pairs = [(d, None) for d in store.similarity_search(query, k=k)]
    total = time.perf_counter() - t0
    embed = min(getattr(emb, "query_seconds", 0.0), total)
    return pairs, {"embed": embed, "search": total - embed}


def retrieve(query: str, k: int):
    return retrieve_timed(query, k)[0]
