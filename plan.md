# c_identifier_find 设计方案

## 架构图

```
┌──────────────────────────────────────────────────────────────┐
│                        Cline (AI Client)                     │
└──────────────────────┬───────────────────────────────────────┘
                       │  MCP 协议（JSON-RPC / stdio）
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   MCP Server (demo-mcp-server)                │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              c_identifier_find 模块（客户端）              │  │
│  │                                                          │  │
│  │  ┌──────────────┐                                        │  │
│  │  │  find_c_      │  HTTP GET /find?name=xxx              │  │
│  │  │  identifier() ├─────────────────────────────────────┐ │  │
│  │  └──────────────┘                                      │ │  │
│  │  ┌──────────────┐                                      │ │  │
│  │  │  c_index_     │  HTTP GET /status                   │ │  │
│  │  │  status()     ├────────────────────────────────────┐│ │  │
│  │  └──────────────┘                                     ││ │  │
│  │                                                       ││ │  │
│  │  client.py（httpx）────────────────────────────────────┘│ │  │
│  │  formatter.py（热替换）       ← 数据 → 文本              │  │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────┬────────────────────────────────────┘
                           │  HTTP（127.0.0.1:8090）
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               c_identifier_find Server（独立进程）             │
│          tools_server/c_identifier_find/                      │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  server.py（HTTP 路由 + JSON 响应）                       │  │
│  │  ┌──────┐  ┌──────┐  ┌────────┐                         │  │
│  │  │ /find │  │/status│  │/rebuild│                         │  │
│  │  └──┬───┘  └──┬───┘  └───┬────┘                         │  │
│  └─────┼─────────┼──────────┼───────────────────────────────┘  │
│        │         │          │                                  │
│  ┌─────┴─────────┴──────────┴───────────────────────────────┐  │
│  │                      scanner.py                           │  │
│  │  遍历 .c/.h → tree-sitter 解析 → extract_symbols          │  │
│  └────────────────────────┬──────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────┴──────────────────────────────────┐  │
│  │                   storage/                                 │  │
│  │  ┌──────────────────┐    ┌──────────────────────┐         │  │
│  │  │  SymbolStorage   │    │  SqliteStorage       │         │  │
│  │  │  (ABC)           │◄───│  (~/.cache/.../      │         │  │
│  │  │                  │    │   db.sqlite3)        │         │  │
│  │  └──────────────────┘    └──────────────────────┘         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                           │                                     │
│  ┌────────────────────────┴──────────────────────────────────┐  │
│  │  watcher.py（watchdog + 防抖）                              │  │
│  │  文件变更 → debounce → 增量 reparse → 更新 storage         │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

## 目录结构

### 项目根目录

```
c_identifier_find_server.py   # 入口：python c_identifier_find_server.py /path/to/config.json
```

### tools/c_identifier_find/（MCP 端）

```
tools/c_identifier_find/
├── __init__.py               # 注册 2 个工具
├── __register__.py           # 自注册
├── client.py                 # HTTP 客户端
└── formatter.py              # 格式化（热替换）
```

### tools_server/c_identifier_find/（服务端）

```
tools_server/c_identifier_find/
├── __init__.py               # 包入口
├── server.py                 # HTTP 路由 + JSON 响应
├── storage/
│   ├── __init__.py           # SymbolStorage ABC
│   ├── memory.py             # MemoryStorage
│   └── sqlite.py             # SqliteStorage
├── scanner.py                # 全量扫描 + 增量重解析
├── watcher.py                # watchdog + 防抖
├── config.json               # 默认配置模板
├── requirements.txt
└── README.md
```

## 职责划分

| 端 | 位置 | 职责 |
|----|------|------|
| **MCP 端** | `tools/c_identifier_find/` | 注册 `find_c_identifier`、`c_index_status` 工具 |
| | `client.py` | HTTP 调用 c_identifier_find Server，返回原始 JSON |
| | `formatter.py` | 将 JSON 数据格式化为可读字符串（热替换） |
| **服务端** | `tools_server/c_identifier_find/` | HTTP 路由，处理 /find /status /rebuild |
| | `scanner.py` | tree-sitter 解析 C 文件，提取符号 |
| | `watcher.py` | watchdog 监听文件变更，增量更新 |
| | `storage/` | 符号存储抽象 + SQLite 实现 |

## 通信格式（固定）

### GET /find?name=xxx&fuzzy=0

```json
{
    "ok": true,
    "data": [
        {
            "name": "spin_lock",
            "file_path": "kernel/lock/spinlock.c",
            "line": 12,
            "column": 5,
            "kind": "definition",
            "symbol_type": "function",
            "definition": "void spin_lock(spinlock_t *lock) {\n    ...\n}",
            "start_line": 12,
            "end_line": 45
        }
    ]
}
```

### GET /status

```json
{
    "ok": true,
    "data": {
        "file_count": 100,
        "symbol_count": 500,
        "status": "ready"
    }
}
```

### 错误响应

```json
{
    "ok": false,
    "error": "服务未就绪"
}
```

## 配置文件

### config.json（默认模板）

```json
{
    "project_id": "my-os",
    "project_dir": "/home/user/work/my-os",
    "http_host": "127.0.0.1",
    "http_port": 8090,
    "storage": "sqlite",
    "exclude_dirs": [".git", "build", ".venv", "__pycache__", "node_modules", "dist"],
    "include_dirs": [],
    "include_extensions": [".c", ".h"],
    "follow_symlinks": false,
    "debounce_ms": 500
}
```

## 缓存目录

```
~/.cache/c_identifier_find/<project_id>/
└── db.sqlite3
```

## 启动方式

```bash
# 终端 1：启动 c_identifier_find Server
python c_identifier_find_server.py /path/to/config.json

