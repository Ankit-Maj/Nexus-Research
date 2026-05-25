"""
Research workflow orchestrator.

Staged execution:
  1. Router
  2. Planner
  3. Query Rewriter
  4. Parallel retrieval (Tavily + RAG concurrently)
  5. Source deduplication + citation assignment
  6. Parallel section writing (all sections concurrently)
  7. Validator (on written sections + full citations with scores)
  8. Risk Analysis (on validated evidence)
  9. Report Compiler

All agent calls are isolated — orchestrator owns sequencing.
"""

import asyncio
import time
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple

from app.utils.config import logger, REPORT_DIR, MAX_SECTION_CONTEXTS, MIN_HYBRID_SCORE
from app.models.schemas import (
    StreamEvent,
    TraceMessage,
    ReportSection,
    Citation,
    FinalReport,
    ValidatorResponse,
    RiskAnalysisResponse,
    RetrievedChunk,
    ObservabilityMetrics,
    OutlineSection,
    PlannerOutlineResponse,
    RetrievalScore,
)
from app.agents.definitions import (
    run_router_agent,
    run_planner_agent,
    run_query_rewriter_agent,
    run_search_agent,
    run_rag_agent,
    run_summarizer_agent,
    run_section_writer_agent_async,
    run_risk_analysis_agent,
    run_validator_agent,
    run_report_compiler_agent,
)
from app.utils.md_generator import generate_report_md
from app.services.database import append_trace

# ── In-memory stores ──────────────────────────────────────────────────────────
session_traces: Dict[str, List[Dict[str, Any]]] = {}
compiled_reports: Dict[str, FinalReport] = {}


# ── Trace helpers ─────────────────────────────────────────────────────────────

def _make_trace(
    session_id: str,
    agent_name: str,
    status: str,
    message: str,
    data: Any = None,
    event_type: str = "agent_update",
) -> Dict[str, Any]:
    trace = {
        "event_type": event_type,
        "timestamp": time.strftime("%H:%M:%S"),
        "agent_name": agent_name,
        "status": status,
        "message": message,
        "data": data,
    }
    session_traces.setdefault(session_id, []).append(trace)
    logger.info(f"[{agent_name}] {message}")
    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(append_trace(session_id, trace))
    except RuntimeError:
        pass  # no running loop — skip DB persistence
    except Exception:
        pass
    return trace


def _sse(trace: Dict[str, Any]) -> str:
    return f"data: {json.dumps(trace)}\n\n"


def get_traces(session_id: str) -> List[Dict[str, Any]]:
    return session_traces.get(session_id, [])


# ── Source processing helpers ─────────────────────────────────────────────────

def _build_citation_pool(
    web_candidates: List[Dict[str, Any]],
    rag_candidates: List[RetrievedChunk],
) -> Tuple[List[Dict[str, Any]], List[Citation]]:
    """
    Deduplicate and assign sequential citation IDs.
    Returns (all_sources_list, citation_list).
    all_sources_list entries carry full score metadata for context building.
    """
    all_sources: List[Dict[str, Any]] = []
    citation_list: List[Citation] = []
    seen: Dict[str, int] = {}

    for w in web_candidates:
        url = w.get("url", "")
        key = f"web:{url}"
        if key in seen:
            continue
        cit_id = len(seen) + 1
        seen[key] = cit_id
        citation_list.append(
            Citation(
                citation_id=cit_id,
                source_name=w.get("title", "Web Source"),
                source_type="web",
                url=url,
                snippet=w.get("content", "")[:500],
                confidence_score=round(float(w.get("score", 0.5)), 3),
                extraction_method="DIRECT",
            )
        )
        all_sources.append({
            "citation_id": cit_id,
            "source_name": w.get("title", "Web Source"),
            "source_type": "web",
            "content": w.get("content", ""),
            "url": url,
            "hybrid_score": float(w.get("score", 0.5)),
            "vector_score": 0.0,
            "bm25_score": 0.0,
            "extraction_method": "DIRECT",
        })

    for chunk in rag_candidates:
        meta = chunk.metadata
        page = meta.page
        key = (
            f"doc:{meta.source_name}:p{page}"
            if page
            else f"doc:{meta.source_name}:c{meta.chunk_index}"
        )
        if key in seen:
            continue
        cit_id = len(seen) + 1
        seen[key] = cit_id
        scores = chunk.scores
        citation_list.append(
            Citation(
                citation_id=cit_id,
                source_name=meta.source_name,
                source_type=meta.source_type,
                page=page,
                url=meta.url,
                snippet=chunk.text[:500],
                confidence_score=round(scores.hybrid_score, 3),
                extraction_method=meta.extraction_method,
                retrieval_scores=scores,
            )
        )
        all_sources.append({
            "citation_id": cit_id,
            "source_name": meta.source_name,
            "source_type": meta.source_type,
            "content": chunk.text,
            "page": page,
            "url": meta.url,
            "hybrid_score": scores.hybrid_score,
            "vector_score": scores.vector_score,
            "bm25_score": scores.bm25_score,
            "extraction_method": meta.extraction_method,
        })

    return all_sources, citation_list


