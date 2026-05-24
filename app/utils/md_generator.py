from pathlib import Path
from app.models.schemas import FinalReport
from app.utils.config import logger


def generate_report_md(report: FinalReport, output_path: Path) -> None:
    """Generate a professional Markdown report with confidence scores and retrieval metadata."""
    try:
        lines = []

        # ── Header ────────────────────────────────────────────────────────────
        lines += [
            f"# {report.title.upper()}",
            "",
            f"**Research Topic:** {report.query}  ",
            f"**Rewritten Query:** {report.rewritten_query or 'N/A'}  ",
            f"**Report ID:** `{report.id}`  ",
            f"**Date Compiled:** {report.created_at}  ",
            f"**Integrity Score:** {report.validation.overall_integrity_score} / 10.0  ",
            f"**Sources Referenced:** {len(report.citations)}  ",
            "",
            "---",
            "",
        ]

        # ── Observability summary ─────────────────────────────────────────────
        if report.metrics:
            m = report.metrics
            lines += [
                "## Observability Metrics",
                "",
                f"| Metric | Value |",
                f"| :--- | :--- |",
                f"| Total Latency | {m.total_latency_ms:.0f} ms |",
                f"| LLM Calls | {m.llm_calls} |",
                f"| Tavily Calls | {m.tavily_calls} |",
                f"| RAG Chunks Retrieved | {m.rag_chunks_retrieved} |",
                f"| Retry Count | {m.retry_count} |",
                "",
                "---",
                "",
            ]

        # ── Executive Summary ─────────────────────────────────────────────────
        lines += [
            "## Executive Summary",
            "",
            report.executive_summary,
            "",
            "---",
            "",
        ]

        # ── Sections ──────────────────────────────────────────────────────────
        for sec in report.sections:
            conf_str = f" *(confidence: {sec.confidence_score:.0%})*" if sec.confidence_score else ""
            latency_str = f" *[{sec.generation_latency_ms:.0f}ms]*" if sec.generation_latency_ms else ""
            lines += [
                f"## {sec.title}{conf_str}{latency_str}",
                "",
                sec.content,
                "",
            ]

        lines += ["---", ""]

        # ── Risks ─────────────────────────────────────────────────────────────
        lines += [
            "## Risks & Challenges Assessment",
            "",
            report.risk_assessment.summary,
            "",
            "| Level | Confidence | Impact / Threat | Mitigation |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for risk in report.risk_assessment.risks:
            mit = (risk.mitigation or "N/A").replace("|", "\\|")
            impact = risk.impact.replace("|", "\\|")
            conf = f"{risk.confidence_score:.0%}" if hasattr(risk, "confidence_score") else "—"
            lines.append(f"| **{risk.level}** | {conf} | {impact} | {mit} |")

        lines += ["", "---", ""]

        # ── Validation ────────────────────────────────────────────────────────
        lines += [
            "## Source Validation & Integrity Audit",
            "",
            f"**Integrity Score:** {report.validation.overall_integrity_score} / 10.0  ",
            "",
        ]
        for f in report.validation.findings:
            conf = getattr(f, "confidence_score", None)
            conf_str = f" *(confidence: {conf:.0%})*" if conf is not None else ""
            cit_str = f" — citations: {f.citation_ids}" if getattr(f, "citation_ids", None) else ""
            lines += [
                f"- **[{f.finding_type}]**{conf_str}  ",
                f"  *Source:* {f.source}{cit_str}  ",
                f"  {f.description}  ",
                "",
            ]

        lines += ["---", ""]

        # ── Citations ─────────────────────────────────────────────────────────
        lines += ["## Appendix: Sources & Citations", ""]
        for cit in report.citations:
            desc = f"**[{cit.citation_id}]** {cit.source_name} (*{cit.source_type.upper()}*)"
            if cit.page:
                desc += f" — Page {cit.page}"
            elif cit.url:
                desc += f" — [{cit.url}]({cit.url})"

            score_parts = []
            if cit.retrieval_scores:
                s = cit.retrieval_scores
                score_parts.append(
                    f"hybrid={s.hybrid_score:.3f} v={s.vector_score:.3f} bm25={s.bm25_score:.3f}"
                )
            if cit.extraction_method:
                score_parts.append(cit.extraction_method)
            if cit.confidence_score is not None:
                score_parts.append(f"conf={cit.confidence_score:.2f}")

            if score_parts:
                desc += f" `[{' | '.join(score_parts)}]`"

            lines += [
                desc,
                f"> \"{cit.snippet.strip()[:300]}\"",
                "",
            ]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"Markdown report saved: {output_path}")

    except Exception as e:
        logger.error(f"Markdown generation failed: {e}")
        raise
