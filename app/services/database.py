"""
MongoDB persistence layer.

Collections:
  users        – registered accounts
  sessions     – per-user research sessions
  reports      – compiled FinalReport documents
  traces       – agent execution traces per session

Falls back gracefully to in-memory dicts when MONGODB_URI is not set,
so the app still works without a database (dev mode).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.utils.config import MONGODB_URI, MONGODB_DB_NAME, logger

# ── Optional Motor (async MongoDB driver) ────────────────────────────────────
_motor_available = False
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    _motor_available = True
except ImportError:
    logger.warning("[DB] motor not installed. Running in in-memory mode.")

# ── Module-level state ────────────────────────────────────────────────────────
_client = None
_db = None

# In-memory fallback stores
_mem_users: Dict[str, Dict] = {}
_mem_sessions: Dict[str, Dict] = {}
_mem_reports: Dict[str, Dict] = {}
_mem_traces: Dict[str, List] = {}


def _use_mongo() -> bool:
    return bool(MONGODB_URI and _motor_available and _db is not None)


async def connect_db() -> None:
    """Call once at application startup."""
    global _client, _db
    if not MONGODB_URI:
        logger.info("[DB] No MONGODB_URI — using in-memory persistence.")
        return
    if not _motor_available:
        logger.warning("[DB] motor package missing — using in-memory persistence.")
        return
    try:
        _client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Ping to verify connection
        await _client.admin.command("ping")
        _db = _client[MONGODB_DB_NAME]
        # Ensure indexes
        await _db.users.create_index("username", unique=True)
        await _db.sessions.create_index("session_id", unique=True)
        await _db.reports.create_index("report_id", unique=True)
        await _db.traces.create_index("session_id")
        logger.info(f"[DB] Connected to MongoDB database '{MONGODB_DB_NAME}'.")
    except Exception as e:
        logger.error(f"[DB] MongoDB connection failed: {e}. Falling back to in-memory.")
        _db = None


async def disconnect_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("[DB] MongoDB connection closed.")


# ── Users ─────────────────────────────────────────────────────────────────────

async def create_user(username: str, hashed_password: str) -> bool:
    """Returns True on success, False if username already exists."""
    doc = {
        "username": username,
        "hashed_password": hashed_password,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if _use_mongo():
        try:
            await _db.users.insert_one(doc)
            return True
        except Exception:
            return False
    else:
        if username in _mem_users:
            return False
        _mem_users[username] = doc
        return True


async def get_user(username: str) -> Optional[Dict]:
    if _use_mongo():
        return await _db.users.find_one({"username": username}, {"_id": 0})
    return _mem_users.get(username)


# ── Sessions ──────────────────────────────────────────────────────────────────

async def upsert_session(session_id: str, username: str, metadata: Dict = None) -> None:
    doc = {
        "session_id": session_id,
        "username": username,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }
    if _use_mongo():
        await _db.sessions.update_one(
            {"session_id": session_id}, {"$set": doc}, upsert=True
        )
    else:
        _mem_sessions[session_id] = doc


async def get_sessions_for_user(username: str) -> List[Dict]:
    if _use_mongo():
        cursor = _db.sessions.find({"username": username}, {"_id": 0})
        return await cursor.to_list(length=200)
    return [s for s in _mem_sessions.values() if s.get("username") == username]


# ── Reports ───────────────────────────────────────────────────────────────────

async def save_report(report_id: str, session_id: str, username: str, report_data: Dict) -> None:
    doc = {
        "report_id": report_id,
        "session_id": session_id,
        "username": username,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": report_data,
    }
    if _use_mongo():
        await _db.reports.update_one(
            {"report_id": report_id}, {"$set": doc}, upsert=True
        )
    else:
        _mem_reports[report_id] = doc


async def get_report(report_id: str) -> Optional[Dict]:
    if _use_mongo():
        doc = await _db.reports.find_one({"report_id": report_id}, {"_id": 0})
        return doc
    return _mem_reports.get(report_id)


async def get_reports_for_user(username: str) -> List[Dict]:
    if _use_mongo():
        cursor = _db.reports.find({"username": username}, {"_id": 0, "data": 0})
        return await cursor.to_list(length=200)
    return [
        {k: v for k, v in r.items() if k != "data"}
        for r in _mem_reports.values()
        if r.get("username") == username
    ]


# ── Traces ────────────────────────────────────────────────────────────────────

async def append_trace(session_id: str, trace: Dict) -> None:
    if _use_mongo():
        await _db.traces.insert_one({"session_id": session_id, **trace})
    else:
        _mem_traces.setdefault(session_id, []).append(trace)


async def get_traces_db(session_id: str) -> List[Dict]:
    if _use_mongo():
        cursor = _db.traces.find({"session_id": session_id}, {"_id": 0, "session_id": 0})
        return await cursor.to_list(length=1000)
    return _mem_traces.get(session_id, [])
