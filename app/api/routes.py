import os
import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse, FileResponse
from jose import JWTError, jwt

from app.utils.config import logger, UPLOAD_DIR, REPORT_DIR, JWT_SECRET_KEY, JWT_ALGORITHM
from app.models.schemas import ResearchRequest, ChunkResponse, TraceMessage
from app.rag.parser import parse_document
from app.rag.retriever import get_session_store, delete_session_store, cleanup_expired_sessions
from app.workflows.orchestrator import run_research_workflow, get_traces, compiled_reports
from app.services.auth import get_current_user, get_current_user_optional
from app.services.database import (
    upsert_session,
    save_report,
    get_report,
    get_reports_for_user,
    get_sessions_for_user,
    get_traces_db,
)

router = APIRouter()

# In-process citation + chunk cache: f"{report_id}_{citation_id}" -> ChunkResponse dict
citation_cache: dict = {}
# Retrieval inspector cache: session_id -> list of RetrievedChunk dicts
retrieval_cache: dict = {}


# ── Upload ────────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_files(
    session_id: str = Form("default_session"),
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    session_upload_dir = UPLOAD_DIR / session_id
    session_upload_dir.mkdir(parents=True, exist_ok=True)
    store = get_session_store(session_id)
    ingested_files = []

    for file in files:
        suffix = Path(file.filename).suffix.lower()
        if suffix not in [".pdf", ".docx", ".txt", ".md"]:
            logger.warning(f"Ignored unsupported file: {file.filename}")
            continue

        file_path = session_upload_dir / file.filename
        try:
            with open(file_path, "wb") as f:
                f.write(await file.read())

            # parse_document now returns (text, extraction_method)
            text_content, extraction_method = parse_document(file_path)
            if not text_content.strip():
                logger.warning(f"'{file.filename}' parsed but returned no text.")

            store.add_document(
                source_name=file.filename,
                content=text_content,
                source_type="document",
                metadata={"file_path": str(file_path)},
                extraction_method=extraction_method,
            )
            ingested_files.append(file.filename)
        except Exception as e:
            logger.error(f"Failed to ingest '{file.filename}': {e}")

    if not ingested_files:
        raise HTTPException(
            status_code=400,
            detail="Failed to ingest any files. Ensure format is PDF, TXT, MD, or DOCX.",
        )

    await upsert_session(session_id, current_user["username"], {"files": ingested_files})

    return {
        "status": "success",
        "session_id": session_id,
        "files": ingested_files,
        "message": f"Ingested {len(ingested_files)} file(s).",
    }


# ── Research ──────────────────────────────────────────────────────────────────

@router.post("/research")
async def trigger_research(
    request: ResearchRequest,
    current_user: dict = Depends(get_current_user),
):
    session_id = request.session_id
    store = get_session_store(session_id)
    uploads_exist = len(store.chunks) > 0

    if request.retrieval_mode == "RAG" and not uploads_exist:
        raise HTTPException(
            status_code=400,
            detail="RAG mode selected but no documents uploaded.",
        )

    username = current_user["username"]

    async def event_generator():
        async for event in run_research_workflow(
            query=request.query,
            retrieval_mode=request.retrieval_mode,
            length=request.length,
            session_id=session_id,
            uploads_exist=uploads_exist,
        ):
            if event.startswith("event: report"):
                try:
                    report_json_str = event.split("\ndata: ")[1].strip()
                    report_data = json.loads(report_json_str)
                    report_id = report_data.get("id")

                    # Populate citation cache with full score metadata
                    for cit in report_data.get("citations", []):
                        cit_id = cit.get("citation_id")
                        key = f"{report_id}_{cit_id}"
                        scores = cit.get("retrieval_scores") or {}
                        citation_cache[key] = {
                            "chunk_id": f"chunk_{key}",
                            "content": cit.get("snippet", ""),
                            "score": cit.get("confidence_score", 1.0),
                            "vector_score": scores.get("vector_score", 0.0),
                            "bm25_score": scores.get("bm25_score", 0.0),
                            "source_name": cit.get("source_name", "Unknown"),
                            "source_type": cit.get("source_type", "document"),
                            "retrieval_rank": cit_id,
                            "extraction_method": cit.get("extraction_method", "DIRECT"),
                            "metadata": {
                                "page": cit.get("page"),
                                "url": cit.get("url"),
                            },
                        }

                    await save_report(report_id, session_id, username, report_data)
                    await upsert_session(session_id, username, {"last_report_id": report_id})

                except Exception as ex:
                    logger.error(f"Error caching/persisting report: {ex}")

            yield event

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ── Download ──────────────────────────────────────────────────────────────────

