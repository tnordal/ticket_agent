from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

KIWI_MCP_URL = "https://mcp.kiwi.com"


@asynccontextmanager
async def kiwi_session():
    async with streamable_http_client(KIWI_MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def search_flights(session: ClientSession, params: dict) -> dict:
    result = await session.call_tool("search-flight", params)
    data = result.structured_content
    if result.is_error or not data:
        text = " ".join(getattr(c, "text", "") for c in result.content)
        raise RuntimeError(f"Kiwi search failed: {text[:300]}")
    if data.get("error"):
        raise RuntimeError(f"Kiwi search error: {data['error']}")
    return data
