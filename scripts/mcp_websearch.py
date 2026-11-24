"""
Tiny MCP server that gives the llama.cpp web UI a web search tool.

Needs:  pip install fastmcp ddgs
Run:    python mcp_websearch.py
It listens on http://127.0.0.1:8000/mcp
"""

from fastmcp import FastMCP
from ddgs import DDGS

mcp = FastMCP("websearch")


@mcp.tool
def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web with DuckDuckGo. Use this for current events or facts you are unsure about.
    Returns a list of results with title, url and snippet."""
    results = DDGS().text(query, max_results=max_results)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": (r.get("body") or "")[:500],
        }
        for r in results
    ]

from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
]

if __name__ == "__main__":
    app = mcp.http_app(middleware=middleware)
    uvicorn.run(app, host="127.0.0.1", port=8000)