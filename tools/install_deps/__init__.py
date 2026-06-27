"""依赖安装能力：按需安装能力模块的 Python 依赖。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_TOOLS_DIR = Path(__file__).parent.parent


def _iter_module_dirs():
    for child in _TOOLS_DIR.iterdir():
        if (
            not child.is_dir()
            or child.name.startswith("_")
            or child.name == "__pycache__"
        ):
            continue
        yield child


def install_deps(module_names: list[str] | None = None) -> dict:
    """安装指定模块的依赖，未指定时安装所有模块的依赖。

    Returns:
        每个模块的安装结果: {"模块名": "OK" / "错误信息"}
    """
    if module_names:
        dirs = [_TOOLS_DIR / name for name in module_names]
    else:
        dirs = list(_iter_module_dirs())

    results = {}
    for d in dirs:
        req_file = d / "requirements.txt"
        if not req_file.exists():
            results[d.name] = "跳过（无 requirements.txt）"
            continue
        content = req_file.read_text().strip()
        if not content or content.startswith("#"):
            results[d.name] = "跳过（无依赖）"
            continue
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            results[d.name] = f"失败:\n{result.stderr.strip()}"
        else:
            results[d.name] = "OK"
    return results


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def install_deps_for_modules(modules: list[str] | None = None) -> str:
        """按需安装能力模块的 Python 依赖。

        Args:
            modules: 要安装依赖的能力模块名列表（例如 ["time_tools", "file_tools"]）。
                     不传或传 None 则安装所有模块的依赖。

        Returns:
            每个模块的安装结果汇总。
        """
        results = install_deps(modules)
        lines = [f"{name}: {status}" for name, status in results.items()]
        return "\n".join(lines)
