# JRU Campus FAQ Chatbot (academic prototype)

Developed by **ContextualDuo**. A Streamlit chatbot that answers questions about Jose Rizal University using the
JRU College Student Handbook and the Faculty Handbook. It is **not** an official JRU service and is not connected
to any JRU system.

## What it uses
| Part | Technology |
|---|---|
| Interface | Streamlit with custom CSS (`styles.css`) |
| RAG framework | LangChain (`PyPDFLoader`, `RecursiveCharacterTextSplitter`) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector database | ChromaDB, persisted in `chroma_db/` |
| Language model | `Qwen/Qwen2.5-1.5B-Instruct` (same model as the WW1/WW2 notebook) |
| Chat history and preferences | SQLite (`storage/app.db`), scoped per user |

The RAG settings come from the ContextualDuo WW1/WW2 experiment: 800-character chunks with 100 overlap, and top-k
of 5 on a GPU or 3 on a CPU (configurations E and B, the recommendations of that experiment).

## Project structure
```
app.py             Streamlit app (all pages)
auth.py            demo login (PBKDF2 password hashes, lock-out)
rag_pipeline.py    retrieval, prompt, Qwen generation, sources
document_loader.py PDF loading, chunking, page labels, upload validation
vector_store.py    ChromaDB build/open/retrieve, index manifest
chat_history.py    SQLite conversations and preferences
faq_data.py        FAQ entries (each verified against the PDF)
config.py          all settings
styles.css         JRU premium dashboard theme (serif headings, gold cards, faded campus photo)
data/              source PDF
chroma_db/         persistent vector index (created on first run)
assets/            original logo and campus photo (source files)
static/            optimized copies the page uses: jru_logo.png, jru_campus_hero.jpg, jru_campus_login.jpg (Streamlit static serving)
model_cache.py     checks/downloads models with visible progress
prepare.py         one-time setup and a test answer outside Streamlit
benchmark.py       per-stage timing measurements
selftest.py        logic tests (no model needed)
verify_faq.py      re-checks every FAQ sentence against the PDF
TESTING.md  DEPLOYMENT.md
```

## Install and run (localhost)
Python 3.10 or newer is recommended.
```
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python prepare.py               # ONE TIME, before the demo: downloads models (about 3 GB), builds the index, tests a question
streamlit run app.py
```
Windows PowerShell: use `.venv\Scripts\Activate.ps1` instead of `activate`.

**Run `python prepare.py` first.** It shows download progress and times every stage outside Streamlit. After it
finishes, the models are in the local cache and the index exists, so the app answers the first question without a
long wait. The app also loads the models **in the background as soon as you log in** (the page stays usable, shows
"Starting the chatbot (n s)", and a question typed meanwhile is answered when loading ends). Later questions reuse the
loaded model. The index is rebuilt only when the PDFs or chunk settings change, or when an employee presses
*Rebuild the vector index*. Answers stream onto the screen word by word, and there is a Stop button.

### If the first question seems stuck
The page now shows the real stage and any error instead of an endless spinner. The usual causes were:
1. **Silent 3 GB model download** inside the first question (no network, or a slow one): run `python prepare.py` and
   watch the byte counts. With no internet use `JRU_OFFLINE=1` after the models are cached.
2. **bfloat16 on a CPU**: Qwen's config requests bfloat16, which many CPUs emulate very slowly. The app now uses
   float32 on a CPU (about 6 GB of RAM). Set `JRU_DTYPE=bfloat16` to override.
3. **Too little memory**: shown as a clear error with a Retry button. Set `JRU_LLM_MODEL` to a smaller model.
4. Timeouts: loading gives up after 30 min (`JRU_LOAD_TIMEOUT`), writing an answer after 4 min
   (`JRU_GENERATION_TIMEOUT`), and 2 min with no new token (`JRU_STALL_TIMEOUT`); each ends with a message.

Measure your own machine with `python benchmark.py` (load time, query embedding, retrieval, generation, total).

A GPU is optional. On a CPU an answer takes roughly a minute with this model (see the experiment report), on a GPU
under two seconds.

## Demo accounts (test accounts only)
| Role | Number | Password |
|---|---|---|
| Student | `2024-00001` | `Student@2026` |
| Employee | `E-0001` | `Employee@2026` |

Passwords are stored only as salted PBKDF2 hashes. Employees can rebuild the index and add PDFs. Remember Me
remembers the account number only, never the password. Forgot Password explains that reset is not connected.

## Settings you can change (environment variables)
`JRU_LLM_MODEL`, `JRU_EMBEDDING_MODEL`, `JRU_CHUNK_SIZE`, `JRU_CHUNK_OVERLAP`, `JRU_TOP_K`, `JRU_MAX_NEW_TOKENS`,
`JRU_DEVICE_MAP` (use `cpu` to force CPU), `JRU_DTYPE`, `JRU_THREADS`, `JRU_OFFLINE`, `JRU_SIDEBAR_TAGLINE`, `JRU_MIN_RELEVANCE` (optional guard, off by default), `JRU_DB_PATH`.
If the model does not fit in memory, set `JRU_LLM_MODEL` to a smaller instruction model. If you change the
embedding model or chunk settings the index rebuilds automatically.

## How answers are produced
1. The question (plus the previous user question when it is a short follow-up) is embedded and searched in ChromaDB.
2. The top chunks are placed in the prompt of the course template, with the last three exchanges for context.
3. Qwen answers from that context. If the context is not enough, the reply is exactly: "I couldn't find sufficient
   information about this in the available JRU reference documents. Please contact the appropriate university office
   for confirmation."
4. The answer is shown with the handbook and page of each source chunk.

## Known limits (read before the demo)
- The handbooks do not state library opening hours, so the chatbot cannot answer that. The FAQ page says so.
- Qwen2.5-1.5B is small. The experiment showed it can add details that are not in the handbook. Always check the
  sources, and treat answers as help, not official policy.
- The prompt differs from the course template in three ways: the exact refusal sentence, conversation history for
  follow-ups, and answer post-processing (refusal normalization and trimming of cut-off answers).
- The relevance guard `JRU_MIN_RELEVANCE` is off because its threshold has not been calibrated on this data.
- The logo and campus photo in `assets/` are the files you supplied; replace them if you have newer ones.
- Models are loaded once per server process (a module-level singleton, which survives Streamlit reruns); restarting `streamlit run` reloads them.
- Follow-up retrieval is a simple rule, not an LLM query rewriter.

## Replacing the images
The page loads `static/jru_logo.png`, `static/jru_campus_hero.jpg` (wide crop, about 1400x640) and `static/jru_campus_login.jpg`.
Replace those files to change the pictures; if one is missing the app falls back to a text monogram or a plain navy background.
No image is embedded in the code. Remember-me stores only the account number. The Student/Employee selector on the login page
must match the account's role; it does not change any password rule.
