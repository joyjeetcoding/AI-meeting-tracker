"""
SQLite MCP Client
-----------------
Why use MCP for DB queries instead of SQLModel directly?
  - Same reason as filesystem: agents call DB operations as tools
  - Clean separation — agents don't need to know SQL
  - Swappable — move to Postgres later without touching agent code
"""

import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import settings


SERVER_PARAMS = StdioServerParameters(
    command="npx",
    args=[
        "-y",
        "@modelcontextprotocol/server-sqlite",     # official MCP SQLite server
        settings.MCP_SQLITE_DB_PATH,               # path to your meetings.db
    ],
)


async def run_query(sql: str) -> list[dict]:
    """
    Run a SELECT query via SQLite MCP.
    Returns a list of row dicts.
    """
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "read_query",
                arguments={"query": sql},
            )
    raw = result.content[0].text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [{"raw": raw}]


async def execute(sql: str) -> str:
    """
    Run an INSERT / UPDATE / DELETE via SQLite MCP.
    Returns a confirmation string.
    """
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "write_query",
                arguments={"query": sql},
            )
    return result.content[0].text


async def get_meeting_summary(meeting_id: int) -> dict:
    """
    Fetch a meeting + all its action items in one MCP query.
    This is what the /get-summary endpoint calls.
    """
    rows = await run_query(f"""
        SELECT
            m.id, m.title, m.summary, m.status, m.created_at,
            a.id as action_id, a.task, a.owner, 
            a.priority, a.deadline, a.status as action_status
        FROM meeting m
        LEFT JOIN actionitem a ON a.meeting_id = m.id
        WHERE m.id = {meeting_id}
    """)

    if not rows:
        return {}

    # First row has the meeting data
    meeting = {
        "id": rows[0]["id"],
        "title": rows[0]["title"],
        "summary": rows[0]["summary"],
        "status": rows[0]["status"],
        "created_at": rows[0]["created_at"],
        "action_items": [],
    }

    # Each row may have a different action item
    for row in rows:
        if row.get("action_id"):
            meeting["action_items"].append({
                "id": row["action_id"],
                "task": row["task"],
                "owner": row["owner"],
                "priority": row["priority"],
                "deadline": row["deadline"],
                "status": row["action_status"],
            })
    return meeting


async def list_all_meetings() -> list[dict]:
    """Return all meetings with their action item counts."""
    return await run_query("""
        SELECT
            m.id, m.title, m.status, m.created_at,
            COUNT(a.id) as action_count
        FROM meeting m
        LEFT JOIN actionitem a ON a.meeting_id = m.id
        GROUP BY m.id
        ORDER BY m.created_at DESC
    """)