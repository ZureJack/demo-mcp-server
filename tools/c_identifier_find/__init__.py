from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_CONFIG_PATH = Path(__file__).parent / "config.json"
_FORMATTER_PATH = Path(__file__).parent / "formatter.py"


def _load_config() -> dict:
    if _CONFIG_PATH.exists():
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    return {"server_url": "http://127.0.0.1:8089"}


def _format_results(data: list[dict], query: str) -> str:
    """动态加载 formatter.py 并格式化结果，出错时 fallback。"""
    try:
        spec = importlib.util.spec_from_file_location("_cif_formatter", _FORMATTER_PATH)
        if spec is None or spec.loader is None:
            raise ImportError("cannot load formatter")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.format_results(data, query)
    except Exception:
        from . import formatter as fallback
        return fallback._fallback_format(data, query)


def register(mcp: "FastMCP") -> None:
    config = _load_config()
    server_url = config["server_url"].rstrip("/")

    @mcp.tool()
    def find_c_identifier(name: str, fuzzy: bool = False) -> str:
        """查找 C 标识符的定义与声明位置。

        前提：需要先启动 c_identifier_find Server
        （python c_identifier_find_server.py /path/to/config.json）

        Args:
            name: 标识符名称
            fuzzy: 是否模糊匹配（默认精确匹配）

        Returns:
            格式化的查询结果
        """
        from .client import call_find

        result = call_find(server_url, name, fuzzy)
        if not result.get("ok"):
            return f"错误: {result.get('error', '未知错误')}"
        data = result.get("data", [])
        return _format_results(data, name)

    @mcp.tool()
    def c_index_status() -> str:
        """查看 c_identifier_find Server 的索引状态。"""
        from .client import call_status

        result = call_status(server_url)
        if not result.get("ok"):
            return f"错误: {result.get('error', '未知错误')}"
        data = result.get("data", {})
        status = data.get("status", "unknown")
        scanned = data.get("scanned", 0)
        total = data.get("total", 0)
        files = data.get("file_count", 0)
        symbols = data.get("symbol_count", 0)

        lines = [
            f"状态:   {status}",
            f"文件数: {files}",
            f"符号数: {symbols}",
        ]
        if total > 0:
            lines.insert(1, f"扫描:   {scanned}/{total}")
        return "\n".join(lines)
