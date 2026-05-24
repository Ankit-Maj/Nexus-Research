"""
Unified schema definitions for the AI Research Platform.
All Pydantic models used across agents, orchestrator, API, and frontend.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ── API Request / Response ────────────────────────────────────────────────────

class ResearchRequest(BaseModel):
    query: str = Field(..., description="The main research topic or question")
    retrieval_mode: str = Field("AUTO", description="AUTO | WEB | RAG | HYBRID")
    length: str = Field("Medium", description="Short | Medium | Detailed")
    session_id: str = Field("default_session", description="Session identifier")

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ── Streaming Events ──────────────────────────────────────────────────────────

class StreamEvent(BaseModel):
    """Structured SSE event emitted by the orchestrator."""
    event_type: str = Field(..., description="agent_update | section_complete | retrieval_update | compiler_status | error")
    timestamp: str
    agent_name: str
    status: str  # started | completed | warning | error | info
    message: str
    data: Optional[Dict[str, Any]] = None

# ── Observability ─────────────────────────────────────────────────────────────

class ObservabilityMetrics(BaseModel):
    session_id: str
    total_latency_ms: float = 0.0
    llm_calls: int = 0
    llm_total_tokens: int = 0
    tavily_calls: int = 0
    rag_chunks_retrieved: int = 0
    retry_count: int = 0
    section_latencies_ms: Dict[str, float] = Field(default_factory=dict)
    rewritten_queries: List[str] = Field(default_factory=list)

# ── Retrieval Models ──────────────────────────────────────────────────────────

class RetrievalScore(BaseModel):
    vector_score: float = Field(0.0, description="Normalized FAISS cosine similarity [0,1]")
    bm25_score: float = Field(0.0, description="Normalized BM25 score [0,1]")
    hybrid_score: float = Field(0.0, description="Combined hybrid score [0,1]")

class ChunkMetadata(BaseModel):
    source_name: str
    source_type: str  # document | web
    chunk_index: int = 0
    page: Optional[int] = None
    url: Optional[str] = None
    file_path: Optional[str] = None
    extraction_method: str = "DIRECT"  # DIRECT | OCR

class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    retrieval_rank: int
    metadata: ChunkMetadata
    scores: RetrievalScore

# ── Agent Structured Outputs ──────────────────────────────────────────────────

class RouterResponse(BaseModel):
    route: str = Field(..., description="RAG | WEB | HYBRID")
    reasoning: str

class OutlineSection(BaseModel):
    title: str
    description: str
    priority: int = Field(1, description="Section priority 1=highest")
    required_topics: List[str] = Field(default_factory=list, description="Key topics this section must cover")
    retrieval_focus: str = Field("", description="Hint for retrieval — what to search for")

class PlannerOutlineResponse(BaseModel):
    title: str
    sections: List[OutlineSection]

class QueryRewriterResponse(BaseModel):
    rewritten_query: str = Field(..., description="Optimized query for retrieval")
    search_queries: List[str] = Field(..., description="Up to 3 distinct search queries")
    reasoning: str = Field("", description="Why the query was rewritten this way")

class SearchQueryGeneration(BaseModel):
    queries: List[str] = Field(..., description="Up to 3 optimized search queries")

class RiskItem(BaseModel):
    level: str = Field(..., description="LOW | MEDIUM | HIGH")
    impact: str
    mitigation: Optional[str] = None
    confidence_score: float = Field(0.7, description="Confidence in this risk finding [0,1]")

class RiskAnalysisResponse(BaseModel):
    summary: str
    risks: List[RiskItem]

class ValidatorFinding(BaseModel):
    finding_type: str = Field(..., description="CONTRADICTION | WEAK_EVIDENCE | VERIFIED")
    source: str
    description: str
    confidence_score: float = Field(0.7, description="Confidence in this finding [0,1]")
    citation_ids: List[int] = Field(default_factory=list, description="Citation IDs involved")

class ValidatorResponse(BaseModel):
    overall_integrity_score: float = Field(..., description="0.0–10.0")
    findings: List[ValidatorFinding]

# ── Report Models ─────────────────────────────────────────────────────────────

class Citation(BaseModel):
    citation_id: int
    source_name: str
    source_type: str  # document | web
    page: Optional[int] = None
    url: Optional[str] = None
    snippet: str
    confidence_score: float = Field(1.0, description="Retrieval confidence for this citation [0,1]")
    extraction_method: str = Field("DIRECT", description="DIRECT | OCR")
    retrieval_scores: Optional[RetrievalScore] = None

class ReportSection(BaseModel):
    title: str
    content: str
    citations: List[int] = Field(default_factory=list)
    confidence_score: float = Field(0.8, description="Overall section confidence [0,1]")
    generation_latency_ms: float = 0.0

class FinalReport(BaseModel):
    id: str
    query: str
    title: str
    rewritten_query: str = Field("", description="Query as rewritten by Query Rewriter Agent")
    executive_summary: str
    sections: List[ReportSection]
    risk_assessment: RiskAnalysisResponse
    validation: ValidatorResponse
    citations: List[Citation]
    metrics: Optional[ObservabilityMetrics] = None
    created_at: str

# ── Retrieval Inspector API ───────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0
    source_name: str
    source_type: str
    retrieval_rank: int = 0
    extraction_method: str = "DIRECT"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TraceMessage(BaseModel):
    timestamp: str
    agent_name: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None
