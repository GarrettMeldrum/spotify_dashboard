from __future__ import annotations

import json
import time
import logging
import os
import queue
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, Optional, Tuple

from flask import Flask, Response, g, jsonify, request
from dotenv import load_dotenv

# --------------------
# Environment & paths
# --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    try:
        load_dotenv(ENV_PATH, override=False, encoding="utf-8")
    except Exception:
        # dotenv is optional; fail soft if not installed
        pass

DB_PATH = os.path.join(BASE_DIR, "spotify_history.db")
LOGGER_TOKEN = os.environ.get("LOGGER_TOKEN")

# --------------------
# Logging
# --------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
            "time": datetime.now(timezone.utc).isoformat(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
log = logging.getLogger("app")
log.setLevel(logging.INFO)
log.addHandler(handler)
log.propagate = False

# --------------------
# SSE subscriber state
# --------------------
SubscriberQ = queue.Queue[str]
subscribers: set[SubscriberQ] = set()
subs_lock = threading.Lock()

# --------------------
# Helpers: time (optional)
# --------------------
def parse_time_to_ms(s: str) -> int:
    s = s.strip()
    if s.isdigit():
        return int(s)
    dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    return int(dt.timestamp() * 1000)

def window_range_ms(win: str) -> Tuple[int, int]:
    now = datetime.now(timezone.utc)
    unit = win[-1].lower()
    amount = int(win[:-1])
    start = now - (timedelta(days=amount) if unit == "d" else timedelta(hours=amount))
    return (int(start.timestamp() * 1000), int(now.timestamp() * 1000))
    
# --- DB watcher helpers for SQLite polling ---
def _open_reader_conn(db_path: str) -> sqlite3.Connection:
    """Independent connection for the watcher thread (friendly to a concurrent writer)."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=2000;")
    return conn

def _get_max_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM spotify_history;").fetchone()
    return int(row["max_id"] or 0)

def _fetch_since(conn: sqlite3.Connection, last_id: int, limit: int = 200) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
          id, played_at, track_id, track_name,
          artist_name_01, album_name, duration_ms
        FROM spotify_history
        WHERE id > ?
        ORDER BY id ASC
        LIMIT ?;
        """,
        (last_id, limit),
    ).fetchall()

def start_db_watcher(broadcast_fn, db_path: str, interval_sec: float = 0.5) -> None:
    """
    Polls for new rows by monotonically increasing id and broadcasts each as it arrives.
    Uses paging to drain bursts quickly; sleeps briefly when idle.
    """
    def loop():
        conn = _open_reader_conn(db_path)
        try:
            # Start at the current tip (no backfill). Use 0 to replay all.
            last_id = _get_max_id(conn)
            while True:
                try:
                    rows = _fetch_since(conn, last_id)
                    if rows:
                        for r in rows:
                            broadcast_fn({"type": "new_play", "data": dict(r)})
                        last_id = rows[-1]["id"]
                        # If we hit the page limit, immediately loop to drain backlog
                        if len(rows) >= 200:
                            continue
                    time.sleep(interval_sec)
                except Exception:
                    # Keep the loop alive; logs already JSON-formatted
                    log.exception("db_watcher_error")
                    time.sleep(1.0)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    t = threading.Thread(target=loop, name="db-watcher", daemon=True)
    t.start()

# --------------------
# App factory
# --------------------
def create_app() -> Flask:
    app = Flask(__name__)

    # ---- DB per request ----
    def get_db() -> sqlite3.Connection:
        db = getattr(g, "_db", None)
        if db is None:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Better read/write concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            # If this process only reads for certain endpoints, you could also:
            # conn.execute("PRAGMA busy_timeout=2000;")
            g._db = conn
            return conn
        return db

    @app.teardown_appcontext
    def close_db(_: Optional[BaseException]) -> None:
        db = getattr(g, "_db", None)
        if db is not None:
            db.close()
            g._db = None

    # ---- SSE broadcast ----
    def broadcast(msg: Dict[str, Any]) -> None:
        data = json.dumps(msg, separators=(",", ":"), ensure_ascii=False)
        with subs_lock:
            dead: list[SubscriberQ] = []
            for q in subscribers:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    # Backpressure: drop oldest, then try once more
                    try:
                        q.get_nowait()
                        q.put_nowait(data)
                    except Exception:
                        dead.append(q)
            for q in dead:
                subscribers.discard(q)

    # --------------------
    # Routes
    # --------------------
    @app.get("/health")
    def health() -> Response:
        try:
            get_db().execute("SELECT 1").fetchone()
            with subs_lock:
                n = len(subscribers)
            return jsonify({"ok": True, "subscribers": n})
        except Exception as e:
            log.exception("health check failed")
            return jsonify({"ok": False, "error": str(e)}), 500

    @app.get("/recent")
    def recent() -> Response:
        # ?limit=... (default 50, max 500)
        try:
            raw = request.args.get("limit", "50")
            limit = int(raw)
        except Exception:
            limit = 50
        limit = max(1, min(limit, 500))

        rows = get_db().execute(
            """
            SELECT
                id,
                played_at,
                track_id,
                track_name,
                artist_name_01,
                album_name,
                duration_ms
            FROM spotify_history
            ORDER BY CAST(played_at AS INTEGER) DESC
            LIMIT ?;
            """,
            (limit,),
        ).fetchall()

        return jsonify([dict(r) for r in rows])

    @app.get("/stream")
    def stream() -> Response:
        def event_stream() -> Iterable[str]:
            q: SubscriberQ = queue.Queue(maxsize=256)
            with subs_lock:
                subscribers.add(q)
            try:
                # Flush headers + set reconnect policy
                yield "retry: 3000\n"  # 3s reconnect backoff
                yield "event: hello\ndata: {}\n\n"

                while True:
                    try:
                        item = q.get(timeout=15)
                        # item is already JSON; ensure no bare newlines
                        yield f"event: update\ndata: {item}\n\n"
                    except queue.Empty:
                        # Comment lines are heartbeats that most proxies let pass
                        yield ": keepalive\n\n"
            finally:
                with subs_lock:
                    subscribers.discard(q)

        return Response(
            event_stream(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": 'https://garrettmeldrum.com',
                "Vary": "Origin",
            },
        )
    
    start_db_watcher(broadcast_fn=broadcast, db_path=DB_PATH, interval_sec=0.5)
    return app

app = create_app()
