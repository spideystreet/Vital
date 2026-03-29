"""PostgreSQL storage for Apple Watch health data."""

import json
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row

from vital.config import DATABASE_URL

_CREATE_METRIC_CATALOG = """
CREATE TABLE IF NOT EXISTS metric_catalog (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    unit TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT
);
"""

_CREATE_HEALTH_DATA = """
CREATE TABLE IF NOT EXISTS health_data (
    id SERIAL PRIMARY KEY,
    recorded_at TIMESTAMPTZ NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metric_id INTEGER NOT NULL REFERENCES metric_catalog(id),
    value DOUBLE PRECISION NOT NULL,
    value_end DOUBLE PRECISION,
    source TEXT,
    metadata JSONB
);
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_health_metric_date
ON health_data (metric_id, recorded_at);
"""

# Default metrics seeded on init
_DEFAULT_METRICS = [
    ("heart_rate", "bpm", "vitals", "Instantaneous heart rate"),
    ("resting_hr", "bpm", "vitals", "Resting heart rate"),
    ("hrv", "ms", "vitals", "Heart rate variability (SDNN)"),
    ("spo2", "%", "vitals", "Blood oxygen saturation"),
    ("steps", "count", "activity", "Step count"),
    ("sleep", "hours", "sleep", "Sleep duration"),
]


def _connect(**kwargs):
    """Open a connection to PostgreSQL."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, **kwargs)


def init_db() -> None:
    """Create tables, indexes, and seed default metrics."""
    with _connect() as conn:
        conn.execute(_CREATE_METRIC_CATALOG)
        conn.execute(_CREATE_HEALTH_DATA)
        conn.execute(_CREATE_INDEX)
        for name, unit, category, description in _DEFAULT_METRICS:
            conn.execute(
                "INSERT INTO metric_catalog (name, unit, category, description) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (name) DO NOTHING",
                (name, unit, category, description),
            )


def _resolve_metric_id(cur, metric_name: str) -> int:
    """Get metric_id from name, raising ValueError if unknown."""
    row = cur.execute("SELECT id FROM metric_catalog WHERE name = %s", (metric_name,)).fetchone()
    if row is None:
        raise ValueError(f"Unknown metric: {metric_name!r}. Register it in metric_catalog first.")
    return row["id"]


def insert_metrics(metrics: list[dict]) -> int:
    """Insert a batch of health metrics. Returns count of inserted rows."""
    if not metrics:
        return 0
    with _connect() as conn:
        with conn.cursor() as cur:
            rows = []
            for m in metrics:
                metric_id = _resolve_metric_id(cur, m["metric"])
                rows.append(
                    (
                        m["recorded_at"],
                        metric_id,
                        m["value"],
                        m.get("value_end"),
                        m.get("source"),
                        json.dumps(m["metadata"]) if m.get("metadata") else None,
                    )
                )
            cur.executemany(
                "INSERT INTO health_data "
                "(recorded_at, metric_id, value, value_end, source, metadata) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                rows,
            )
    return len(rows)


def get_latest(metric: str, limit: int = 1) -> list[dict]:
    """Get the N most recent values for a given metric."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT d.*, c.name as metric, c.unit
            FROM health_data d
            JOIN metric_catalog c ON c.id = d.metric_id
            WHERE c.name = %s
            ORDER BY d.recorded_at DESC
            LIMIT %s
            """,
            (metric, limit),
        ).fetchall()
    return rows


def get_summary(hours: int = 24) -> dict:
    """Get aggregated summary of all metrics over the last N hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT c.name as metric, c.unit,
                   COUNT(*) as count,
                   ROUND(AVG(d.value)::numeric, 1) as avg,
                   ROUND(MIN(d.value)::numeric, 1) as min,
                   ROUND(MAX(d.value)::numeric, 1) as max,
                   ROUND((ARRAY_AGG(d.value ORDER BY d.recorded_at DESC))[1]::numeric, 1) as latest
            FROM health_data d
            JOIN metric_catalog c ON c.id = d.metric_id
            WHERE d.recorded_at >= %s
            GROUP BY c.name, c.unit
            ORDER BY c.name
            """,
            (since,),
        ).fetchall()
    return {
        row["metric"]: {
            "metric": row["metric"],
            "unit": row["unit"],
            "count": row["count"],
            "avg": float(row["avg"]),
            "min": float(row["min"]),
            "max": float(row["max"]),
            "latest": float(row["latest"]),
        }
        for row in rows
    }


def get_recent_raw(hours: int = 24) -> list[dict]:
    """Get all raw data points from the last N hours."""
    since = datetime.now(UTC) - timedelta(hours=hours)
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT d.*, c.name as metric, c.unit
            FROM health_data d
            JOIN metric_catalog c ON c.id = d.metric_id
            WHERE d.recorded_at >= %s
            ORDER BY d.recorded_at DESC
            """,
            (since,),
        ).fetchall()
    return rows