# 终端 2：启动 MCP Server
./run.sh
```

Cline 配置：
```json
{
    "mcpServers": {
        "demo-mcp-server": {
            "command": "/path/to/demo-mcp-server/run.sh"
        }
    }
}
```

## 存储层

### SymbolStorage 抽象基类（storage/__init__.py）

```python
from abc import ABC, abstractmethod
from typing import NamedTuple, Literal

class SymbolData(NamedTuple):
    name: str
    file_path: str
    line: int
    column: int
    kind: Literal["definition", "declaration"]
    symbol_type: Literal["function", "variable", "type", "macro", "struct", "union", "enum"]
    definition: str
    start_line: int
    end_line: int

class SymbolStorage(ABC):
    @abstractmethod
    def add_symbols(self, symbols: list[SymbolData]) -> None: ...
    @abstractmethod
    def remove_file(self, file_path: str) -> None: ...
    @abstractmethod
    def find_by_name(self, name: str) -> list[SymbolData]: ...
    @abstractmethod
    def find_by_name_contains(self, part: str) -> list[SymbolData]: ...
    @abstractmethod
    def stats(self) -> dict: ...
    @abstractmethod
    def clear(self) -> None: ...
    @abstractmethod
    def close(self) -> None: ...
```

### SqliteStorage（storage/sqlite.py）

建表：
```sql
CREATE TABLE IF NOT EXISTS symbols (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    line        INTEGER NOT NULL,
    column      INTEGER NOT NULL,
    kind        TEXT NOT NULL,
    symbol_type TEXT NOT NULL,
    definition  TEXT NOT NULL,
    start_line  INTEGER NOT NULL,
    end_line    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sym_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_sym_file ON symbols(file_path);
CREATE INDEX IF NOT EXISTS idx_sym_type ON symbols(symbol_type);
```

## 扫描器（scanner.py）

### full_scan

1. 收集文件列表（递归，排除 exclude_dirs，过滤 include_dirs/include_extensions）
2. 跳过符号链接（follow_symlinks=false）
3. 对每个文件：tree-sitter 解析 → extract_symbols
4. 每 N 个文件批量写入 storage
5. 通过回调上报进度

### extract_symbols 逻辑

| AST 节点 | kind | symbol_type | 定义范围 |
|----------|------|-------------|---------|
| `function_definition` → name | definition | function | 整个函数（含 body） |
| `declaration` → function_declarator → name | declaration | function | 整条声明 |
| `declaration` → identifier | declaration | variable | 整条声明 |
| `declaration` → init_declarator → identifier | definition | variable | 整条声明 |
| `type_definition` → type_identifier | definition | type | 整条 typedef |
| `struct_specifier` 带 body | definition | struct | 完整 `struct name { ... }` |
| `struct_specifier` 无 body | declaration | struct | `struct name;` |
| `union_specifier` 同上 | — | union | — |
| `enum_specifier` → name | definition | enum | `enum name { ... }` |
| `preproc_def` → name | definition | macro | `#define` 行（含续行符） |
| `preproc_function_def` → name | definition | macro | `#define` 行（含续行符） |

行号计算：`source[:node.start_byte].count("\n") + 1`

## 文件监听（watcher.py）

- 使用 `watchdog` 的 `Observer`
- 防抖：同一文件 500ms（可配置）内多次修改只解析一次
- 使用 `Timer` 实现
- 增量更新与全量扫描互斥（`Lock`）

## 结果格式化（formatter.py，MCP 端）

```python
def format_results(data: list[dict], query: str) -> str:
    ...

def _fallback_format(data: list[dict], query: str) -> str:
    ...
```

- 输入：HTTP 返回的 `data` 列表（每个元素为符号原始 JSON）
- 输出：格式化字符串
- 每次查询 `importlib.reload` 动态加载，修改即时生效
- 改写出错时自动 fallback 到内置格式

## 工具 API（MCP 端）

| 工具 | 功能 |
|------|------|
| `find_c_identifier(name, fuzzy?)` | HTTP GET /find → formatter.format_results → 返回字符串 |
| `c_index_status()` | HTTP GET /status → 返回状态字符串 |

## server 启动流程

```
1. python c_identifier_find_server.py /path/to/config.json
2. 读取 config.json
3. 计算 cache 路径: ~/.cache/c_identifier_find/<project_id>/
4. 实例化 storage（memory/sqlite）
5. 如果 db 不存在 → 全量扫描
6. 如果 db 已存在 → 增量扫描变更文件
7. 启动 watchdog，开始监听
8. 启动 HTTP 服务（127.0.0.1:port）
9. ready

MCP Server 端独立启动，无需做进程管理
```

## 关键设计要点

- 两个独立进程：MCP Server（客户端） + c_identifier_find Server（服务端）
- HTTP 通信，JSON 格式固定
- formatter.py 在客户端侧，用户可自定义输出
- 每个项目独享一个 c_identifier_find Server 进程
- 数据存储在 `~/.cache/c_identifier_find/<project_id>/` 下
- 存储层抽象，可替换为不同后端
- Tree-sitter 解析 C AST，提取完整定义（非仅行号）
- Watchdog 监听文件变更 + 防抖处理
- 全量扫描与增量更新互斥（Lock）
- 支持模糊搜索
