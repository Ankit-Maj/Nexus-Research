"""
Agent definitions — deterministic, isolated, reusable.

Each agent is a pure function (sync or async) that:
  - accepts typed inputs
  - calls LLM or retrieval services
  - returns typed outputs
  - does NOT orchestrate other agents

Token budgeting:
  Context fed to LLM is truncated to MAX_CONTEXT_TOKENS characters
  (using CHARS_PER_TOKEN approximation) before any call.
"""

import re
import asyncio
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

from app.utils.config import (
    logger,
    MAX_CONTEXT_TOKENS,
    MAX_OUTPUT_TOKENS,
    MAX_SECTION_CONTEXTS,
    CHARS_PER_TOKEN,
)
from app.services.llm import llm_service
from app.services.tavily_client import tavily_client
from app.rag.retriever import get_session_store
from app.models.schemas import (
    RouterResponse,
    PlannerOutlineResponse,
    OutlineSection,
    QueryRewriterResponse,
    SearchQueryGeneration,
    RiskAnalysisResponse,
    ValidatorResponse,
    ValidatorFinding,
    RiskItem,
    ReportSection,
    Citation,
    FinalReport,
    RetrievedChunk,
    RetrievalScore,
    ObservabilityMetrics,
)

# ── Token budget helpers ──────────────────────────────────────────────────────

def _budget_chars(max_tokens: int) -> int:
    return max_tokens * CHARS_PER_TOKEN


def _truncate_to_budget(text: str, max_tokens: int) -> str:
    limit = _budget_chars(max_tokens)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n[...truncated for context budget...]"


def _build_context_block(
    chunks: List[Dict[str, Any]],
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> str:
    """
    Build a formatted context string from source dicts.
    Prioritizes by hybrid_score descending, then truncates to token budget.
    """
    budget = _budget_chars(max_tokens)
    lines: List[str] = []
    used = 0

    for ctx in chunks:
        cit_id = ctx.get("citation_id", "?")
        source = ctx.get("source_name", "Unknown")
        src_type = ctx.get("source_type", "document")
        content = ctx.get("content", "")
        url = ctx.get("url", "")
        page = ctx.get("page")
        v_score = ctx.get("vector_score", 0.0)
        b_score = ctx.get("bm25_score", 0.0)
        h_score = ctx.get("hybrid_score", 0.0)
        extraction = ctx.get("extraction_method", "DIRECT")

        header = (
            f"[Source ID: {cit_id} | {src_type.upper()} | {source}"
            + (f" | Page {page}" if page else "")
            + (f" | {url}" if url else "")
            + f" | hybrid={h_score:.3f} v={v_score:.3f} bm25={b_score:.3f} | {extraction}]"
        )
        block = f"{header}\n{content}\n"

        if used + len(block) > budget:
            remaining = budget - used
            if remaining > 200:
                lines.append(block[:remaining] + "\n[...truncated...]")
            break

        lines.append(block)
        used += len(block)

    return "\n".join(lines) if lines else "No context available."


# ── 1. Router Agent ───────────────────────────────────────────────────────────

def run_router_agent(query: str, uploads_exist: bool) -> RouterResponse:
    logger.info(f"[Router] query='{query}' uploads={uploads_exist}")

    if not uploads_exist:
        return RouterResponse(
            route="WEB",
            reasoning="No documents uploaded. Using live web search.",
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Query Router Agent. Choose the retrieval route:\n"
                "- 'RAG': query is specific and answerable from uploaded documents.\n"
                "- 'WEB': query needs current events or general web knowledge.\n"
                "- 'HYBRID': query needs both documents and web knowledge.\n"
                "Be decisive."
            ),
        },
        {
            "role": "user",
            "content": f'Query: "{query}"\nUploaded files available: {uploads_exist}',
        },
    ]
    return llm_service.complete_structured(messages, RouterResponse, temperature=0.1)


# ── 2. Planner Agent ──────────────────────────────────────────────────────────

