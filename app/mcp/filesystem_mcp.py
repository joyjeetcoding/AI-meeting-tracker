"""
Filesystem MCP Client
---------------------
Uses direct file I/O locally (Windows MCP stdio is unreliable),
and MCP server in production (Linux/Docker).
"""

import sys
import json
import anyio
from pathlib import Path
from app.config import settings


# ── Direct file I/O (used locally on Windows) ─────────────────────────

async def save_file(relative_path: str, content: str) -> str:
    abs_path = (Path(settings.MCP_FILESYSTEM_ROOT) / relative_path).resolve()
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_text(content, encoding="utf-8")
    print(f"[FilesystemMCP] Written directly → {abs_path}")
    return str(abs_path)


async def read_file(relative_path: str) -> str:
    abs_path = (Path(settings.MCP_FILESYSTEM_ROOT) / relative_path).resolve()
    return abs_path.read_text(encoding="utf-8")


async def list_files(subdirectory: str = "") -> list[str]:
    target = (Path(settings.MCP_FILESYSTEM_ROOT) / subdirectory).resolve()
    return [str(p) for p in target.iterdir() if p.is_file()]


async def save_json(relative_path: str, data: dict) -> str:
    return await save_file(relative_path, json.dumps(data, indent=2, default=str))


# ── MCP server version (production / Linux only) ──────────────────────

def _get_server_params():
    from mcp import StdioServerParameters
    return StdioServerParameters(
        command="npx.cmd" if sys.platform == "win32" else "npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", settings.MCP_FILESYSTEM_ROOT],
    )


async def save_file_via_mcp(relative_path: str, content: str) -> str:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    abs_path = str((Path(settings.MCP_FILESYSTEM_ROOT) / relative_path).resolve())
    with anyio.fail_after(30):
        async with stdio_client(_get_server_params()) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                await session.call_tool("write_file", arguments={"path": abs_path, "content": content})
    return abs_path