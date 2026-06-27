"""基础能力：连通性测试与运行环境信息。"""

from __future__ import annotations

import os
import platform
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def echo(text: str) -> str:
        """回显输入文本，可用于测试 server 是否连通。

        Args:
            text: 要回显的文本。

        Returns:
            与输入完全一致的字符串。
        """
        return text

    @mcp.tool()
    def system_info() -> dict:
        """返回当前运行 server 的系统与解释器信息。"""
        return {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "executable": sys.executable,
            "in_virtualenv": getattr(sys, "base_prefix", sys.prefix) != sys.prefix,
            "cwd": os.getcwd(),
            "pid": os.getpid(),
        }