def _select_section_sources(
    section: OutlineSection,
    all_sources: List[Dict[str, Any]],
    max_sources: int = MAX_SECTION_CONTEXTS,
) -> List[Dict[str, Any]]:
    """
    Select the most relevant sources for a section.
    Combines keyword overlap with hybrid retrieval score.
    """
    focus = f"{section.title} {section.description} {section.retrieval_focus}"
    focus_tokens = set(focus.lower().split())

    scored = []
    for src in all_sources:
        content_tokens = set(src["content"].lower().split())
        overlap = len(focus_tokens & content_tokens) / max(len(focus_tokens), 1)
        combined = 0.6 * src.get("hybrid_score", 0.0) + 0.4 * overlap
        scored.append((combined, src))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in scored[:max_sources]]


# ── Main workflow ─────────────────────────────────────────────────────────────

async def run_research_workflow(
    query: str,
    retrieval_mode: str,
    length: str,
    session_id: str,
    uploads_exist: bool,
) -> AsyncGenerator[str, None]:
    """
    Staged multi-agent research workflow with SSE streaming.
    """
    t_start = time.monotonic()
    metrics = ObservabilityMetrics(session_id=session_id)

    # ── 1. Router ─────────────────────────────────────────────────────────────
    yield _sse(_make_trace(session_id, "Router Agent", "started", f'Routing query: "{query}"'))
    await asyncio.sleep(0)

    try:
        if retrieval_mode == "AUTO":
            router_res = run_router_agent(query, uploads_exist)
            route, reasoning = router_res.route, router_res.reasoning
        else:
            route = retrieval_mode
            reasoning = f"Manual mode: {retrieval_mode}."
        yield _sse(_make_trace(
            session_id, "Router Agent", "completed",
            f"Route: {route}. {reasoning}",
            {"route": route},
        ))
    except Exception as e:
        route = "WEB" if not uploads_exist else "HYBRID"
        yield _sse(_make_trace(session_id, "Router Agent", "error", f"Router failed → {route}: {e}"))

    await asyncio.sleep(0)

    # ── 2. Planner ────────────────────────────────────────────────────────────
    yield _sse(_make_trace(session_id, "Planner Agent", "started", "Generating report outline..."))
    await asyncio.sleep(0)

    try:
        outline_res = run_planner_agent(query, length)
        yield _sse(_make_trace(
            session_id, "Planner Agent", "completed",
            f'Outline: "{outline_res.title}" ({len(outline_res.sections)} sections)',
            {"outline": outline_res.model_dump()},
        ))
    except Exception as e:
        logger.error(f"Planner failed: {e}")
        from app.models.schemas import OutlineSection
        outline_res = PlannerOutlineResponse(
            title=f"Research Report: {query}",
            sections=[
                OutlineSection(title="Overview", description="General overview", priority=1),
                OutlineSection(title="Key Findings", description="Core findings", priority=2),
                OutlineSection(title="Strategic Outlook", description="Future outlook", priority=3),
            ],
        )
        yield _sse(_make_trace(session_id, "Planner Agent", "warning", "Planner failed — using fallback outline."))

    await asyncio.sleep(0)

    # ── 3. Query Rewriter ─────────────────────────────────────────────────────
    yield _sse(_make_trace(session_id, "Query Rewriter Agent", "started", "Rewriting query for optimal retrieval..."))
    await asyncio.sleep(0)

    loop = asyncio.get_running_loop()
    rewritten = await loop.run_in_executor(
        None, lambda: run_query_rewriter_agent(query, metrics=metrics)
    )
    metrics.llm_calls += 1
    yield _sse(_make_trace(
        session_id, "Query Rewriter Agent", "completed",
        f'Rewritten: "{rewritten.rewritten_query}"',
        {"rewritten_query": rewritten.rewritten_query, "search_queries": rewritten.search_queries},
        event_type="retrieval_update",
    ))

    await asyncio.sleep(0)

    # ── 4. Parallel Retrieval ─────────────────────────────────────────────────
    web_candidates: List[Dict[str, Any]] = []
    rag_candidates: List[RetrievedChunk] = []

    retrieval_tasks = []
    if route in ("WEB", "HYBRID"):
        retrieval_tasks.append(("web", run_search_agent(query, rewritten, metrics)))
    if route in ("RAG", "HYBRID") and uploads_exist:
        retrieval_tasks.append(("rag", asyncio.get_running_loop().run_in_executor(
            None, lambda: run_rag_agent(query, session_id, top_k=10, rewritten=rewritten, metrics=metrics)
        )))

    if retrieval_tasks:
        yield _sse(_make_trace(
            session_id, "Retrieval Agent", "started",
            f"Running {len(retrieval_tasks)} retrieval task(s) concurrently...",
            event_type="retrieval_update",
        ))
        await asyncio.sleep(0)

        results = await asyncio.gather(*[t for _, t in retrieval_tasks], return_exceptions=True)

        for (rtype, _), result in zip(retrieval_tasks, results):
            if isinstance(result, Exception):
                yield _sse(_make_trace(session_id, "Retrieval Agent", "error", f"{rtype} retrieval failed: {result}"))
            elif rtype == "web":
                web_candidates = result
                yield _sse(_make_trace(
                    session_id, "Search Agent", "completed",
                    f"Retrieved {len(web_candidates)} web results.",
                    event_type="retrieval_update",
                ))
            elif rtype == "rag":
                rag_candidates = result
                yield _sse(_make_trace(
                    session_id, "RAG Retrieval Agent", "completed",
                    f"Retrieved {len(rag_candidates)} document chunks (above threshold).",
                    event_type="retrieval_update",
                ))

    await asyncio.sleep(0)

    # ── 5. Build citation pool ────────────────────────────────────────────────
    all_sources, citation_list = _build_citation_pool(web_candidates, rag_candidates)
    yield _sse(_make_trace(
        session_id, "Orchestrator", "info",
        f"Citation pool: {len(citation_list)} unique sources.",
        {"total_sources": len(citation_list)},
    ))
    await asyncio.sleep(0)

    # ── 6. Parallel Section Writing ───────────────────────────────────────────
    yield _sse(_make_trace(
        session_id, "Section Writer Agent", "started",
        f"Writing {len(outline_res.sections)} sections in parallel...",
        event_type="section_complete",
    ))
    await asyncio.sleep(0)

    async def _write_section(
        i: int, sec: OutlineSection
    ) -> Tuple[int, ReportSection, Exception | None]:
        try:
            section_sources = _select_section_sources(sec, all_sources)
            section_cit_ids = [s["citation_id"] for s in section_sources]

            summarized = await loop.run_in_executor(
                None,
                lambda: run_summarizer_agent(sec.title, sec.description, section_sources),
            )
            metrics.llm_calls += 1

            body, refs, confidence, latency_ms = await run_section_writer_agent_async(
                sec.title, sec.description, summarized, section_cit_ids, length
            )
            metrics.llm_calls += 1
            metrics.section_latencies_ms[sec.title] = latency_ms

            return i, ReportSection(
                title=sec.title,
                content=body,
                citations=refs,
                confidence_score=confidence,
                generation_latency_ms=latency_ms,
            ), None
        except Exception as e:
            return i, ReportSection(
                title=sec.title,
                content=f"Section generation failed: {e}",
                citations=[],
                confidence_score=0.0,
            ), e

    section_tasks = [_write_section(i, sec) for i, sec in enumerate(outline_res.sections)]
    section_results_raw = await asyncio.gather(*section_tasks)

    # Sort back to original order and stream completions
    section_results_raw = sorted(section_results_raw, key=lambda x: x[0])
    written_sections: List[ReportSection] = []

    for i, section, err in section_results_raw:
        written_sections.append(section)
        if err:
            yield _sse(_make_trace(
                session_id, "Section Writer Agent", "error",
                f'Section "{section.title}" failed: {err}',
                event_type="section_complete",
            ))
        else:
            yield _sse(_make_trace(
                session_id, "Section Writer Agent", "completed",
                f'Section {i + 1}/{len(outline_res.sections)}: "{section.title}" '
                f'(confidence={section.confidence_score:.2f}, {section.generation_latency_ms:.0f}ms)',
                {
                    "section_title": section.title,
                    "confidence": section.confidence_score,
                    "latency_ms": section.generation_latency_ms,
                },
                event_type="section_complete",
            ))
        await asyncio.sleep(0)

    # ── 7. Validator ──────────────────────────────────────────────────────────
    yield _sse(_make_trace(session_id, "Validator Agent", "started", "Auditing report integrity..."))
    await asyncio.sleep(0)

    sections_json = [s.model_dump() for s in written_sections]
    try:
        validator_res = await loop.run_in_executor(
            None,
            lambda: run_validator_agent(sections_json, citation_list, rag_candidates or None),
        )
        metrics.llm_calls += 1
        yield _sse(_make_trace(
            session_id, "Validator Agent", "completed",
            f"Integrity score: {validator_res.overall_integrity_score}/10.0 | "
            f"{len(validator_res.findings)} findings.",
            {"integrity_score": validator_res.overall_integrity_score},
        ))
    except Exception as e:
        from app.models.schemas import ValidatorFinding
        validator_res = ValidatorResponse(
            overall_integrity_score=5.0,
            findings=[ValidatorFinding(
                finding_type="WEAK_EVIDENCE", source="System",
                description=f"Validator failed: {e}", confidence_score=0.0,
            )],
        )
        yield _sse(_make_trace(session_id, "Validator Agent", "error", f"Validator failed: {e}"))

    await asyncio.sleep(0)

    # ── 8. Risk Analysis ──────────────────────────────────────────────────────
    yield _sse(_make_trace(session_id, "Risk Analysis Agent", "started", "Assessing risks from validated evidence..."))
    await asyncio.sleep(0)

    try:
        risk_res = await loop.run_in_executor(
            None,
            lambda: run_risk_analysis_agent(query, sections_json, citation_list),
        )
        metrics.llm_calls += 1
        yield _sse(_make_trace(
            session_id, "Risk Analysis Agent", "completed",
            f"Found {len(risk_res.risks)} risks.",
            {"risk_count": len(risk_res.risks)},
        ))
    except Exception as e:
        from app.models.schemas import RiskItem
        risk_res = RiskAnalysisResponse(
            summary="Risk analysis failed.",
            risks=[RiskItem(level="MEDIUM", impact=f"Agent failed: {e}", confidence_score=0.0)],
        )
        yield _sse(_make_trace(session_id, "Risk Analysis Agent", "error", f"Risk analysis failed: {e}"))

    await asyncio.sleep(0)

    # ── 9. Report Compiler ────────────────────────────────────────────────────
    yield _sse(_make_trace(
        session_id, "Report Compiler Agent", "started",
        "Assembling final report and executive summary...",
        event_type="compiler_status",
    ))
    await asyncio.sleep(0)

    try:
        metrics.total_latency_ms = round((time.monotonic() - t_start) * 1000, 1)

        final_report = await loop.run_in_executor(
            None,
            lambda: run_report_compiler_agent(
                query=query,
                title=outline_res.title,
                rewritten_query=rewritten.rewritten_query,
                sections=written_sections,
                risk_assessment=risk_res,
                validation=validator_res,
                citations=citation_list,
                metrics=metrics,
            ),
        )
        metrics.llm_calls += 1

        # Persist JSON + Markdown
        compiled_reports[final_report.id] = final_report
        report_path = REPORT_DIR / f"{final_report.id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(final_report.model_dump_json(indent=2))

        try:
            md_path = REPORT_DIR / f"{final_report.id}.md"
            generate_report_md(final_report, md_path)
        except Exception as md_err:
            logger.error(f"Markdown generation failed: {md_err}")

        # Emit final report event
        yield f"event: report\ndata: {final_report.model_dump_json()}\n\n"

        yield _sse(_make_trace(
            session_id, "Report Compiler Agent", "completed",
            f"Report compiled. ID: {final_report.id} | "
            f"Latency: {metrics.total_latency_ms:.0f}ms | "
            f"LLM calls: {metrics.llm_calls}",
            {
                "report_id": final_report.id,
                "total_latency_ms": metrics.total_latency_ms,
                "llm_calls": metrics.llm_calls,
                "tavily_calls": metrics.tavily_calls,
            },
            event_type="compiler_status",
        ))

    except Exception as e:
        logger.error(f"Report Compiler failed: {e}")
        yield _sse(_make_trace(
            session_id, "Report Compiler Agent", "error",
            f"Compiler failed: {e}",
            event_type="compiler_status",
        ))
