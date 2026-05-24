import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# ── Groq API Keys (primary + fallbacks) ──────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY2 = os.getenv("GROQ_API_KEY2", "")
GROQ_API_KEYS: list[str] = [k for k in [GROQ_API_KEY, GROQ_API_KEY2] if k]

# ── OpenRouter fallback ───────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Tavily API Keys (primary + fallbacks) ─────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_API_KEY2 = os.getenv("TAVILY_API_KEY2", "")
TAVILY_API_KEYS: list[str] = [k for k in [TAVILY_API_KEY, TAVILY_API_KEY2] if k]

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "research_platform")

# ── Auth / JWT ────────────────────────────────────────────────────────────────
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_STRONG_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# ── OCR / PDF tools ───────────────────────────────────────────────────────────
OCR_TESSERACT_CMD = os.getenv("OCR_TESSERACT_CMD", "")
OCR_POPPLER_PATH = os.getenv("OCR_POPPLER_PATH", "")

# ── Directory configurations ──────────────────────────────────────────────────
UPLOAD_DIR = BASE_DIR / "app" / "uploads"
REPORT_DIR = BASE_DIR / "app" / "reports"
LOG_DIR = BASE_DIR / "app" / "logs"

for dir_path in [UPLOAD_DIR, REPORT_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = LOG_DIR / "app.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)

logger = logging.getLogger("MultiAgentResearch")

# ── Token budget constants ─────────────────────────────────────────────────────
MAX_CONTEXT_TOKENS = 6000       # Max tokens fed into any single LLM call as context
MAX_OUTPUT_TOKENS = 3000        # Max tokens for section writer output
MAX_SECTION_CONTEXTS = 4        # Max source chunks per section
CHARS_PER_TOKEN = 4             # Rough approximation: 1 token ≈ 4 characters

# ── Retrieval quality threshold ───────────────────────────────────────────────
MIN_HYBRID_SCORE = 0.15         # Discard chunks below this hybrid score

# ── Session cleanup ───────────────────────────────────────────────────────────
SESSION_TTL_SECONDS = 3600      # 1 hour — sessions older than this are eligible for cleanup

if not GROQ_API_KEYS:
    logger.warning("No GROQ_API_KEY configured. LLM calls will fail.")
if not TAVILY_API_KEYS:
    logger.warning("No TAVILY_API_KEY configured. Web search will use fallback only.")
if not MONGODB_URI:
    logger.warning("MONGODB_URI not set. Persistence will be disabled.")
if JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION_USE_STRONG_SECRET":
    logger.warning("JWT_SECRET_KEY is using the default insecure value. Set a strong secret in .env.")

logger.info("Application logging and configuration initialized.")
