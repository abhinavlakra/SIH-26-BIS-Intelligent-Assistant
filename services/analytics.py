"""Query telemetry.

Two audiences. For us: real latency and grounded-rate numbers instead of
estimates. For **BIS**: the list of queries that matched nothing is a
standards-development gap signal generated from actual demand — the one thing
in this system built for the ministry rather than for the end user.

Privacy: the query text, timing and outcome are recorded. No IP address, no
user identifier, no session token. Nothing here can be tied back to a person,
and the UI says so.

Storage is a small SQLite file. It is optional — if it cannot be opened, every
function degrades to a no-op rather than taking the request down with it.
"""

import sqlite3
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.models import AnalyticsResponse, FacetCount, QueryLogEntry

_LOCK = threading.Lock()
_SCHEMA = """
CREATE TABLE IF NOT EXISTS queries (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    query      TEXT    NOT NULL,
    endpoint   TEXT    NOT NULL,
    grounded   INTEGER NOT NULL,
    top_score  REAL    NOT NULL,
    latency_ms INTEGER NOT NULL,
    used_model TEXT    NOT NULL,
    at         TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS queries_at ON queries (at DESC);
"""

_RECENT_LIMIT = 20


def _db_path() -> Path:
    settings = get_settings()
    return settings.chroma_dir.parent / "analytics.sqlite3"


def _connect() -> sqlite3.Connection | None:
    try:
        path = _db_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=2.0)
        connection.executescript(_SCHEMA)
        return connection
    except sqlite3.Error:
        # Telemetry must never be the reason a request fails.
        return None


def record(
    query: str,
    endpoint: str,
    grounded: bool,
    top_score: float,
    latency_ms: int,
    used_model: str,
) -> None:
    connection = _connect()
    if connection is None:
        return
    try:
        with _LOCK, connection:
            connection.execute(
                "INSERT INTO queries "
                "(query, endpoint, grounded, top_score, latency_ms, used_model, at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    query.strip()[:500],
                    endpoint,
                    int(grounded),
                    float(top_score),
                    int(latency_ms),
                    used_model,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                ),
            )
    except sqlite3.Error:
        pass
    finally:
        connection.close()


def summary(limit: int = 10) -> AnalyticsResponse:
    connection = _connect()
    empty = AnalyticsResponse(
        total_queries=0, grounded_rate=0.0, median_latency_ms=0, top_queries=[]
    )
    if connection is None:
        return empty

    try:
        rows = connection.execute(
            "SELECT query, endpoint, grounded, top_score, latency_ms, used_model, at "
            "FROM queries ORDER BY id DESC"
        ).fetchall()
    except sqlite3.Error:
        return empty
    finally:
        connection.close()

    if not rows:
        return empty

    total = len(rows)
    grounded = sum(1 for r in rows if r[2])
    latencies = [r[4] for r in rows]

    def tally(subset) -> list[FacetCount]:
        counts: dict[str, int] = {}
        for row in subset:
            key = row[0].strip().lower()
            counts[key] = counts.get(key, 0) + 1
        return [
            FacetCount(value=value, count=count)
            for value, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
        ]

    return AnalyticsResponse(
        total_queries=total,
        grounded_rate=round(grounded / total, 3),
        median_latency_ms=int(statistics.median(latencies)),
        top_queries=tally(rows),
        unanswered=tally([r for r in rows if not r[2]]),
        recent=[
            QueryLogEntry(
                query=r[0],
                endpoint=r[1],
                grounded=bool(r[2]),
                top_score=r[3],
                latency_ms=r[4],
                used_model=r[5],
                at=r[6],
            )
            for r in rows[:_RECENT_LIMIT]
        ],
    )
