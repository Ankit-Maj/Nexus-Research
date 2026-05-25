# NEXUS — System Design Document

**Version:** 2.0.0  
**Stack:** FastAPI · React · MongoDB Atlas · Groq · Tavily · FAISS · BM25

---

## 1. System Overview

NEXUS is a multi-agent AI research orchestration platform. It accepts a natural language research query and produces a structured, cited intelligence report by coordinating a deterministic pipeline of specialized agents. Each agent is isolated, stateless, and reusable. The orchestrator owns all sequencing and state.

The system is designed around three principles:
- **Explainability** — every retrieval score, agent decision, and confidence value is tracked and exposed
- **Reliability** — every external call (LLM, search) has a multi-tier fallback chain
- **Determinism** — the pipeline is staged and sequential at the macro level, with parallelism only where outputs are independent

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT (React)                             │
│  Auth → Query Input → SSE Stream Consumer → Report Renderer        │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS / SSE
┌────────────────────────────▼────────────────────────────────────────┐
│                       FASTAPI BACKEND                               │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  Auth Layer  │  │  API Routes  │  │  Retrieval Inspector API │  │
│  │  JWT + bcrypt│  │  /research   │  │  /retrieval, /metrics    │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────────┘  │
│                           │                                         │
│              ┌────────────▼────────────┐                           │
│              │      ORCHESTRATOR       │                           │
│              │  Staged async pipeline  │                           │
│              └────────────┬────────────┘                           │
│                           │                                         │
│   ┌───────────────────────▼──────────────────────────────────┐     │
│   │                    AGENT LAYER                            │     │
│   │  Router · Planner · Rewriter · Search · RAG ·            │     │
│   │  Summarizer · SectionWriter · Validator · Risk · Compiler │     │
│   └───────────────────────┬──────────────────────────────────┘     │
│                           │                                         │
│   ┌───────────────────────▼──────────────────────────────────┐     │
│   │                   SERVICE LAYER                           │     │
│   │  LLMService (Groq + OpenRouter)  TavilyClient            │     │
│   │  SessionRAGStore (FAISS + BM25)  MongoDB (motor)         │     │
│   └──────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Agent Pipeline

The pipeline is deterministic and staged. Agents do not call each other — the orchestrator calls each agent in sequence and passes outputs forward.

### 3.1 Execution Order

```
1. Router Agent
      ↓
2. Planner Agent
      ↓
3. Query Rewriter Agent
      ↓
4. ┌─────────────────────────────────┐
   │  PARALLEL RETRIEVAL             │
   │  Search Agent  ║  RAG Agent     │
   └─────────────────────────────────┘
      ↓
5. Citation Pool Builder (dedup + ID assignment)
      ↓
6. ┌─────────────────────────────────────────────┐
   │  PARALLEL SECTION WRITING                   │
   │  [Summarizer → SectionWriter] × N sections  │
   └─────────────────────────────────────────────┘
      ↓
7. Validator Agent
      ↓
8. Risk Analysis Agent
      ↓
9. Report Compiler Agent
      ↓
   FinalReport (JSON + Markdown) → SSE stream → client
```

### 3.2 Agent Responsibilities

| Agent | Input | Output | Model |
|---|---|---|---|
| Router | query, uploads_exist | route (WEB/RAG/HYBRID) | llama-3.3-70b |
| Planner | query, length | structured outline (N sections) | llama-3.3-70b |
| Query Rewriter | query | rewritten_query, search_queries[] | llama-3.1-8b (fast) |
| Search Agent | search_queries[] | web results[] | — (Tavily API) |
| RAG Agent | rewritten_query, session_id | RetrievedChunk[] | — (FAISS+BM25) |
| Summarizer | section, sources[] | synthesized context string | llama-3.3-70b |
| Section Writer | section, context | markdown body, citation_ids[] | llama-3.3-70b |
| Validator | sections[], citations[] | integrity_score, findings[] | llama-3.3-70b |
| Risk Analysis | sections[], citations[] | risks[], summary | llama-3.3-70b |
| Report Compiler | all above | FinalReport + executive summary | llama-3.3-70b |

---

## 4. Retrieval System

### 4.1 Hybrid Search

Every document query runs two searches in parallel and fuses the scores:

```
Query
  ├─► FAISS IndexFlatIP (cosine similarity via normalized inner product)
  │       → vector_score ∈ [0, 1]
  │
  └─► BM25Okapi (sparse keyword matching)
          → bm25_score ∈ [0, 1] (min-max normalized)

hybrid_score = 0.5 × vector_score + 0.5 × bm25_score

Filter: discard chunks where hybrid_score < MIN_HYBRID_SCORE (0.15)
```