def run_planner_agent(query: str, length: str) -> PlannerOutlineResponse:
    section_count = {"Short": 3, "Medium": 5, "Detailed": 7}.get(length, 5)
    logger.info(f"[Planner] query='{query}' length={length} sections={section_count}")

    messages = [
        {
            "role": "system",
            "content": (
                "You are a Research Planner Agent. Break the query into a structured report outline.\n"
                "For each section provide: title, description, priority (1=highest), "
                "required_topics (list of key topics), retrieval_focus (what to search for).\n"
                "Do NOT include Introduction, Conclusion, or Appendix — those are auto-generated.\n"
                "Order sections by priority.\n"
                "The 'title' field at the top level must be a descriptive report title string, "
                "NOT a class name or schema name."
            ),
        },
        {
            "role": "user",
            "content": (
                f'Research Query: "{query}"\n'
                f"Report Length: {length} — generate exactly {section_count} sections.\n"
                f'Example title format: "Comprehensive Analysis of {query}"'
            ),
        },
    ]
    result = llm_service.complete_structured(messages, PlannerOutlineResponse, temperature=0.2)

    # Guard: if LLM returned the class name as title, replace it
    if not result.title or result.title in ("PlannerOutlineResponse", "title", "string"):
        result = PlannerOutlineResponse(
            title=f"Research Report: {query}",
            sections=result.sections,
        )
    return result


# ── 3. Query Rewriter Agent ───────────────────────────────────────────────────

def run_query_rewriter_agent(
    query: str,
    section_focus: str = "",
    metrics: Optional[ObservabilityMetrics] = None,
) -> QueryRewriterResponse:
    """
    Rewrites the query for optimal retrieval.
    Runs BEFORE both Tavily search and RAG retrieval.
    """
    logger.info(f"[QueryRewriter] original='{query}'")

    context_hint = f"\nSection focus: {section_focus}" if section_focus else ""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a Query Rewriter Agent for an enterprise research platform.\n"
                "Your job is to:\n"
                "1. Rewrite the query to be specific, descriptive, and retrieval-optimized.\n"
                "2. Generate up to 3 distinct search queries covering different angles.\n"
                "3. Explain your reasoning briefly.\n"
                "Return ONLY valid JSON."
            ),
        },
        {
            "role": "user",
            "content": f'Original query: "{query}"{context_hint}',
        },
    ]
    try:
        result = llm_service.complete_structured(
            messages, QueryRewriterResponse, model=llm_service.fast_model, temperature=0.1
        )
        logger.info(f"[QueryRewriter] rewritten='{result.rewritten_query}'")
        if metrics:
            metrics.rewritten_queries.append(result.rewritten_query)
        return result
    except Exception as e:
        logger.warning(f"[QueryRewriter] failed: {e}. Using original.")
        return QueryRewriterResponse(
            rewritten_query=query,
            search_queries=[query],
            reasoning="Rewriter failed — using original query.",
        )


# ── 4. Search Agent ───────────────────────────────────────────────────────────

async def run_search_agent(
    query: str,
    rewritten: Optional[QueryRewriterResponse] = None,
    metrics: Optional[ObservabilityMetrics] = None,
) -> List[Dict[str, Any]]:
    """
    Runs concurrent Tavily searches for all generated queries.
    Returns deduplicated results with source metadata.
    """
    logger.info(f"[Search] query='{query}'")

    queries = rewritten.search_queries[:3] if rewritten else [query]
    logger.info(f"[Search] executing {len(queries)} queries concurrently: {queries}")

    async def _fetch(q: str) -> List[Dict[str, Any]]:
        results = await tavily_client.search_async(q, max_results=3)
        if metrics:
            metrics.tavily_calls += 1
        return results

    all_results = await asyncio.gather(*[_fetch(q) for q in queries], return_exceptions=True)

    seen_urls: set = set()
    aggregated: List[Dict[str, Any]] = []
    for batch in all_results:
        if isinstance(batch, Exception):
            logger.error(f"[Search] batch error: {batch}")
            continue
        for r in batch:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                aggregated.append(r)

    logger.info(f"[Search] aggregated {len(aggregated)} unique results.")
    return aggregated


# ── 5. RAG Retrieval Agent ────────────────────────────────────────────────────

def run_rag_agent(
    query: str,
    session_id: str,
    top_k: int = 10,
    rewritten: Optional[QueryRewriterResponse] = None,
    metrics: Optional[ObservabilityMetrics] = None,
) -> List[RetrievedChunk]:
    """Retrieves chunks using the rewritten query if available."""
    effective_query = rewritten.rewritten_query if rewritten else query
    logger.info(f"[RAG] session='{session_id}' query='{effective_query}'")
    store = get_session_store(session_id)
    results = store.search(effective_query, top_k=top_k)
    if metrics:
        metrics.rag_chunks_retrieved += len(results)
    logger.info(f"[RAG] retrieved {len(results)} chunks above threshold.")
    return results


# ── 6. Summarizer Agent ───────────────────────────────────────────────────────

