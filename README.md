# LEXICON — AI Multi-Agent Research Intelligence Platform

> Enterprise-grade multi-agent research orchestration system. Produces structured intelligence reports with source validation, inline citations, retrieval scoring, and full workflow observability.

---

## Overview

LEXICON is a production-ready AI research platform that coordinates a pipeline of specialized agents to answer complex research queries. It is not a chatbot wrapper — it is a deterministic, staged orchestration system that plans, retrieves, synthesizes, validates, and compiles structured reports with full source traceability.

The system supports document ingestion (PDF, DOCX, TXT, MD) with hybrid vector + keyword retrieval, live web search via Tavily, JWT authentication, MongoDB persistence, and real-time SSE streaming of agent execution traces to the frontend.

---

## Architecture

### Agent Pipeline

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                             │
│                                                                 │
│  1. Router Agent          → decides WEB / RAG / HYBRID          │
│  2. Planner Agent         → generates structured outline        │
│  3. Query Rewriter Agent  → optimizes query for retrieval       │
│  4. ┌─────────────────────────────────────────────┐            │
│     │  PARALLEL RETRIEVAL                          │            │
│     │  Search Agent (Tavily)  ║  RAG Agent (FAISS) │            │
│     └─────────────────────────────────────────────┘            │
│  5. Citation Pool Builder → deduplicates, assigns IDs          │
│  6. ┌─────────────────────────────────────────────┐            │
│     │  PARALLEL SECTION WRITING                    │            │
│     │  Summarizer → Section Writer (per section)   │            │
│     └─────────────────────────────────────────────┘            │
│  7. Validator Agent       → audits sections vs. evidence        │
│  8. Risk Analysis Agent   → identifies risks from evidence      │
│  9. Report Compiler Agent → assembles + executive summary       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
FinalReport (JSON + Markdown) → streamed to frontend via SSE
```

### Retrieval Pipeline

```
Query
  │
  ├─► Query Rewriter Agent (LLM-optimized query)
  │
  ├─► Tavily Web Search (concurrent, multi-key rotation, DDG fallback)
  │
  └─► FAISS Vector Search + BM25 Keyword Search
          │
          └─► Hybrid Score Fusion (0.5 × vector + 0.5 × BM25)
                  │
                  └─► Threshold Filter (MIN_HYBRID_SCORE = 0.15)
                          │
                          └─► RetrievedChunk (with full score metadata)
```

### LLM Fallback Chain

```
For each model in priority list:
  Groq key 1  →  Groq key 2  →  OpenRouter
  (max_retries=0 on SDK — our chain fires immediately on 429)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| LLM provider | Groq (llama-3.3-70b, llama-3.1-8b, mixtral, gemma2) |
| LLM fallback | OpenRouter |
| Web search | Tavily API + DuckDuckGo HTML fallback |
| Vector search | FAISS (cosine similarity, IndexFlatIP) |
| Keyword search | BM25Okapi (rank-bm25) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Document parsing | pypdf, python-docx, pytesseract (OCR fallback) |
| Authentication | JWT (python-jose) + bcrypt |
| Database | MongoDB Atlas (motor async driver) |
| Frontend | React 19 + Vite + Tailwind CSS v3 |
| Icons | Lucide React |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
pepCapstone1/
├── app/
│   ├── agents/
│   │   └── definitions.py        # All agent functions (isolated, reusable)
│   ├── api/
│   │   ├── routes.py             # Main API endpoints
│   │   └── auth_routes.py        # Auth endpoints (/auth/*)
│   ├── models/
│   │   └── schemas.py            # All Pydantic models
│   ├── rag/
│   │   ├── parser.py             # Document parser (DIRECT + OCR)
│   │   └── retriever.py          # SessionRAGStore (FAISS + BM25)
│   ├── services/
│   │   ├── auth.py               # JWT + bcrypt
│   │   ├── database.py           # MongoDB + in-memory fallback
│   │   ├── llm.py                # LLM service with fallback chain
│   │   └── tavily_client.py      # Tavily + DuckDuckGo fallback
│   ├── utils/
│   │   ├── config.py             # All env vars + constants
│   │   └── md_generator.py       # Markdown report generator
│   ├── workflows/
│   │   └── orchestrator.py       # Staged async orchestration
│   └── main.py                   # FastAPI app + lifespan
├── frontend/
│   ├── src/
│   │   ├── App.jsx               # Full React application
│   │   └── index.css             # Tailwind + custom CSS
│   ├── tailwind.config.js
│   └── package.json
├── tests/
│   ├── test_api.py
│   ├── test_live_workflow.py
│   └── test_rag.py
├── .env                          # Environment variables (not committed)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── README.md
└── design.md                     # UI/UX design system reference
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
# ── Groq API Keys (primary + fallback) ───────────────────────────────────────
GROQ_API_KEY=gsk_...
GROQ_API_KEY2=gsk_...           # Optional second key for rate-limit rotation

# ── Tavily API Keys ───────────────────────────────────────────────────────────
TAVILY_API_KEY=tvly-...
TAVILY_API_KEY2=tvly-...        # Optional second key

# ── OpenRouter (LLM fallback after all Groq keys exhausted) ──────────────────
OPENROUTER_API_KEY=sk-or-v1-...