### 4.2 RetrievedChunk Schema

Every chunk returned from the store carries full provenance:

```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    retrieval_rank: int
    metadata: ChunkMetadata      # source_name, page, url, extraction_method
    scores: RetrievalScore       # vector_score, bm25_score, hybrid_score
```

Scores are preserved through the entire pipeline — into citations, the validator, and the exported report.

### 4.3 Document Ingestion

```
File upload (PDF/DOCX/TXT/MD)
    ↓
parse_document() → (text, extraction_method)
    extraction_method = "DIRECT" | "OCR"
    ↓
chunk_text() → overlapping 1000-char chunks, 200-char overlap
    ↓
SentenceTransformer.encode() → 384-dim embeddings (all-MiniLM-L6-v2)
    ↓
FAISS IndexFlatIP rebuild + BM25Okapi rebuild
```

OCR fallback (pytesseract + pdf2image) activates automatically when direct text extraction yields fewer than 50 characters.

### 4.4 Query Rewriter

Runs before both Tavily and FAISS. Uses the fast model to:
1. Rewrite the original query into a retrieval-optimized form
2. Generate up to 3 distinct search queries covering different angles

The rewritten query is stored in the final report for full transparency.

---

## 5. LLM Service & Fallback Chain

### 5.1 Provider Priority

```
For each model in [llama-3.3-70b, llama-3.1-8b, mixtral-8x7b, gemma2-9b]:
    Try Groq key 1  →  Try Groq key 2  →  Try OpenRouter equivalent
    (first success returns immediately)

If all exhausted → raise RuntimeError
```

### 5.2 Key Design: max_retries=0

The Groq SDK has an internal retry loop that holds a 429 for up to 40 seconds before surfacing the error. Setting `max_retries=0` on the Groq client disables this, so our fallback chain fires immediately on rate limits.

### 5.3 Token Budget

All context fed to the LLM is truncated before the call:

```python
MAX_CONTEXT_TOKENS = 6000    # ~24,000 chars
MAX_OUTPUT_TOKENS  = 3000
MAX_SECTION_CONTEXTS = 4     # max source chunks per section
CHARS_PER_TOKEN = 4          # approximation
```

Context blocks are sorted by hybrid_score descending before truncation — highest-quality evidence is always preserved.

---

## 6. Web Search Service

### 6.1 Tavily Fallback Chain

```
For each Tavily API key (TAVILY_API_KEY, TAVILY_API_KEY2):
    POST api.tavily.com/search
    On 429 → try next key

If all keys exhausted → DuckDuckGo HTML scrape (no API key required)
```

### 6.2 Concurrent Search

The Search Agent fires all generated queries concurrently via `asyncio.gather`, then deduplicates results by URL. This reduces search latency from O(N×latency) to O(latency).

### 6.3 Result Caching

Results are cached in-memory by `(query, max_results)` key for the lifetime of the process, preventing duplicate API calls for the same query within a session.

---

## 7. Authentication & Security

### 7.1 Password Hashing

```python
# bcrypt has a hard 72-byte input limit.
# SHA-256 + base64 normalizes any password length before hashing.
digest = hashlib.sha256(password.encode()).digest()
hashed = bcrypt.hashpw(base64.b64encode(digest), bcrypt.gensalt(rounds=12))
```

### 7.2 JWT Flow

```
POST /auth/login
    → verify password
    → jwt.encode({ sub: username, exp: now + 60min }, JWT_SECRET_KEY)
    → return { access_token, token_type: "bearer" }

All protected routes:
    → OAuth2PasswordBearer extracts token from Authorization header
    → jwt.decode() → get username → lookup user in DB
    → inject user dict into route handler
```

### 7.3 Download Auth

The `/download/{report_id}` endpoint accepts the JWT as either an `Authorization` header or a `?token=` query parameter, enabling direct browser download links.

---

## 8. Persistence Layer

### 8.1 MongoDB Collections

| Collection | Contents |
|---|---|
| `users` | username, hashed_password, created_at |
| `sessions` | session_id, username, metadata, updated_at |
| `reports` | report_id, session_id, username, created_at, data (full FinalReport) |
| `traces` | session_id + all trace events |

### 8.2 In-Memory Fallback

If `MONGODB_URI` is not set, all collections fall back to in-memory Python dicts. The application is fully functional without a database — useful for local development with zero infrastructure.

### 8.3 Session Cleanup

Sessions have a TTL of 3600 seconds (`SESSION_TTL_SECONDS`). `cleanup_expired_sessions()` removes expired FAISS stores from memory. Triggered via `POST /admin/cleanup` or automatically on the next access check.

