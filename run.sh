#!/usr/bin/env bash
# 启动 demo-mcp-server，并确保使用项目内的虚拟环境。
#
# 行为：
#   1. 切到本脚本所在目录（即项目根）。
#   2. 若 .venv 不存在则用 python3 创建。
#   3. 若依赖未安装（无法 import mcp）则用 venv 内的 pip 安装一次。
#   4. 用 .venv/bin/python 启动 server.py，stdin/stdout/stderr 直通父进程。
#
# 在 Cline 的 cline_mcp_settings.json 里只需：
#   {
#     "mcpServers": {
#       "demo-mcp-server": {
#         "command": "/home/loto/work/mcp/run.sh"
#       }
#     }
#   }
set -euo pipefail

# --- 1. 定位项目根 ------------------------------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

# 所有诊断输出都写到 stderr，避免污染 stdio JSON-RPC 通道。
log() { printf '[run.sh] %s\n' "$*" >&2; }

# --- 2. 选择宿主 Python -------------------------------------------------------
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
    if command -v python3 &>/dev/null; then
        PYTHON_BIN="python3"
    elif command -v python &>/dev/null; then
        PYTHON_BIN="python"
    else
        log "错误: 未找到 python3 / python，请先安装 Python 3.10+。"
        exit 127
    fi
fi

# --- 3. 创建虚拟环境 ----------------------------------------------------------
if [[ ! -x "$VENV_PY" ]]; then
    log "未发现虚拟环境，使用 '$PYTHON_BIN' 创建 $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

# --- 4. 按需安装依赖 ----------------------------------------------------------
if ! "$VENV_PY" -c "import mcp" &>/dev/null; then
    log "首次启动: 安装依赖到虚拟环境 ..."
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet -r "$REQ_FILE"
fi

# --- 5. 启动 server -----------------------------------------------------------
exec "$VENV_PY" "$SCRIPT_DIR/server.py" "$@"
