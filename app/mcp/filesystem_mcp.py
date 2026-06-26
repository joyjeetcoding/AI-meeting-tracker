"""
Filesystem MCP Client
---------------------
Why use MCP instead of plain open() ?
  - Agents interact with files the same way they'd call any tool
  - File operations are auditable — you can see exactly what was read/written
  - Swappable — want to move to S3 later? Change this file, agents don't change
"""

import json
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from app.config import settings


# This tells MCP which server to spin up and how
# npx runs the official MCP filesystem server as a subprocess
SERVER_PARAMS = StdioServerParameters(
    command="npx",
    args=[
        "-y",                                           # auto-install if not present
        "@modelcontextprotocol/server-filesystem",      # official MCP filesystem server
        settings.MCP_FILESYSTEM_ROOT,                   # root directory it can access
    ],
)


async def save_file(relative_path: str, content: str) -> str:
    """
    Save text content to a file via Filesystem MCP.
    Returns the absolute path where the file was saved.
    """
    abs_path = str(Path(settings.MCP_FILESYSTEM_ROOT)/relative_path)

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await session.call_tool(
                "write_file",
                arguments={"path": abs_path, "content": content},
            )
    return abs_path


async def read_file(relative_path: str) -> str:
    """Read a file's contents via Filesystem MCP."""
    abs_path = str(Path(settings.MCP_FILESYSTEM_ROOT)/relative_path)

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "read_file",
                arguments={"path": abs_path},
            )
    return result.content[0].text


async def list_files(subdirectory: str = "") -> list[str]:
    """List all files in a subdirectory via Filesystem MCP."""
    target = str(Path(settings.MCP_FILESYSTEM_ROOT)/subdirectory)

    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "list_directory",
                arguments={"path": target},
            )
    raw = result.content[0].text
    return [line.strip() for line in raw.splitlines() if line.strip()]


async def save_json(relative_path: str, data: dict) -> str:
    """Convenience wrapper — serializes dict to JSON then saves via MCP."""
    return await save_file(relative_path, json.dumps(data, indent=2, default=str))