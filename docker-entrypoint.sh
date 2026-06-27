#!/usr/bin/env bash
set -euo pipefail

# 默认配置，可通过环境变量覆盖
CIF_PROJECT_DIR="${CIF_PROJECT_DIR:-/project}"
CIF_PORT="${CIF_PORT:-8090}"
CIF_STORAGE="${CIF_STORAGE:-sqlite}"
CIF_CONFIG="/app/tools_server/c_identifier_find/config.json"

log() { printf '[entrypoint] %s\n' "$*" >&2; }

# --- 检查项目目录 ---
if [ ! -d "$CIF_PROJECT_DIR" ]; then
    log "错误: 项目目录不存在: $CIF_PROJECT_DIR"
    log "请挂载卷: -v /path/to/c/project:$CIF_PROJECT_DIR"
    exit 1
fi

# --- 生成 c_identifier_find 配置 ---
mkdir -p "$(dirname "$CIF_CONFIG")"
cat > "$CIF_CONFIG" <<EOF
{
    "project_id": "$(basename "$CIF_PROJECT_DIR")",
    "project_dir": "$CIF_PROJECT_DIR",
    "http_host": "127.0.0.1",
    "http_port": $CIF_PORT,
    "storage": "$CIF_STORAGE",
    "exclude_dirs": [".git", "build", ".venv", "__pycache__", "node_modules", "dist"],
    "include_extensions": [".c", ".h"],
    "follow_symlinks": false,
    "debounce_ms": 500
}
EOF

log "配置已写入 $CIF_CONFIG"

# --- 启动 c_identifier_find HTTP 服务（后台） ---
python /app/c_identifier_find_server.py "$CIF_CONFIG" &
CIF_PID=$!
log "c_identifier_find 服务已启动 (PID: $CIF_PID)"

# --- 等待 HTTP 就绪 ---
for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:$CIF_PORT/status" >/dev/null 2>&1; then
        log "c_identifier_find 服务就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        log "警告: c_identifier_find 服务未在预期内就绪，仍继续启动 MCP 服务"
    fi
    sleep 1
done

# --- 前台启动 MCP 服务（stdio 模式，供 Cline 连接） ---
log "启动 MCP server (stdio)..."
exec python /app/server.py
