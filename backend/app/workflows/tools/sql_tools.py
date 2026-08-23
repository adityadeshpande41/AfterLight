"""
SQL query tools for agents.

These are callable functions that agents can invoke to query the database.
Agents decide WHAT to query based on their reasoning.

Note: These run synchronously (blocking) since OpenAI tool calls happen
in a synchronous context. They use their own short-lived connections.
"""

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, text

from app.config import settings

# Sync connection URL (replace asyncpg with psycopg2-compatible)
SYNC_URL = settings.database_url.replace("+asyncpg", "").replace("postgresql://", "postgresql+psycopg2://")
# Actually, just use raw psycopg2 style URL
SYNC_URL = settings.database_url.replace("postgresql+asyncpg", "postgresql")


def _sync_query(sql: str, params: dict = None) -> list[dict]:
    """Run a synchronous SQL query and return results as dicts."""
    from sqlalchemy import create_engine, text as sa_text
    engine = create_engine(SYNC_URL)
    with engine.connect() as conn:
        result = conn.execute(sa_text(sql), params or {})
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    engine.dispose()
    return rows


def query_incidents_by_venue(venue_id: str, days: int = 90) -> str:
    """Query incidents for a venue within a time window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    rows = _sync_query(
        """SELECT ref_code, title, incident_type, severity, location, occurred_at, status
           FROM incidents
           WHERE venue_id = :venue_id AND occurred_at >= :cutoff
           ORDER BY occurred_at DESC""",
        {"venue_id": venue_id, "cutoff": cutoff},
    )
    return json.dumps(rows, default=str)


def query_incidents_by_location(venue_id: str, location_keyword: str) -> str:
    """Query incidents at a specific location within a venue."""
    rows = _sync_query(
        """SELECT ref_code, title, severity, location, occurred_at
           FROM incidents
           WHERE venue_id = :venue_id AND LOWER(location) LIKE :pattern
           ORDER BY occurred_at DESC""",
        {"venue_id": venue_id, "pattern": f"%{location_keyword.lower()}%"},
    )
    return json.dumps(rows, default=str)


def query_incidents_by_time_window(venue_id: str, start_hour: int, end_hour: int) -> str:
    """Query incidents within a time-of-day window."""
    rows = _sync_query(
        """SELECT ref_code, title, severity, location, occurred_at,
                  EXTRACT(HOUR FROM occurred_at) as hour
           FROM incidents
           WHERE venue_id = :venue_id
           ORDER BY occurred_at DESC""",
        {"venue_id": venue_id},
    )
    # Filter by time window in Python (simpler than SQL for wrap-around)
    filtered = []
    for row in rows:
        hour = int(row.get("hour", 0))
        if start_hour <= end_hour:
            match = start_hour <= hour <= end_hour
        else:  # wraps midnight
            match = hour >= start_hour or hour <= end_hour
        if match:
            filtered.append(row)
    return json.dumps(filtered, default=str)


def get_action_completion_stats(venue_id: str) -> str:
    """Get action item completion statistics for a venue."""
    rows = _sync_query(
        """SELECT ai.status, COUNT(*) as count
           FROM action_items ai
           JOIN incidents i ON ai.incident_id = i.id
           WHERE i.venue_id = :venue_id
           GROUP BY ai.status""",
        {"venue_id": venue_id},
    )
    total = sum(r["count"] for r in rows)
    completed = sum(r["count"] for r in rows if r["status"] == "Complete")
    return json.dumps({
        "total": total,
        "completed": completed,
        "open": total - completed,
        "completion_rate": round(completed / total * 100, 1) if total > 0 else 0,
        "breakdown": {r["status"]: r["count"] for r in rows},
    })


# Tool definitions for OpenAI function calling
SQL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_incidents_by_venue",
            "description": "Query all incidents for a venue within a time window. Use to understand incident frequency and history.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string", "description": "UUID of the venue"},
                    "days": {"type": "integer", "description": "Number of days to look back (default 90)"},
                },
                "required": ["venue_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_incidents_by_location",
            "description": "Query incidents at a specific location within a venue. Use to detect location-based patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string", "description": "UUID of the venue"},
                    "location_keyword": {"type": "string", "description": "Keyword to match in location (e.g., 'entrance', 'bar')"},
                },
                "required": ["venue_id", "location_keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_incidents_by_time_window",
            "description": "Query incidents in a specific time-of-day window. Use to detect time-based patterns.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string", "description": "UUID of the venue"},
                    "start_hour": {"type": "integer", "description": "Start hour (0-23)"},
                    "end_hour": {"type": "integer", "description": "End hour (0-23)"},
                },
                "required": ["venue_id", "start_hour", "end_hour"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_action_completion_stats",
            "description": "Get action item completion statistics for a venue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "venue_id": {"type": "string", "description": "UUID of the venue"},
                },
                "required": ["venue_id"],
            },
        },
    },
]

SQL_TOOL_FUNCTIONS = {
    "query_incidents_by_venue": query_incidents_by_venue,
    "query_incidents_by_location": query_incidents_by_location,
    "query_incidents_by_time_window": query_incidents_by_time_window,
    "get_action_completion_stats": get_action_completion_stats,
}
