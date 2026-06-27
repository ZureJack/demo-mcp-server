# c_identifier_find Server

独立进程，负责扫描 C 项目并构建符号索引，通过 HTTP 对外提供查询服务。

## 启动

```bash
python c_identifier_find_server.py /path/to/config.json
```

## 配置文件

```json
{
    "project_id": "my-os",
    "project_dir": "/home/user/work/my-os",
    "http_host": "127.0.0.1",
    "http_port": 8089,
    "storage": "sqlite",
    "exclude_dirs": [".git", "build", ".venv", "__pycache__", "node_modules", "dist"],
    "include_dirs": [],
    "include_extensions": [".c", ".h"],
    "follow_symlinks": false,
    "debounce_ms": 500
}
```

## HTTP API

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/find?name=xxx&fuzzy=0` | 精确/模糊查询符号 |
| `GET` | `/status` | 索引状态 |
| `POST` | `/rebuild` | 重建索引 |
| `POST` | `/shutdown` | 关闭服务 |

## 依赖

- tree-sitter
- tree-sitter-c
- watchdog
