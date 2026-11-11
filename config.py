"""Central configuration for the JRU Campus FAQ Chatbot .

RAG settings are carried over from the ContextualDuo WW1/WW2 notebook, which is built on the
professor's Generic Domain RAG template: all-MiniLM-L6-v2 embeddings, ChromaDB, Qwen2.5-1.5B-Instruct,
RecursiveCharacterTextSplitter (sizes in characters). Nothing secret lives here; secrets, if any,
come from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")   # keep ChromaDB quiet
# Without these, a missing or slow internet connection can make the Hugging Face client wait a long time
# on the first model download. With them it fails fast with a readable error instead.
os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "10")
os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "60")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = BASE_DIR / "chroma_db"
ASSETS_DIR = BASE_DIR / "assets"
STORAGE_DIR = BASE_DIR / "storage"           # SQLite database (chat history, preferences)
CSS_PATH = BASE_DIR / "styles.css"
LOGO_PATH = ASSETS_DIR / "jru_logo.png"       # used only if the official logo is supplied
LOGIN_BG_PATH = next((p for p in (ASSETS_DIR / "login_bg.jpg", ASSETS_DIR / "login_bg.png") if p.exists()),
                     ASSETS_DIR / "login_bg.jpg")   # optional campus photo, login page only

for _d in (DATA_DIR, CHROMA_DIR, ASSETS_DIR, STORAGE_DIR):
    _d.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.environ.get("JRU_DB_PATH", STORAGE_DIR / "app.db"))

# ---------------- application identity ----------------
SYSTEM_NAME = "JRU Campus Information Assistant"
APP_NAME = "JRU Campus FAQ Chatbot"
APP_TAGLINE = "Your Digital Guide to Jose Rizal University."
SIDEBAR_TAGLINE = os.environ.get("JRU_SIDEBAR_TAGLINE", "We Build Better Futures.")
DEVELOPER = "ContextualDuo"      # kept for the README and code comments; not shown in the interface
DISCLAIMER = ("Answers are generated from the JRU handbooks supplied to this assistant and may contain errors. "
              "This is not an official Jose Rizal University service; please confirm important matters with the "
              "appropriate university office.")
# Index rebuilding and PDF uploads are hidden from ordinary visitors. The person running the server can enable
# them by setting the environment variable JRU_ADMIN=1 before starting the app.
ADMIN_MODE = os.environ.get("JRU_ADMIN", "0") == "1"

# ---------------- RAG parameters (from the WW1/WW2 experiment) ----------------
EMBEDDING_MODEL = os.environ.get(
    "JRU_EMBEDDING_MODEL",
    "sentence-transformers/all-MiniLM-L6-v2"
)

# ---------------- Groq API configuration ----------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

GROQ_MODEL = os.environ.get(
    "GROQ_MODEL",
    "openai/gpt-oss-120b"
)

LLM_MODEL = GROQ_MODEL
# ---------------- Gemini API configuration ----------------
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
COLLECTION_NAME = "jru_campus_faq"
CHUNK_SIZE = int(os.environ.get("JRU_CHUNK_SIZE", 800))          # configurations B and E of the experiment
CHUNK_OVERLAP = int(os.environ.get("JRU_CHUNK_OVERLAP", 100))
# Recommended top-k from the experiment: 5 on a GPU (configuration E), 3 on a CPU (configuration B).
# JRU_TOP_K overrides the automatic choice.
TOP_K_GPU = 5
TOP_K_CPU = 3
TOP_K_OVERRIDE = os.environ.get("JRU_TOP_K")
MAX_NEW_TOKENS = int(os.environ.get("JRU_MAX_NEW_TOKENS", 1024))
TEMPERATURE = 0.0
DO_SAMPLE = False
DEVICE_MAP = os.environ.get("JRU_DEVICE_MAP", "auto")           # "cpu" forces CPU
# Optional retrieval guard: if the best relevance score is below this value, the LLM is not called and the
# standard "insufficient information" reply is shown. 0 disables it. Calibrate on your own questions first.
MIN_RELEVANCE = float(os.environ.get("JRU_MIN_RELEVANCE", 0.0))

# ---------------- loading and generation safety limits ----------------
OFFLINE = os.environ.get("JRU_OFFLINE", "0") == "1"                 # use only models already in the local cache
DTYPE = os.environ.get("JRU_DTYPE", "auto")                         # auto: float32 on CPU, bfloat16/float16 on GPU
CPU_THREADS = int(os.environ.get("JRU_THREADS", 0))                 # 0 = leave the PyTorch default
LOAD_TIMEOUT_S = int(os.environ.get("JRU_LOAD_TIMEOUT", 1800))      # give up waiting for the models after this long
GENERATION_TIMEOUT_S = int(os.environ.get("JRU_GENERATION_TIMEOUT", 240))   # stop writing an answer after this long
STREAM_STALL_S = int(os.environ.get("JRU_STALL_TIMEOUT", 120))      # no new token for this long = generation stalled

# Repeated questions: a finished, grounded answer is reused only for a standalone question (no earlier turns in the
# chat), the same retrieval settings and an unchanged index. 0 disables the cache.
ANSWER_CACHE_SIZE = 0

HISTORY_TURNS = 3            # previous exchanges passed to the model for follow-up questions
MAX_QUESTION_CHARS = 500
MAX_UPLOAD_MB = 25

REFUSAL_MESSAGE = ("I couldn't find sufficient information about this in the available JRU reference documents. "
                   "Please contact the appropriate university office for confirmation.")

# ---------------- source documents ----------------
# The combined PDF joins two handbooks. PDF pages 1-42 are the College Student Handbook and
# pages 43-89 the Faculty Handbook (verified against the evidence sentences of the experiment).
COMBINED_PDF_NAME = "JRU_Combined_Student_and_Faculty_Handbooks.pdf"
STUDENT_LAST_PDF_PAGE = 42
STUDENT_HANDBOOK = "JRU College Student Handbook (2024-2025)"
FACULTY_HANDBOOK = "JRU Faculty Handbook (2024-2025)"
DOCUMENT_DESCRIPTIONS = {
    COMBINED_PDF_NAME: ("Combined PDF of the JRU College Student Handbook (PDF pages 1-42) and the JRU Faculty "
                        "Handbook (PDF pages 43-89). It is the knowledge base of the chatbot."),
}

# ---------------- navigation and categories ----------------
# Sidebar menu: (section label, [(page slug, menu label), ...]). Every slug is a real page in app.py.
NAV = [
    ("MAIN MENU", [("overview", "Overview"), ("chat", "Chat Assistant"),
                   ("faq", "Frequently Asked Questions"), ("campus", "Campus Information")]),
    ("KNOWLEDGE CENTER", [("documents", "Documents"), ("kb", "Knowledge Base")]),
    ("ACTIVITY", [("history", "Conversation History")]),
    ("PREFERENCES", [("settings", "Settings"), ("appearance", "Appearance")]),
]
DEFAULT_PAGE = "overview"
CATEGORIES = [
    "Admission and Enrollment",
    "Library Hours and Facilities",
    "Student Services and Offices",
    "Academic Policies",
    "Faculty Policies",
    "General University Information",
]

# The four cards on the chat home screen. Each opens suggested questions from one or more FAQ categories.
HOME_CARDS = [      # (title, icon key, FAQ categories it opens, description)
    ("Admissions & Enrollment", "cap", ["Admission and Enrollment"], "Admission requirements, enrollment procedures, and registration."),
    ("Library & Facilities", "book", ["Library Hours and Facilities"], "Library schedules, facilities, and campus resources."),
    ("Student Services", "users", ["Student Services and Offices"], "Student assistance, offices, and university services."),
    ("General Information", "info", ["General University Information", "Academic Policies", "Faculty Policies"], "General campus questions and university information."),
]
POPULAR_QUESTIONS = ["What are the admission requirements?", "What are the library operating hours?",
                     "How do I enroll at JRU?", "Where can I find student services?"]
# images are served as files from static/ (Streamlit static serving), not embedded in the page
STATIC_DIR = BASE_DIR / "static"
def static_url(name):
    """URL of a file in static/ if it exists, else None (callers fall back gracefully)."""
    return f"app/static/{name}" if (STATIC_DIR / name).exists() else None

CATEGORY_ICONS = {"Admission and Enrollment": "🎓", "Library Hours and Facilities": "📖",
                  "Student Services and Offices": "👥", "Academic Policies": "📝",
                  "Faculty Policies": "🧑‍🏫", "General University Information": "ℹ️"}

# ---------------- colors (JRU-inspired palette) ----------------
NAVY, DEEP_NAVY, GOLD = "#102B4E", "#0B1F38", "#D4A843"
WHITE, CREAM, LIGHT_GRAY = "#FFFFFF", "#F8F6F0", "#F1F3F7"
