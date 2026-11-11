"""Logic tests that run without Streamlit, PyTorch, or model downloads (python selftest.py).
They cover authentication, per-user chat history, FAQ evidence, page mapping, prompt/answer post-processing,
the answer flow with a stand-in model, and upload validation. They do NOT test the Streamlit screens or the
real Qwen/ChromaDB pipeline; use TESTING.md for those."""
import os, sys, tempfile, types

os.environ["JRU_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
import auth, chat_history, config, document_loader, faq_data, rag_pipeline, vector_store

passed = 0
def check(name, cond):
    global passed
    print(("PASS " if cond else "FAIL "), name)
    if not cond: sys.exit(1)
    passed += 1

# ---- auth
check("student login works", auth.verify_credentials("2024-00001", "Student@2026")["role"] == "Student")
check("employee login works", auth.verify_credentials("E-0001", "Employee@2026")["role"] == "Employee")
check("wrong password rejected", auth.verify_credentials("2024-00001", "wrong") is None)
check("unknown user rejected", auth.verify_credentials("nobody", "Student@2026") is None)
check("empty input rejected", auth.verify_credentials("", "") is None)
src = open("auth.py").read()
check("no plain-text demo password in auth.py", "Student@2026" not in src and "Employee@2026" not in src)
check("lock-out after 5 failures", auth.lockout_remaining(5, 1000.0, now=1010.0) == 50)
check("no lock-out before 5 failures", auth.lockout_remaining(4, 1000.0, now=1010.0) == 0)
check("lock-out expires", auth.lockout_remaining(5, 1000.0, now=1100.0) == 0)

# ---- chat history isolation
chat_history.init_db()
a = chat_history.create_conversation("2024-00001", "Attendance question")
chat_history.add_message("2024-00001", a, "user", "What is the attendance rule?")
chat_history.add_message("2024-00001", a, "assistant", "Regular attendance.", [{"handbook": "H", "page": 13}])
msgs = chat_history.get_messages("2024-00001", a)
check("messages stored with sources", len(msgs) == 2 and msgs[1]["sources"][0]["page"] == 13)
check("other user cannot read", chat_history.get_messages("E-0001", a) == [])
try:
    chat_history.add_message("E-0001", a, "user", "intrusion"); ok = False
except PermissionError:
    ok = True
check("other user cannot write", ok)
chat_history.delete_conversation("E-0001", a)
check("other user cannot delete", len(chat_history.list_conversations("2024-00001")) == 1)
chat_history.clear_conversation("2024-00001", a)
check("clear removes messages", chat_history.get_messages("2024-00001", a) == [])
chat_history.delete_conversation("2024-00001", a)
check("owner can delete", chat_history.list_conversations("2024-00001") == [])
chat_history.set_preference("E-0001", "font_size", "Large")
check("preferences persist", chat_history.get_preference("E-0001", "font_size") == "Large")
check("SQL injection text stored literally", chat_history.create_conversation("x'); DROP TABLE messages;--", "t") > 0)
check("tables survive", len(chat_history.list_conversations("2024-00001")) == 0)

# ---- documents and FAQ
check("page mapping: student page 13", document_loader.handbook_for_page(config.COMBINED_PDF_NAME, 13) == (config.STUDENT_HANDBOOK, 13))
check("page mapping: faculty pdf 82 -> page 40", document_loader.handbook_for_page(config.COMBINED_PDF_NAME, 82) == (config.FACULTY_HANDBOOK, 40))
check("page mapping: boundary 42/43", document_loader.handbook_for_page(config.COMBINED_PDF_NAME, 42)[0] == config.STUDENT_HANDBOOK
      and document_loader.handbook_for_page(config.COMBINED_PDF_NAME, 43)[0] == config.FACULTY_HANDBOOK)
import subprocess
check("FAQ evidence verified against the PDF", subprocess.run([sys.executable, "verify_faq.py"], capture_output=True).returncode == 0)
check("every FAQ category is valid", {f["category"] for f in faq_data.get_faqs()} <= set(config.CATEGORIES))
pdf = (config.DATA_DIR / config.COMBINED_PDF_NAME).read_bytes()
check("valid PDF upload accepted", document_loader.validate_upload("handbook.pdf", pdf)[0])
check("non-PDF upload rejected", not document_loader.validate_upload("x.exe", b"MZ")[0])
check("fake PDF rejected", not document_loader.validate_upload("x.pdf", b"not a pdf")[0])
check("path traversal name sanitized", document_loader.validate_upload("../../evil.pdf", pdf)[2] == "evil.pdf")
check("index status reports missing before build", vector_store.index_status()["state"] in ("missing", "stale", "ready"))

# ---- assets served from static/
check("hero, login photo and seal exist in static/", all(config.static_url(n) for n in ("jru_campus_hero.jpg", "jru_campus_login.jpg", "jru_logo.png")))
check("missing asset gives None (graceful fallback)", config.static_url("nope.png") is None)
check("static serving enabled", "enableStaticServing = true" in open(".streamlit/config.toml").read())
check("four home cards and four popular questions", len(config.HOME_CARDS) == 4 and len(config.POPULAR_QUESTIONS) == 4)
check("no base64 image embedded in styles or app", "base64," not in open("app.py").read().replace("data:image/svg","") )

# ---- prompt and post-processing
check("smalltalk detected", rag_pipeline.is_smalltalk("Hello!") and not rag_pipeline.is_smalltalk("What is the retirement age?"))
hist = [{"role": "user", "content": "How many tardy marks equal an absence?"}, {"role": "assistant", "content": "Three."}]
check("follow-up gets previous question", "tardy" in rag_pipeline.compose_retrieval_query("what about faculty?", hist))
check("long question not rewritten", rag_pipeline.compose_retrieval_query("What is the normal retirement age of employees at JRU?", hist).startswith("What is the normal"))
check("refusal phrase normalized", rag_pipeline.postprocess_answer("The documents do not provide a sufficient answer.") == config.REFUSAL_MESSAGE)
check("empty answer becomes refusal", rag_pipeline.postprocess_answer("  ") == config.REFUSAL_MESSAGE)
cut = rag_pipeline.postprocess_answer("First point is complete and long enough to keep here. Second point is cut off mid sen", True)
check("cut-off answer trimmed to a full sentence", cut.endswith("keep here."))
check("complete answer untouched", rag_pipeline.postprocess_answer("Retirement is at sixty.") == "Retirement is at sixty.")
class Tok:
    chat_template = None
tp = rag_pipeline.build_prompt(Tok(), "Q?", "CTX", hist)
check("prompt has history, context, question and refusal rule", all(s in tp for s in ("CONVERSATION SO FAR", "CONTEXT:", "QUESTION:", config.REFUSAL_MESSAGE)))

# ---- answer flow with stand-ins (no model, no ChromaDB)
import threading, time
class Doc:
    def __init__(s, text, page): s.page_content, s.metadata = text, {"source": "x.pdf", "handbook": config.STUDENT_HANDBOOK, "handbook_page": page, "pdf_page": page}
vector_store.retrieve_timed = lambda q, k: ([(Doc("A student is required to attend classes regularly.", 13), 0.8),
                                             (Doc("same page again", 13), 0.7), (Doc("other page", 14), 0.6)],
                                            {"embed": 0.01, "search": 0.02})
class FakeTok:
    chat_template = None
    def __call__(s, t, return_tensors=None): return {"input_ids": list(range(len(str(t).split())))}
class FakePipeline(rag_pipeline.RAGPipeline):
    """Skips model loading; _generate streams canned pieces (or hangs/fails on request)."""
    def __init__(self, mode="ok"):
        self.tokenizer, self.top_k, self.device, self.dtype, self.mode, self.load_times = FakeTok(), 3, "cpu", "float32", mode, {"total": 0}
    def _generate(self, prompt, cancel):
        if self.mode == "fail":
            raise RuntimeError("simulated generation failure")
        if self.mode == "stall":
            raise TimeoutError("simulated stall")
        for piece in ("Students must attend ", "classes regularly ", "and punctually."):
            if cancel.is_set(): return
            time.sleep(0.02)
            yield piece
p = FakePipeline()
events = list(p.answer_stream("What does the handbook say about attendance?", []))
check("stream emits stage, tokens and done", [e[0] for e in events][:2] == ["stage", "stage"] and events[-1][0] == "done"
      and sum(e[0] == "token" for e in events) == 3)
res = events[-1][1]
check("answer returned", "regularly" in res["answer"] and not res["refused"])
check("sources deduplicated by page", [s["page"] for s in res["sources"]] == [13, 14])
check("timings recorded (embed, search, generation, total)", all(k in res["timings"] for k in ("embed", "search", "generation", "total")))
check("smalltalk skips the model", p.answer("hello")["sources"] == [])
config.MIN_RELEVANCE = 0.9
check("low relevance gives the standard reply", p.answer("What is the weather?")["answer"] == config.REFUSAL_MESSAGE)
config.MIN_RELEVANCE = 0.0
vector_store.retrieve_timed = lambda q, k: ([], {"embed": 0.0, "search": 0.0})
check("no retrieved passages gives the standard reply", p.answer("zzz")["refused"])

# ---- background loader and answer job: the page must never wait forever
def run_job(factory, q="What is the attendance rule?"):
    rag_pipeline._FACTORY = factory
    rag_pipeline._loader.reset()
    job = rag_pipeline.AnswerJob(q, [])
    t0 = time.time()
    while not job.done and time.time() - t0 < 10:
        time.sleep(0.05)
    return job
vector_store.retrieve_timed = lambda q, k: ([(Doc("A student is required to attend classes regularly.", 13), 0.8)], {"embed": 0.01, "search": 0.02})
def slow_factory(say):
    say("loading..."); time.sleep(0.5); return FakePipeline()
job = run_job(slow_factory)
check("job waits for loader, then answers", job.stage == "done" and "regularly" in job.result["answer"])
check("loader ran exactly once", rag_pipeline.loader_status()["state"] == "ready")
t0 = time.time(); job2 = rag_pipeline.AnswerJob("second question about leaves", [])
while not job2.done and time.time() - t0 < 5: time.sleep(0.02)
check("second question reuses the loaded pipeline (no reload)", job2.done and rag_pipeline.loader_status()["state"] == "ready" and job2.error is None)
def broken_factory(say): raise MemoryError("not enough memory")
job = run_job(broken_factory)
check("model load failure becomes a visible error, not endless loading", job.stage == "error" and "memory" in job.error.lower())
check("loader reports error state", rag_pipeline.loader_status()["state"] == "error")
job = run_job(lambda say: FakePipeline("fail"))
check("generation failure becomes an error", job.stage == "error" and "simulated" in job.error)
job = run_job(lambda say: FakePipeline("stall"))
check("generation stall becomes an error", job.stage == "error")
old = config.LOAD_TIMEOUT_S; config.LOAD_TIMEOUT_S = 1
job = run_job(lambda say: (time.sleep(3), FakePipeline())[1]); config.LOAD_TIMEOUT_S = old
check("load timeout ends the wait with a message", job.stage == "error" and "did not finish loading" in job.error)
rag_pipeline._FACTORY = lambda say: FakePipeline(); rag_pipeline._loader.reset()
j = rag_pipeline.AnswerJob("stop me", []); j.cancel.set()
t0 = time.time()
while not j.done and time.time() - t0 < 5: time.sleep(0.02)
check("Stop button ends the job", j.done)
print(f"\nAll {passed} checks passed.")