def run_summarizer_agent(
    section_title: str,
    section_desc: str,
    contexts: List[Dict[str, Any]],
) -> str:
    """
    Synthesizes retrieved context into a fact-oriented summary.
    Context is token-budgeted before the LLM call.
    """
    logger.info(f"[Summarizer] section='{section_title}'")

    context_str = _build_context_block(contexts, max_tokens=MAX_CONTEXT_TOKENS)

    system_prompt = (
        "You are a Research Summarizer Agent.\n"
        f"Topic: '{section_title}'\nDescription: '{section_desc}'\n\n"
        "Guidelines:\n"
        "1. Synthesize factual findings from the provided sources.\n"
        "2. Tag every fact with its Source ID: e.g. [Source ID: 3].\n"
        "3. Do not invent facts. If evidence is missing, say so.\n"
        "4. Be comprehensive but concise."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Retrieved Contexts:\n\n{context_str}"},
    ]
    return llm_service.complete(messages, temperature=0.2, max_tokens=2500)


# ── 7. Section Writer Agent ───────────────────────────────────────────────────

async def run_section_writer_agent_async(
    section_title: str,
    section_desc: str,
    summarized_context: str,
    citation_ids: List[int],
    length: str,
) -> Tuple[str, List[int], float]:
    """
    Async section writer. Returns (content, cited_ids, confidence_score).
    Uses regex for deterministic citation extraction.
    """
    import time as _time
    t0 = _time.monotonic()
    logger.info(f"[SectionWriter] section='{section_title}'")

    length_instruction = {
        "Short": "Write a concise section of 250–400 words.",
        "Medium": "Write a balanced section of 400–600 words.",
        "Detailed": "Write an exhaustive section of 600–900 words with deep analysis.",
    }.get(length, "Write 400–600 words.")

    # Truncate summarized context to output budget
    context_budgeted = _truncate_to_budget(summarized_context, MAX_CONTEXT_TOKENS)

    system_prompt = (
        "You are a Senior Research Analyst writing one section of a professional report.\n\n"
        "RULES:\n"
        "1. Formal, objective, analytical tone.\n"
        "2. Use inline citations [N] where N is the Source ID from the context.\n"
        "3. Translate [Source ID: N] references directly to [N] in your text.\n"
        "4. Only use citation numbers that appear in the provided context.\n"
        "5. No boilerplate. No generic filler.\n"
        f"6. {length_instruction}"
    )
    user_prompt = (
        f"Section: {section_title}\n"
        f"Goal: {section_desc}\n\n"
        f"Summarized Context:\n{context_budgeted}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Run sync LLM call in thread pool to not block event loop
    loop = asyncio.get_event_loop()
    section_body = await loop.run_in_executor(
        None,
        lambda: llm_service.complete(messages, temperature=0.2, max_tokens=MAX_OUTPUT_TOKENS),
    )

    # Deterministic citation extraction via regex
    found_ids = set(int(m) for m in re.findall(r"\[(\d+)\]", section_body))
    valid_ids = sorted(found_ids.intersection(set(citation_ids)))

    # Confidence: ratio of available citations actually used
    confidence = round(len(valid_ids) / max(len(citation_ids), 1), 2)
    confidence = min(confidence + 0.3, 1.0)  # base floor

    latency_ms = round((_time.monotonic() - t0) * 1000, 1)
    return section_body, valid_ids, confidence, latency_ms


# ── 8. Validator Agent ────────────────────────────────────────────────────────

def run_validator_agent(
    sections_data: List[Dict[str, Any]],
    citations: List[Citation],
    retrieved_chunks: Optional[List[RetrievedChunk]] = None,
) -> ValidatorResponse:
    """
    Validates report sections against source evidence.
    Receives full retrieval scores for richer audit.
    """
    logger.info("[Validator] running audit...")

    sections_text = _truncate_to_budget(
        "\n\n".join(f"## {s['title']}\n{s['content']}" for s in sections_data),
        MAX_CONTEXT_TOKENS // 2,
    )

    # Build citation evidence block with scores
    cit_lines = []
    for c in citations:
        score_info = ""
        if c.retrieval_scores:
            score_info = (
                f" [hybrid={c.retrieval_scores.hybrid_score:.3f} "
                f"v={c.retrieval_scores.vector_score:.3f} "
                f"bm25={c.retrieval_scores.bm25_score:.3f}]"
            )
        cit_lines.append(
            f"[{c.citation_id}] {c.source_name} ({c.source_type}){score_info}\n"
            f"  Snippet: {c.snippet[:300]}"
        )
    citations_text = _truncate_to_budget("\n".join(cit_lines), MAX_CONTEXT_TOKENS // 2)

    system_prompt = (
        "You are a Validator Agent auditing a research report.\n"
        "For each finding classify as:\n"
        "- VERIFIED: claim is clearly supported by the cited source.\n"
        "- WEAK_EVIDENCE: claim is loosely supported or source is low-confidence.\n"
        "- CONTRADICTION: claim contradicts the cited source.\n\n"
        "Also assign a confidence_score [0.0–1.0] per finding.\n"
        "Give an overall_integrity_score [0.0–10.0]."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Report Sections:\n{sections_text}\n\n"
                f"Source Evidence:\n{citations_text}"
            ),
        },
    ]
    try:
        return llm_service.complete_structured(messages, ValidatorResponse, temperature=0.1)
    except Exception as e:
        logger.error(f"[Validator] failed: {e}")
        return ValidatorResponse(
            overall_integrity_score=5.0,
            findings=[
                ValidatorFinding(
                    finding_type="WEAK_EVIDENCE",
                    source="System",
                    description="Validator agent failed to complete audit.",
                    confidence_score=0.0,
                )
            ],
        )


