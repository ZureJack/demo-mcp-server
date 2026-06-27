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

# --- 同步扫描（先建立索引，不依赖 server 内部线程） ---
python -c "
import json, os, sys
sys.path.insert(0, '/app')
from tools_server.c_identifier_find.scanner import full_scan, _collect_files
from tools_server.c_identifier_find.storage.sqlite import SqliteStorage
from tools_server.c_identifier_find.storage import SymbolData
import threading

config = json.load(open('$CIF_CONFIG'))
project_dir = config['project_dir']
cache_dir = os.path.expanduser(f'~/.cache/c_identifier_find/{config[\"project_id\"]}')
os.makedirs(cache_dir, exist_ok=True)
db_path = os.path.join(cache_dir, 'db.sqlite3')

if os.path.isfile(db_path):
    storage = SqliteStorage(db_path)
    stats = storage.stats()
    if stats['symbol_count'] > 0:
        print('[entrypoint] 索引已存在，跳过扫描')
        storage.close()
        sys.exit(0)
    storage.close()

print('[entrypoint] 开始全量扫描...')
storage = SqliteStorage(db_path)
files = _collect_files(project_dir, config)
total = len(files)
print(f'[entrypoint] 共发现 {total} 个文件')

def _on_progress(scanned, total):
    if scanned % 500 == 0 or scanned == total:
        print(f'[entrypoint] 进度: {scanned}/{total}')

cancel = threading.Event()
full_scan(project_dir, config, storage, cancel, _on_progress)
storage.close()
print('[entrypoint] 扫描完成')
" 2>&1 | while IFS= read -r line; do log "$line"; done

# --- 启动 c_identifier_find HTTP 服务（后台，无扫描线程） ---
python /app/c_identifier_find_server.py "$CIF_CONFIG" &
CIF_PID=$!
log "c_identifier_find 服务已启动 (PID: $CIF_PID)"

# --- 等待 HTTP 就绪 ---
for i in $(seq 1 15); do
    if curl -sf "http://127.0.0.1:$CIF_PORT/status" >/dev/null 2>&1; then
        log "c_identifier_find 服务就绪"
        break
    fi
    if [ $i -eq 15 ]; then
        log "警告: c_identifier_find 服务未就绪，仍继续"
    fi
    sleep 1
done

# --- 前台启动 MCP 服务（stdio 模式，供 Cline 连接） ---
log "启动 MCP server (stdio)..."
exec python /app/server.py
