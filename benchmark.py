"""Timing benchmark outside Streamlit:  python benchmark.py [repetitions]   (default 3)

Loads the models once, then for Top-K = 3 and Top-K = 5 measures, per question, query embedding, ChromaDB search,
time to first token, generation and total time, and writes benchmark_results.csv and benchmark_answers.txt.
The answer cache is switched off here so every repetition really runs retrieval and generation. Repetition 1 of each
question is a warm-up and is left out of the averages. Compare benchmark_answers.txt for Top-K 3 and 5 by eye before
choosing a value: a faster setting is only better if the answers stay correct and cited."""
import csv
import statistics as stats
import sys
import time

import config

config.ANSWER_CACHE_SIZE = 0          # must be set before the pipeline runs
import rag_pipeline  # noqa: E402

QUESTIONS = [
    "How many tardy marks are equivalent to one absence?",
    "What is the normal retirement age of employees at JRU?",
    "What does the handbook say about attendance?",
    "What is the capital of France?",                      # not in the handbooks: should give the standard reply
]
TOP_KS = (3, 5)


def main(reps=3):
    t0 = time.perf_counter()
    pipe = rag_pipeline.get_pipeline(progress=lambda m: None)
    load = time.perf_counter() - t0
    original_k = pipe.top_k
    print(f"Model loading: {load:.1f} s on {pipe.device} ({pipe.dtype}); max new tokens {config.MAX_NEW_TOKENS}\n")
    rows, answers = [], []
    for k in TOP_KS:
        pipe.top_k = k
        for q in QUESTIONS:
            for r in range(1, reps + 1):
                res = pipe.answer(q)
                t = res["timings"]
                rows.append({"top_k": k, "question": q, "rep": r, "embed_s": t.get("embed", 0), "search_s": t.get("search", 0),
                             "first_token_s": t.get("first_token", 0), "generation_s": t.get("generation", 0),
                             "total_s": t.get("total", 0), "new_tokens": t.get("new_tokens", 0),
                             "prompt_tokens": res.get("prompt_tokens") or 0, "refused": res["refused"]})
                if r == reps:
                    pages = ", ".join(f"{s['handbook']} p.{s['page']}" for s in res["sources"]) or "(no sources)"
                    answers.append(f"[top_k={k}] {q}\n{res['answer']}\nSources: {pages}\n")
    pipe.top_k = original_k
    for k in TOP_KS:
        print(f"Top-K = {k}")
        print(f"  {'Question':50} {'embed':>7} {'search':>7} {'1st tok':>8} {'gen':>7} {'total':>7} {'tokens':>7}")
        for q in QUESTIONS:
            rs = [x for x in rows if x["top_k"] == k and x["question"] == q and x["rep"] > 1] or \
                 [x for x in rows if x["top_k"] == k and x["question"] == q]
            m = lambda key: stats.mean(x[key] for x in rs)
            print(f"  {q[:50]:50} {m('embed_s'):7.3f} {m('search_s'):7.3f} {m('first_token_s'):8.2f} "
                  f"{m('generation_s'):7.2f} {m('total_s'):7.2f} {m('new_tokens'):7.0f}")
        print()
    with open("benchmark_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    with open("benchmark_answers.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(answers))
    print("Saved benchmark_results.csv and benchmark_answers.txt (repetition 1 is the warm-up, excluded from the averages).")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 3)