@router.get("/download/{report_id}")
async def download_report_md(
    report_id: str,
    token: Optional[str] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    if not current_user and token:
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            if not payload.get("sub"):
                raise HTTPException(status_code=401, detail="Invalid token.")
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token.")
    elif not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    md_path = REPORT_DIR / f"{report_id}.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    return FileResponse(
        path=md_path,
        filename=f"AI_Research_Report_{report_id}.md",
        media_type="text/markdown",
    )


# ── Citation source viewer ────────────────────────────────────────────────────

@router.get("/sources/{source_id}")
async def get_source_details(
    source_id: str,
    current_user: dict = Depends(get_current_user),
):
    if source_id not in citation_cache:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
    return citation_cache[source_id]


# ── Retrieval Inspector ───────────────────────────────────────────────────────

@router.get("/retrieval/{session_id}")
async def get_retrieval_inspector(
    session_id: str,
    query: str = Query(..., description="Query to inspect retrieval for"),
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    """
    Run a live retrieval query against the session store and return
    full chunk details including vector/BM25/hybrid scores, rank, and extraction method.
    """
    store = get_session_store(session_id)
    if not store.chunks:
        raise HTTPException(status_code=404, detail="No documents indexed for this session.")

    chunks = store.search(query, top_k=top_k)
    return [
        {
            "chunk_id": c.chunk_id,
            "text_preview": c.text[:300],
            "retrieval_rank": c.retrieval_rank,
            "vector_score": c.scores.vector_score,
            "bm25_score": c.scores.bm25_score,
            "hybrid_score": c.scores.hybrid_score,
            "source_name": c.metadata.source_name,
            "source_type": c.metadata.source_type,
            "page": c.metadata.page,
            "url": c.metadata.url,
            "extraction_method": c.metadata.extraction_method,
            "chunk_index": c.metadata.chunk_index,
        }
        for c in chunks
    ]


# ── Observability ─────────────────────────────────────────────────────────────

@router.get("/metrics/{report_id}")
async def get_report_metrics(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return observability metrics for a compiled report."""
    report = compiled_reports.get(report_id)
    if not report:
        doc = await get_report(report_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
        metrics = doc.get("data", {}).get("metrics")
        return metrics or {"message": "No metrics recorded for this report."}
    if report.metrics:
        return report.metrics.model_dump()
    return {"message": "No metrics recorded for this report."}


# ── Traces ────────────────────────────────────────────────────────────────────

@router.get("/trace/{session_id}")
async def get_session_traces(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    traces = get_traces(session_id)
    if not traces:
        traces = await get_traces_db(session_id)
    return traces or []


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history/reports")
async def list_my_reports(current_user: dict = Depends(get_current_user)):
    return await get_reports_for_user(current_user["username"])


@router.get("/history/sessions")
async def list_my_sessions(current_user: dict = Depends(get_current_user)):
    return await get_sessions_for_user(current_user["username"])


@router.get("/history/reports/{report_id}")
async def get_full_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    doc = await get_report(report_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found.")
    if doc.get("username") != current_user["username"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    return doc.get("data", {})


# ── Session cleanup ───────────────────────────────────────────────────────────

@router.delete("/session/{session_id}")
async def cleanup_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Manually clean up a session's RAG store and uploads."""
    delete_session_store(session_id)
    upload_dir = UPLOAD_DIR / session_id
    if upload_dir.exists():
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
    return {"status": "cleaned", "session_id": session_id}


@router.post("/admin/cleanup")
async def run_cleanup(current_user: dict = Depends(get_current_user)):
    """Trigger expired session cleanup."""
    removed = cleanup_expired_sessions()
    return {"removed_sessions": removed}


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.0.0"}
