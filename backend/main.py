"""
CodeTribunal - Multi-Agent Adversarial Code Review System
Main Backend Application

This module implements the FastAPI server that orchestrates the tribunal
and handles WebSocket connections for real-time streaming of debate proceedings.
"""

import asyncio
import json
import uuid
import logging
from contextlib import asynccontextmanager

# Configure logging so application loggers are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agents import TribunalCourt, ProceedingEntry
from .agents.benchmark import run_benchmark_comparison
from .config import settings
from .utils import detect_language_from_content, generate_case_title, sanitize_code_content
from .database import (
    SessionLocal, init_db,
    create_session, consume_session, cleanup_expired_sessions,
)

logger = logging.getLogger("codetribunal.main")


# ── Lifespan: init DB + periodic cleanup ────────────────────────────
async def _session_cleanup_loop():
    """Periodically clean up consumed/expired sessions from Neon."""
    import asyncio
    while True:
        await asyncio.sleep(3600)  # every hour
        if SessionLocal:
            db = SessionLocal()
            try:
                cleanup_expired_sessions(db, max_age_hours=24)
            except Exception as e:
                logger.warning(f"Session cleanup failed: {e}")
            finally:
                db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    cleanup_task = asyncio.create_task(_session_cleanup_loop())
    logger.info("CodeTribunal started. DB initialized, session cleanup scheduled.")
    yield
    # Shutdown
    cleanup_task.cancel()


