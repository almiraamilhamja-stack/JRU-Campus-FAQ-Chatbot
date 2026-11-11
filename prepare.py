"""One-time setup, run from the terminal BEFORE the first demo:  python prepare.py

It downloads the two models (shows progress), builds the ChromaDB index, loads Qwen, and answers one test question
outside Streamlit, printing the time of every stage. If this finishes, the web app will not hang on the first question,
because the models are then in the local cache and the index already exists."""
import time

import config
import rag_pipeline
import vector_store


def main():
    t0 = time.perf_counter()
    print(f"Embedding model : {config.EMBEDDING_MODEL}\nLanguage model  : {config.LLM_MODEL}\n")
    pipe = rag_pipeline.get_pipeline(progress=lambda m: print("  " + m, flush=True))
    print("\nLoad times (s):", {k: round(v, 1) for k, v in pipe.load_times.items()})
    idx = vector_store.index_status()
    print(f"Index: {idx['state']}, {idx['chunks']} chunks, device {pipe.device} ({pipe.dtype}), top-k {pipe.top_k}")
    q = "How many tardy marks are equivalent to one absence?"
    print(f"\nTest question: {q}")
    res = pipe.answer(q)
    print("Answer :", res["answer"])
    print("Sources:", [(s["handbook"], s["page"]) for s in res["sources"]])
    print("Timings:", {k: round(v, 2) for k, v in res["timings"].items() if isinstance(v, float)})
    print(f"\nDone in {time.perf_counter() - t0:.0f} s. You can now run: streamlit run app.py")


if __name__ == "__main__":
    main()