# ── MongoDB ───────────────────────────────────────────────────────────────────
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?appName=...
MONGODB_DB_NAME=research_platform

# ── JWT Auth ──────────────────────────────────────────────────────────────────
JWT_SECRET_KEY=your-long-random-secret-here   # CHANGE IN PRODUCTION
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# ── OCR (optional, for scanned PDF support) ───────────────────────────────────
OCR_TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
OCR_POPPLER_PATH=C:\path\to\poppler\bin
```

**Required:** `GROQ_API_KEY`, `TAVILY_API_KEY`  
**Strongly recommended:** `MONGODB_URI`, `JWT_SECRET_KEY` (change from default), `OPENROUTER_API_KEY`  
**Optional:** `GROQ_API_KEY2`, `TAVILY_API_KEY2`, OCR paths

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Tesseract OCR *(optional — for scanned PDF support)*
- Poppler *(optional — required by pdf2image for OCR)*

### Local Setup

**1. Clone and configure**
```bash
git clone <repo-url>
cd pepCapstone1
cp .env.example .env   # then fill in your keys
```

**2. Backend**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**3. Frontend**
```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`, backend at `http://localhost:8000`.

### Docker (full stack)

```bash
docker-compose up --build
```

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:80`

---

## API Reference

All endpoints except `/health` and `/auth/*` require a JWT bearer token.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create account `{ username, password }` |
| `POST` | `/auth/login` | Get JWT token (form: `username`, `password`) |
| `GET` | `/auth/me` | Current user info |

### Research

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Ingest documents into session RAG store |
| `POST` | `/research` | Start workflow, stream SSE events |
| `GET` | `/download/{report_id}` | Download Markdown report |

### Inspection & Observability

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/sources/{report_id}_{citation_id}` | Citation chunk details with scores |
| `GET` | `/retrieval/{session_id}?query=...` | Live retrieval inspector |
| `GET` | `/metrics/{report_id}` | Observability metrics for a report |
| `GET` | `/trace/{session_id}` | Agent execution traces |

### History

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/history/reports` | All reports for current user |
| `GET` | `/history/reports/{report_id}` | Full report data |
| `GET` | `/history/sessions` | All sessions for current user |

### Session Management

| Method | Endpoint | Description |
|---|---|---|
| `DELETE` | `/session/{session_id}` | Clean up session RAG store + uploads |
| `POST` | `/admin/cleanup` | Remove all expired sessions |
| `GET` | `/health` | Health check |

### SSE Stream Format

The `/research` endpoint streams Server-Sent Events:

```
data: {"event_type":"agent_update","timestamp":"12:00:01","agent_name":"Router Agent","status":"completed","message":"Route: WEB","data":{"route":"WEB"}}

data: {"event_type":"section_complete","timestamp":"12:00:08","agent_name":"Section Writer Agent","status":"completed","message":"Section 1/3: \"History\" (confidence=0.85, 1240ms)"}

event: report
data: { ...FinalReport JSON... }
```

---

## Key Design Decisions

**Why `max_retries=0` on Groq SDK?**  
The Groq SDK has its own internal retry loop that holds a 429 for 4–40 seconds before surfacing the error. Setting `max_retries=0` lets our fallback chain fire immediately: same model → key 2 → OpenRouter.

**Why parallel section writing?**  
Sections are independent. Running them concurrently with `asyncio.gather` cuts total latency by ~60% on medium-length reports.

**Why SHA-256 pre-hash before bcrypt?**  
bcrypt has a hard 72-byte input limit. SHA-256 + base64 encoding normalizes any password length safely before hashing — the same pattern used by Django.

**Why in-memory fallback for MongoDB?**  
The app is fully functional without a database configured. `MONGODB_URI` being unset silently switches to in-memory dicts, so local development requires zero infrastructure.

**Why `MIN_HYBRID_SCORE = 0.15`?**  
Low-scoring chunks add noise to the context window and inflate token usage without improving quality. The threshold discards retrieval results that are unlikely to be relevant.

---

## Observability

Every compiled report includes an `ObservabilityMetrics` object:

```json
{
  "session_id": "session_abc123",
  "total_latency_ms": 18420,
  "llm_calls": 14,
  "llm_total_tokens": 0,
  "tavily_calls": 3,
  "rag_chunks_retrieved": 8,
  "retry_count": 0,
  "section_latencies_ms": {
    "History and Development": 1240,
    "Technical Architecture": 1890
  },
  "rewritten_queries": ["optimized query string"]
}
```

Accessible via `GET /metrics/{report_id}` or embedded in the report JSON.

---

## Limitations

- **Session-scoped RAG**: FAISS indices live in memory per session. Restarting the server clears them. Documents must be re-uploaded after restart unless MongoDB persistence is used for metadata.
- **OCR requires system binaries**: Tesseract and Poppler must be installed at the OS level. The app degrades gracefully to direct text extraction if they are absent.
- **Groq free tier rate limits**: The free tier has per-minute token limits. The fallback chain (key 2 → OpenRouter) handles this automatically, but very long reports may still be slow under heavy rate limiting.
- **No streaming PDF**: Reports export as Markdown only. PDF generation was removed due to Unicode font limitations in fpdf2.