app = FastAPI(title="CodeTribunal", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store is now Neon PostgreSQL (see database.py) ──────────
# No more in-memory dict — safe for multi-worker / serverless deployments.

# ── Pydantic models ──────────────────────────────────────────────────
class CodeSubmission(BaseModel):
    code_content: str
    language: str = "auto"
    focus_area: str = ""

# ── Helpers ──────────────────────────────────────────────────────────
def _format_entry(entry: ProceedingEntry) -> dict:
    """Format a ProceedingEntry with full structured metadata for frontend."""
    data = {
        "agent": entry.agent.value,
        "tag": entry.tag,
        "message": entry.message,
        "round_number": entry.round_number,
        "timestamp": entry.timestamp.isoformat(),
        "confidence": entry.confidence,
        # Structured metadata for courtroom UI
        "phase": entry.phase,
        "speaker": entry.speaker,
        "exhibit_ref": entry.exhibit_ref,
        "is_objection": entry.is_objection,
        "line_range": entry.line_range,
    }
    # Include structured findings if present
    if entry.findings:
        data["findings"] = [f.to_dict() for f in entry.findings]
    # Include deterministic rubric scores if present (from ARBITER verdict)
    if entry.rubric_scores:
        data["rubric_scores"] = entry.rubric_scores
    return data

# ═════════════════════════════════════════════════════════════════════
# REST Endpoints
# ═════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    return {"message": "CodeTribunal Backend is running", "status": "healthy"}


@app.post("/submit/")
async def submit_code(submission: CodeSubmission):
    """Submit code for tribunal review (non-streaming, synchronous)."""
    code_content = sanitize_code_content(submission.code_content)
    language = submission.language
    if language == "auto" or not language:
        language = detect_language_from_content(code_content)

    tribunal = TribunalCourt()
    proceedings = await tribunal.conduct_trial(code_content, language, submission.focus_area)

    formatted = [_format_entry(e) for e in proceedings]
    return {
        "status": "success",
        "proceedings": formatted,
        "token_usage": tribunal.token_usage.summary() if settings.TRACK_TOKEN_USAGE else None,
        "summary": tribunal.get_formatted_proceedings(),
    }


@app.post("/benchmark/")
async def benchmark_code(submission: CodeSubmission):
    """
    Compare single-agent baseline vs multi-agent tribunal on the same code.
    Demonstrates measurable efficiency gain of the multi-agent approach.
    Returns side-by-side metrics for Track 3 hackathon evaluation.
    """
    code_content = sanitize_code_content(submission.code_content)
    language = submission.language
    if language == "auto" or not language:
        language = detect_language_from_content(code_content)

    comparison = await run_benchmark_comparison(
        code_content, language, submission.focus_area
    )
    return {"status": "success", **comparison}


@app.post("/upload/")
async def upload_code(file: UploadFile = File(...)):
    """
    Upload a code file.
    Returns a session_id that the frontend can use to connect to /ws/trial/{session_id}
    OR run the trial immediately and return results.
    """
    allowed_extensions = ('.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.cs', '.rb', '.php', '.rs')
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {allowed_extensions}")

    raw = await file.read()
    code_content = sanitize_code_content(raw.decode("utf-8"))
    language = detect_language_from_content(code_content)

    # Create a Neon-backed session so WebSocket can pick it up
    session_id = str(uuid.uuid4())
    payload = {
        "code_content": code_content,
        "language": language,
        "focus_area": "",
        "title": generate_case_title(code_content, language),
        "filename": file.filename,
    }
    if SessionLocal:
        db = SessionLocal()
        try:
            create_session(db, session_id, payload)
        finally:
            db.close()
    else:
        raise HTTPException(status_code=503, detail="Database not available")

    return {
        "session_id": session_id,
        "filename": file.filename,
        "language": language,
        "title": payload["title"],
        "status": "ready",
        "message": "File uploaded. Connect to /ws/trial/{session_id} to stream the trial.",
    }


@app.post("/sessions/{session_id}/start")
async def start_session_trial(session_id: str, focus_area: str = ""):
    """
    Start a trial for an existing session via REST (non-streaming).
    The session must have been created via /upload/ or /submit-session/.
    NOTE: For large files, prefer WebSocket streaming to avoid HTTP timeouts.
    """
    if not SessionLocal:
        raise HTTPException(status_code=503, detail="Database not available")

    db = SessionLocal()
    try:
        session = consume_session(db, session_id)
    finally:
        db.close()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found or already consumed")

    if focus_area:
        session["focus_area"] = focus_area

    tribunal = TribunalCourt()
    proceedings = await tribunal.conduct_trial(
        session["code_content"], session["language"], session["focus_area"]
    )
    formatted = [_format_entry(e) for e in proceedings]

    return {
        "session_id": session_id,
        "status": "success",
        "proceedings": formatted,
        "token_usage": tribunal.token_usage.summary() if settings.TRACK_TOKEN_USAGE else None,
        "summary": tribunal.get_formatted_proceedings(),
    }


@app.post("/submit-session/")
async def submit_code_with_session(submission: CodeSubmission):
    """
    Submit code and get a session_id back.
    Use this when you want to stream via WebSocket instead of getting immediate results.
    """
    code_content = sanitize_code_content(submission.code_content)
    language = submission.language
    if language == "auto" or not language:
        language = detect_language_from_content(code_content)

    session_id = str(uuid.uuid4())
    payload = {
        "code_content": code_content,
        "language": language,
        "focus_area": submission.focus_area,
        "title": generate_case_title(code_content, language),
    }
    if SessionLocal:
        db = SessionLocal()
        try:
            create_session(db, session_id, payload)
        finally:
            db.close()
    else:
        raise HTTPException(status_code=503, detail="Database not available")

    return {
        "session_id": session_id,
        "title": payload["title"],
        "language": language,
        "status": "ready",
        "message": "Session created. Connect to /ws/trial/{session_id} to stream the trial.",
    }


# ═════════════════════════════════════════════════════════════════════
# WebSocket Endpoint
# ═════════════════════════════════════════════════════════════════════

@app.websocket("/ws/trial/{session_id}")
async def websocket_trial(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time streaming of tribunal proceedings.
    Requires a valid session_id (created via /upload/ or /submit-session/).
    """
    await websocket.accept()

    # Consume session from Neon (atomic read-and-mark)
    if not SessionLocal:
        await websocket.send_text(json.dumps({
            "type": "error", "message": "Database not available"
        }))
        await websocket.close(code=4003, reason="DB unavailable")
        return

    db = SessionLocal()
    try:
        session = consume_session(db, session_id)
    finally:
        db.close()

    if session is None:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Session '{session_id}' not found or already consumed. "
                       f"Upload code first via /upload/ or /submit-session/."
        }))
        await websocket.close(code=4004, reason="Session not found")
        return

    tribunal = TribunalCourt()

    try:
        await websocket.send_text(json.dumps({
            "type": "connection",
            "message": f"Connected to CodeTribunal. Starting trial: {session.get('title', 'Unknown Case')}",
            "session_id": session_id,
            "title": session.get("title", ""),
            "language": session.get("language", "unknown"),
        }))

        async for entry in tribunal.conduct_trial_streaming(
            session["code_content"], session["language"], session["focus_area"]
        ):
            payload = {
                "type": "proceeding",
                "data": _format_entry(entry),
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(0.3)  # slight delay for UX

        # Send completion with token usage + trial summary
        # Extract rubric scores from the verdict entry (deterministic, not LLM-parsed)
        rubric_scores = None
        for proc in tribunal.proceedings:
            if proc.rubric_scores:
                rubric_scores = proc.rubric_scores
                break

        completion_payload = {
            "type": "completion",
            "message": "Trial completed. Final verdict rendered.",
            "conflict_clusters": [
                c.to_dict() for c in tribunal.conflict_clusters
            ],
        }
        if rubric_scores:
            completion_payload["rubric_scores"] = rubric_scores
        if settings.TRACK_TOKEN_USAGE:
            completion_payload["token_usage"] = tribunal.token_usage.summary()

        await websocket.send_text(json.dumps(completion_payload))

    except (WebSocketDisconnect, asyncio.CancelledError):
        # Client disconnected or task was cancelled — stop burning tokens
        tribunal.cancel()
        logger.info(
            f"Client disconnected/cancelled for session {session_id}. "
            f"Trial aborted, {tribunal.token_usage.calls} API calls made before cancellation."
        )
    except Exception as e:
        tribunal.cancel()
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": f"An error occurred during the trial: {str(e)}"
            }))
        except Exception:
            pass


# Run the server with: uvicorn backend.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
