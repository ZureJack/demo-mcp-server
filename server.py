"""
MCP server 主框架。

职责：
    1. 创建 FastMCP 实例（决定 server 名称与传输方式）。
    2. 检测当前 Python 是否运行在虚拟环境中（否则向 stderr 警告）。
    3. 调用 ``tools.register_all`` 把所有能力模块挂载到 server。
    4. 启动 stdio 事件循环。

**本文件不包含任何业务逻辑**——所有工具 / 资源 / 提示都位于 ``tools/`` 包内，
新增能力不需要修改本文件。

直接运行 ``python server.py`` 即可；推荐通过 ``run.sh`` 启动以确保使用虚拟环境。
"""

from __future__ import annotations

import sys

from mcp.server.fastmcp import FastMCP

from tools import register_all

# server 名称会显示在 Cline 的 MCP 面板中
SERVER_NAME = "demo-mcp-server"


def _in_virtualenv() -> bool:
    """判断当前解释器是否处于虚拟环境（venv / virtualenv / uv）。"""
    # PEP 405: 在 venv 中 sys.prefix != sys.base_prefix
    return getattr(sys, "base_prefix", sys.prefix) != sys.prefix


def _warn_if_not_in_venv() -> None:
    if _in_virtualenv():
        return
    print(
        "[demo-mcp-server] 警告: 当前未在虚拟环境中运行。\n"
        f"  解释器: {sys.executable}\n"
        "  建议使用项目根目录下的 ./run.sh 启动，或先 `source .venv/bin/activate`。",
        file=sys.stderr,
    )


def build_server() -> FastMCP:
    """构造并装配好所有能力的 FastMCP 实例（便于测试时复用）。"""
    mcp = FastMCP(SERVER_NAME)
    register_all(mcp)
    return mcp


# 模块级实例，供 `mcp dev server.py` / `mcp run server.py` 等 CLI 使用
mcp = build_server()


if __name__ == "__main__":
    _warn_if_not_in_venv()
    # 默认使用 stdio 传输：Cline 以子进程方式启动并通过 stdin/stdout 通信
    mcp.run()
