"""文件相关能力。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def read_text_file(path: str, max_bytes: int = 64_000) -> str:
        """读取一个本地文本文件的内容。

        Args:
            path: 文件的绝对路径或相对于 server 启动目录的相对路径。
            max_bytes: 最多读取的字节数，防止把超大文件喂给 LLM，默认 64KB。

        Returns:
            文件文本内容（UTF-8 解码，非法字节会被替换）。
        """
        p = Path(path).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"文件不存在: {p}")
        if not p.is_file():
            raise ValueError(f"不是常规文件: {p}")
        data = p.read_bytes()[:max_bytes]
        return data.decode("utf-8", errors="replace")

