"""MCP prompts：可被客户端复用的提示模板。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.prompt()
    def summarize(text: str) -> str:
        """生成一个让模型用中文总结给定文本的提示。"""
        return f"请用简洁的中文要点总结以下内容：\n\n{text}"

