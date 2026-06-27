"""
能力模块包：每个子模块负责一类业务能力，向外暴露 ``register(mcp)`` 函数。

主框架 ``server.py`` 只通过 :func:`register_all` 一次性把全部模块挂载到
FastMCP 实例上，**新增能力只需在 tools/ 下新建子目录**，**无需修改本文件**。

注册机制
--------
:func:`register_all` 会通过子进程逐个执行 ``python -m tools.xxx``，
每个能力子包的 ``if __name__ == "__main__"`` 自注册到 ``.registry.json``，
再统一导入并挂载。

约定
----
每个能力子包（``tools/xxx/``）必须实现 ``__init__.py`` 并暴露：

.. code-block:: python

    def register(mcp: "FastMCP") -> None:
        @mcp.tool()
        def my_tool(...): ...

工具包自动注册机制
--------------------
在 ``tools/xxx/__register__.py`` 中调用 :func:`lib.registry.register_module`：

.. code-block:: python

    from lib.registry import register_module
    register_module("xxx")

``register_all`` 通过子进程 ``python tools/xxx/__register__.py`` 执行该文件完成自注册。

不要在模块顶层引用全局 ``mcp``，保证模块本身与主框架解耦、可被独立 import
和单元测试。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP

_TOOLS_DIR = Path(__file__).parent
_REGISTRY_FILE = _TOOLS_DIR / ".registry.json"

# 在 register_all 执行后填充，运行时不要直接读写此变量
TOOL_MODULES: list[str] = []


def iter_tool_names() -> Iterable[str]:
    """返回当前已注册的能力模块名（按注册顺序）。"""
    return iter(TOOL_MODULES)


def _discover_and_register_modules() -> None:
    """扫描 tools/ 下所有 .py 文件，通过子进程逐一触发自注册。"""
    # 清空 registry
    _REGISTRY_FILE.write_text(json.dumps([]))

    # 扫描模块
    import pkgutil

    modules: list[str] = []
    for _importer, modname, ispkg in pkgutil.iter_modules(__path__):
        if modname.startswith("_") or modname == "__init__" or not ispkg:
            continue
        modules.append(modname)

    # 通过子进程执行每个模块的 __register__.py，触发自注册
    env = {**os.environ, "PYTHONPATH": str(_TOOLS_DIR.parent)}
    for modname in sorted(modules):
        script = _TOOLS_DIR / modname / "__register__.py"
        subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            cwd=str(_TOOLS_DIR.parent),
            env=env,
        )

    # 汇集注册结果
    try:
        registered: list[str] = json.loads(_REGISTRY_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        registered = []

    TOOL_MODULES.clear()
    TOOL_MODULES.extend(registered)


_registered = False


def _ensure_all_registered() -> None:
    global _registered
    if not _registered:
        _discover_and_register_modules()
        _registered = True


def register_all(mcp: "FastMCP") -> None:
    """把所有已自注册的能力模块挂载到给定的 FastMCP 实例。"""
    _ensure_all_registered()
    for name in TOOL_MODULES:
        module = import_module(f"{__name__}.{name}")
        register = getattr(module, "register", None)
        if not callable(register):
            raise RuntimeError(
                f"能力模块 tools.{name} 缺少必需的 register(mcp) 函数"
            )
        register(mcp)


__all__ = ["TOOL_MODULES", "iter_tool_names", "register_all"]
