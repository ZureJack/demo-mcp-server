"""MCP resources：作为只读上下文暴露给客户端。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.resource("greeting://{name}")
    def greeting(name: str) -> str:
        """返回一段问候语，演示带参数的 resource。"""
        return f"你好，{name}！欢迎使用 MCP demo server。"

