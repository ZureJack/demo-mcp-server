"""MCP 能力模块自注册工具。

每个能力文件在 ``if __name__ == "__main__"`` 中调用 :func:`register_module`，
将自身注册到 ``tools/.registry.json``，供 :func:`tools.register_all` 收集。
"""

from __future__ import annotations

import json
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"
_REGISTRY_FILE = _TOOLS_DIR / ".registry.json"


def register_module(name: str) -> None:
    """将能力模块名 ``name`` 注册到 registry 文件（幂等）。"""
    data = json.loads(_REGISTRY_FILE.read_text()) if _REGISTRY_FILE.exists() else []
    if name not in data:
        data.append(name)
    _REGISTRY_FILE.write_text(json.dumps(data))