# ── 9. Risk Analysis Agent ────────────────────────────────────────────────────

def run_risk_analysis_agent(
    query: str,
    sections_data: List[Dict[str, Any]],
    citations: Optional[List[Citation]] = None,
) -> RiskAnalysisResponse:
    """
    Risk analysis operates on validated evidence (citations) + section content.
    """
    logger.info("[RiskAnalysis] running...")

    sections_text = _truncate_to_budget(
        "\n\n".join(f"## {s['title']}\n{s['content']}" for s in sections_data),
        MAX_CONTEXT_TOKENS // 2,
    )

    evidence_text = ""
    if citations:
        evidence_lines = [
            f"[{c.citation_id}] {c.source_name}: {c.snippet[:200]}"
            for c in citations[:20]
        ]
        evidence_text = "\n\nValidated Evidence:\n" + "\n".join(evidence_lines)

    system_prompt = (
        "You are a Risk Analysis Agent.\n"
        "Identify structural risks, challenges, and threats from the research findings.\n"
        "Classify each as LOW, MEDIUM, or HIGH.\n"
        "Assign a confidence_score [0.0–1.0] per risk.\n"
        "Base risks on the validated evidence, not just the prose."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Research Topic: {query}\n\n"
                f"Findings:\n{sections_text}"
                f"{evidence_text}"
            ),
        },
    ]
    try:
        return llm_service.complete_structured(messages, RiskAnalysisResponse, temperature=0.2)
    except Exception as e:
        logger.error(f"[RiskAnalysis] failed: {e}")
        return RiskAnalysisResponse(
            summary="Risk analysis could not be completed.",
            risks=[
                RiskItem(
                    level="MEDIUM",
                    impact="Risk analysis agent failed.",
                    mitigation="Review logs.",
                    confidence_score=0.0,
                )
            ],
        )


# ── 10. Report Compiler Agent ─────────────────────────────────────────────────

def run_report_compiler_agent(
    query: str,
    title: str,
    rewritten_query: str,
    sections: List[ReportSection],
    risk_assessment: RiskAnalysisResponse,
    validation: ValidatorResponse,
    citations: List[Citation],
    metrics: Optional[ObservabilityMetrics] = None,
) -> FinalReport:
    """Assembles all components and generates the executive summary."""
    logger.info("[Compiler] assembling final report...")

    sections_text = _truncate_to_budget(
        "\n\n".join(f"## {s.title}\n{s.content}" for s in sections),
        MAX_CONTEXT_TOKENS,
    )
    system_prompt = (
        "You are a Report Compiler Agent.\n"
        "Write a professional Executive Summary (2–3 paragraphs) covering:\n"
        "- Primary findings\n- Key risks\n- Conclusions\n"
        "Return ONLY the summary text. No headers, no greetings."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Topic: {query}\nTitle: {title}\n\nSections:\n{sections_text}",
        },
    ]
    exec_summary = llm_service.complete(messages, temperature=0.2, max_tokens=1000)

    return FinalReport(
        id=str(uuid.uuid4())[:8],
        query=query,
        title=title,
        rewritten_query=rewritten_query,
        executive_summary=exec_summary.strip(),
        sections=sections,
        risk_assessment=risk_assessment,
        validation=validation,
        citations=citations,
        metrics=metrics,
        created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