---

## 9. Streaming Architecture

The `/research` endpoint returns a `StreamingResponse` with `media_type="text/event-stream"`. The orchestrator is an `AsyncGenerator` that yields SSE-formatted strings at each pipeline stage.

### 9.1 Event Types

```
event_type: "agent_update"     → general agent status
event_type: "retrieval_update" → search/RAG progress
event_type: "section_complete" → one section finished
event_type: "compiler_status"  → final assembly
event: report                  → final FinalReport JSON (special SSE named event)
```

### 9.2 SSE Format

```
data: {"event_type":"section_complete","timestamp":"12:00:08",
       "agent_name":"Section Writer Agent","status":"completed",
       "message":"Section 2/5: \"Market Analysis\" (confidence=0.87, 1340ms)",
       "data":{"confidence":0.87,"latency_ms":1340}}

event: report
data: { ...full FinalReport JSON... }
```

The frontend splits the stream on `\n\n`, parses each event, and updates the pipeline visualizer, trace console, and report view in real time.

---

## 10. Observability

Every compiled report includes an `ObservabilityMetrics` object:

```python
class ObservabilityMetrics(BaseModel):
    session_id: str
    total_latency_ms: float
    llm_calls: int
    tavily_calls: int
    rag_chunks_retrieved: int
    retry_count: int
    section_latencies_ms: Dict[str, float]   # per-section timing
    rewritten_queries: List[str]
```

Accessible via `GET /metrics/{report_id}` and embedded in the report JSON and exported Markdown.

---

## 11. API Surface

### Auth
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Get JWT token |
| GET | `/auth/me` | ✓ | Current user |

### Research
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/upload` | ✓ | Ingest documents into session RAG store |
| POST | `/research` | ✓ | Run pipeline, stream SSE |
| GET | `/download/{id}` | ✓ | Export Markdown report |

### Inspection
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/sources/{report_id}_{cit_id}` | ✓ | Citation chunk + scores |
| GET | `/retrieval/{session_id}?query=` | ✓ | Live retrieval inspector |
| GET | `/metrics/{report_id}` | ✓ | Observability metrics |
| GET | `/trace/{session_id}` | ✓ | Agent execution traces |

### History & Cleanup
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/history/reports` | ✓ | All user reports |
| GET | `/history/reports/{id}` | ✓ | Full report data |
| DELETE | `/session/{id}` | ✓ | Clean up session |
| POST | `/admin/cleanup` | ✓ | Remove expired sessions |
| GET | `/health` | — | Health check |

---

## 12. Data Flow: Single Request

```
1.  POST /research { query, retrieval_mode, length, session_id }
2.  JWT validated → username extracted
3.  Orchestrator starts → ObservabilityMetrics initialized
4.  Router Agent → route = "WEB"
5.  Planner Agent → 5-section outline
6.  Query Rewriter → rewritten_query + 3 search_queries
7.  asyncio.gather(Search Agent, RAG Agent)  ← concurrent
8.  Citation pool built → 9 unique sources, IDs 1–9
9.  asyncio.gather(*[write_section(i) for i in range(5)])  ← concurrent
    Each: Summarizer → SectionWriter → ReportSection(confidence, latency)
10. Validator Agent → integrity_score=7.8, 12 findings
11. Risk Analysis Agent → 6 risks
12. Report Compiler → executive summary → FinalReport
13. FinalReport saved to MongoDB + written to disk as .json + .md
14. SSE: "event: report\ndata: {...}\n\n"
15. POST /research returns — total latency ~18s
```

---

## 13. Deployment

### Environment Variables (required)

```
GROQ_API_KEY          Primary LLM key
GROQ_API_KEY2         Fallback LLM key
TAVILY_API_KEY        Web search key
OPENROUTER_API_KEY    Final LLM fallback
MONGODB_URI           Atlas connection string
JWT_SECRET_KEY        Long random string (change in production)
```

### Railway (recommended)

**Backend service:**
- Root directory: *(repo root)*
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**Frontend service:**
- Root directory: `frontend`
- Build: `npm install && npm run build`
- Publish: `dist`
- Env: `VITE_API_URL=https://your-backend.up.railway.app`

### Known Constraints

- FAISS indices are in-memory per session — lost on restart unless MongoDB stores metadata
- OCR requires Tesseract/Poppler system binaries — not available on Railway/Render Python environments; app degrades gracefully
- Groq free tier has per-minute token limits — the fallback chain handles this but very long reports may be slow under heavy load
- `sentence-transformers` downloads ~90MB model on first startup — may timeout on slow build environments
