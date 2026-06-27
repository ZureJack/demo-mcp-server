from __future__ import annotations

import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from .storage import SymbolStorage, SymbolData
from .scanner import full_scan, _collect_files
from .watcher import FileWatcher

_STORAGE: SymbolStorage | None = None
_WATCHER: FileWatcher | None = None
_CONFIG: dict = {}
_PROJECT_DIR: str = ""
_SCAN_LOCK = threading.Lock()
_SCAN_THREAD: threading.Thread | None = None
_CANCEL_EVENT = threading.Event()
_SCAN_PROGRESS: dict = {"scanned": 0, "total": 0, "status": "idle"}


def _json_response(handler: BaseHTTPRequestHandler, data, status: int = 200) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/find":
            name = params.get("name", [""])[0]
            fuzzy = params.get("fuzzy", ["0"])[0] == "1"
            if not name:
                _json_response(self, {"ok": False, "error": "missing name parameter"}, 400)
                return
            if _STORAGE is None:
                _json_response(self, {"ok": False, "error": "storage not initialized"}, 500)
                return
            if fuzzy:
                results = _STORAGE.find_by_name_contains(name)
            else:
                results = _STORAGE.find_by_name(name)
            _json_response(self, {
                "ok": True,
                "data": [_symbol_to_dict(s) for s in results],
            })

        elif parsed.path == "/status":
            if _STORAGE is None:
                _json_response(self, {"ok": False, "error": "storage not initialized"}, 500)
                return
            stats = _STORAGE.stats()
            stats["status"] = _SCAN_PROGRESS["status"]
            stats["scanned"] = _SCAN_PROGRESS["scanned"]
            stats["total"] = _SCAN_PROGRESS["total"]
            _json_response(self, {"ok": True, "data": stats})

        else:
            _json_response(self, {"ok": False, "error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/rebuild":
            self._trigger_rebuild()
        elif self.path == "/shutdown":
            _json_response(self, {"ok": True, "data": "shutting down"})
            try:
                threading.Thread(target=self.server.shutdown, daemon=True).start()
            except RuntimeError:
                pass
        else:
            _json_response(self, {"ok": False, "error": "not found"}, 404)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _trigger_rebuild(self) -> None:
        global _SCAN_THREAD, _CANCEL_EVENT, _SCAN_PROGRESS

        _CANCEL_EVENT.set()
        if _SCAN_THREAD is not None and _SCAN_THREAD.is_alive():
            _SCAN_THREAD.join(timeout=5)

        _CANCEL_EVENT.clear()
        _SCAN_PROGRESS = {"scanned": 0, "total": 0, "status": "scanning"}
        _STORAGE.clear()

        try:
            _SCAN_THREAD = threading.Thread(
                target=full_scan,
                args=(_PROJECT_DIR, _CONFIG, _STORAGE, _CANCEL_EVENT, _on_progress),
                daemon=True,
            )
            _SCAN_THREAD.start()
            _json_response(self, {"ok": True, "data": "rebuild started"})
        except RuntimeError:
            _json_response(self, {"ok": False, "error": "无法创建后台扫描线程，请手动重启容器"})


def _symbol_to_dict(sym: SymbolData) -> dict:
    return {
        "name": sym.name,
        "file_path": sym.file_path,
        "line": sym.line,
        "column": sym.column,
        "kind": sym.kind,
        "symbol_type": sym.symbol_type,
        "definition": sym.definition,
        "start_line": sym.start_line,
        "end_line": sym.end_line,
    }


def _on_progress(scanned: int, total: int) -> None:
    _SCAN_PROGRESS["scanned"] = scanned
    _SCAN_PROGRESS["total"] = total


def run_server(config: dict) -> None:
    global _STORAGE, _WATCHER, _CONFIG, _PROJECT_DIR, _SCAN_PROGRESS, _SCAN_THREAD

    _CONFIG = config
    _PROJECT_DIR = config["project_dir"]
    cache_dir = os.path.expanduser(
        f"~/.cache/c_identifier_find/{config['project_id']}"
    )
    os.makedirs(cache_dir, exist_ok=True)

    storage_type = config.get("storage", "sqlite")
    if storage_type == "memory":
        from .storage.memory import MemoryStorage
        _STORAGE = MemoryStorage()
    else:
        from .storage.sqlite import SqliteStorage
        _STORAGE = SqliteStorage(os.path.join(cache_dir, "db.sqlite3"))

    _SCAN_PROGRESS["status"] = "scanning"

    need_scan = True
    if storage_type != "memory":
        stats = _STORAGE.stats()
        if stats["symbol_count"] > 0:
            need_scan = False
            _SCAN_PROGRESS["status"] = "ready"
            print(f"[c_identifier_find] 索引已存在 ({stats['symbol_count']} 个符号)", flush=True)

    if need_scan:
        all_files = _collect_files(_PROJECT_DIR, _CONFIG)
        _SCAN_PROGRESS["total"] = len(all_files)

        def _scan_and_finish():
            full_scan(_PROJECT_DIR, _CONFIG, _STORAGE, _CANCEL_EVENT, _on_progress)
            _SCAN_PROGRESS["status"] = "ready"
            print(f"[c_identifier_find] 扫描完成", flush=True)

        try:
            _SCAN_THREAD = threading.Thread(
                target=_scan_and_finish,
                daemon=True,
            )
            _SCAN_THREAD.start()
        except RuntimeError:
            print("[c_identifier_find] 警告: 无法创建扫描线程，降级为前台同步扫描", flush=True)
            _scan_and_finish()
        print(f"[c_identifier_find] 开始扫描 {len(all_files)} 个文件...", flush=True)

    _WATCHER = FileWatcher(_PROJECT_DIR, _CONFIG, _STORAGE, _SCAN_LOCK)
    try:
        _WATCHER.start()
    except RuntimeError:
        print("[c_identifier_find] 警告: 文件监控线程创建失败（跳过 watcher）", flush=True)

    host = config.get("http_host", "127.0.0.1")
    port = config.get("http_port", 8089)

    server = HTTPServer((host, port), Handler)
    print(f"[c_identifier_find] HTTP 服务已启动: http://{host}:{port}", flush=True)
    print(f"[c_identifier_find] 项目: {_PROJECT_DIR}", flush=True)
    print(f"[c_identifier_find] 存储: {storage_type} ({cache_dir})", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _CANCEL_EVENT.set()
        _WATCHER.stop()
        if _STORAGE:
            _STORAGE.close()
        server.server_close()
