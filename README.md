# demo-mcp-server

一个使用 **Python** 编写的 [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) Server，
可直接接入 [Cline](https://github.com/cline/cline) / Claude Desktop 等 MCP 客户端。

设计要点
--------

- **始终在虚拟环境中运行**：通过 `run.sh` 启动，脚本会自动创建 `.venv`、按需安装依赖，并用 venv 内的 Python 拉起 server。Cline 配置只需一行 `command`。
- **主框架与能力解耦**：`server.py` 只负责创建 FastMCP 实例、注册能力、启动事件循环；所有业务工具 / 资源 / 提示都位于独立的 `tools/` 包，新增能力**不需要改动任何现有文件**。
- **能力自注册**：每个能力子包通过 `__register__.py` 调用 `lib.registry.register_module()` 完成自我注册，无需手动维护模块清单。

---

## 项目结构

```
mcp/
├── server.py              # 主框架：装配并启动 FastMCP，不含业务逻辑
├── tools/                 # 能力包：每个子包负责一类业务能力
│   ├── __init__.py        # 自动发现 + register_all()
│   ├── basic/             # echo, system_info
│   │   ├── __init__.py
│   │   └── __register__.py
│   ├── time_tools/        # get_current_time
│   │   ├── __init__.py
│   │   └── __register__.py
│   ├── math_tools/        # add, calculate
│   │   ├── __init__.py
│   │   └── __register__.py
│   ├── file_tools/        # read_text_file
│   │   ├── __init__.py
│   │   └── __register__.py
│   ├── resources/         # greeting://{name}
│   │   ├── __init__.py
│   │   └── __register__.py
│   └── prompts/           # summarize
│       ├── __init__.py
│       └── __register__.py
├── lib/                   # 工具库
│   ├── __init__.py
│   └── registry.py        # register_module() — 能力自注册接口
├── run.sh                 # 虚拟环境启动脚本（Cline 调用入口）
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 已内置能力

### Tools（工具）

| 名称 | 子包 | 说明 |
| --- | --- | --- |
| `echo(text)` | `tools.basic` | 回显文本，连通性测试 |
| `system_info()` | `tools.basic` | 返回平台、Python、是否在 venv 等 |
| `get_current_time(tz?)` | `tools.time_tools` | 获取当前时间，支持 IANA 时区 |
| `add(a, b)` | `tools.math_tools` | 两数相加 |
| `calculate(expression)` | `tools.math_tools` | 安全地对算术表达式求值 |
| `read_text_file(path, max_bytes?)` | `tools.file_tools` | 读取本地文本文件 |

### Resources（资源）

- `greeting://{name}` — `tools.resources`

### Prompts（提示模板）

- `summarize(text)` — `tools.prompts`

---

## 环境要求

- Python **3.10+**
- Linux / macOS（`run.sh` 为 Bash 脚本；Windows 请见下文）

---

## 快速开始

```bash
cd /home/loto/work/mcp
./run.sh
```

首次运行 `run.sh` 会自动：

1. 在项目目录下创建 `.venv/`；
2. 安装 `requirements.txt` 中的依赖；
3. 用 `.venv/bin/python` 启动 `server.py`。

之后再次启动会跳过 1、2 直接进入第 3 步。

> 服务通过 stdio 传输 JSON-RPC，**stdout 不会有可读输出**，日志走 stderr。`Ctrl+C` 退出。

可视化调试（推荐）：

```bash
source .venv/bin/activate
mcp dev server.py
```

会弹出一个浏览器面板，可查看与手动调用 tools / resources / prompts。

---

## 在 Cline 中接入

Cline 的配置文件位置：

- VS Code (Linux)：`~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- VS Code (macOS)：`~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- VS Code (Windows)：`%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

或直接在 Cline 侧边栏 **MCP Servers → Configure MCP Servers** 打开。

将本 server 加入 `mcpServers`（**只需一行 `command`**，无需手写解释器路径）：

```jsonc
{
  "mcpServers": {
    "demo-mcp-server": {
      "command": "/home/loto/work/mcp/run.sh",
      "args": [],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

`run.sh` 会保证子进程始终运行在项目自己的 `.venv` 中，免去手填路径与版本错位问题。

### 在 Cline 中验证

> 调用 demo-mcp-server 的 echo 工具，参数 `text="hello mcp"`

Cline 会请求执行该工具，确认后返回 `hello mcp`。

### Windows 用户

`run.sh` 是 Bash 脚本，在 Windows 上推荐通过 **WSL** 或 **Git Bash** 调用：

```jsonc
{
  "mcpServers": {
    "demo-mcp-server": {
      "command": "wsl",
      "args": ["/home/loto/work/mcp/run.sh"]
    }
  }
}
```

或直接指向虚拟环境内的 `python.exe`：

```jsonc
{
  "mcpServers": {
    "demo-mcp-server": {
      "command": "C:\\path\\to\\mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\mcp\\server.py"]
    }
  }
}
```

---

## 添加你自己的能力

得益于"主框架 / 能力"分离的设计，新增能力只需在 `tools/` 下新建一个子包，
**无需修改任何现有文件**。

### 1. 新建 `tools/weather/` 子包

```
tools/weather/
├── __init__.py       # register(mcp) + 工具实现
└── __register__.py   # 自注册入口
```

`tools/weather/__init__.py`：

```python
"""天气查询能力。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def fetch_weather(city: str) -> dict:
        """根据城市名查询天气。"""
        # ... 你的实现 ...
        return {"city": city, "temp": 25}
```

`tools/weather/__register__.py`：

```python
from lib.registry import register_module

register_module("weather")
```

### 2. 保存，让 Cline 重启该 MCP server

即可看到 `fetch_weather` 工具——**`server.py` 和 `tools/__init__.py` 都不动**。

---

**自动注册原理**：`register_all()` 会扫描 `tools/` 下所有子包，
通过子进程运行每个子包的 `__register__.py`，各文件调用 `register_module("xxx")`
将自身写入 `.registry.json`。完成扫描后再统一导入并挂载所有已注册的能力。

约定：每个能力子包必须实现 `register(mcp)`，且不要在模块顶层引用全局 `mcp`，
便于单元测试与隔离。

> 命名说明：包目录 `tools/` 指"业务能力模块集合"，内部既可以注册 MCP tools，
> 也可以注册 resources / prompts。

---

## 常见问题

**Q1. `./run.sh: Permission denied`**
- 给可执行权限：`chmod +x run.sh`。

**Q2. `ModuleNotFoundError: No module named 'mcp'`**
- 说明虚拟环境损坏。删除 `.venv` 重新运行 `./run.sh` 即可。

**Q3. server 启动后没有任何输出**
- 这是预期行为：stdio 传输下，stdout 只用于 JSON-RPC，日志在 stderr。

**Q4. 想强制使用别的宿主 Python 创建 venv**
- 设置环境变量：`PYTHON_BIN=/usr/bin/python3.12 ./run.sh`。

**Q5. server 启动时 stderr 出现"当前未在虚拟环境中运行"警告**
- 说明你直接用了系统 Python 调用 `python server.py`。改用 `./run.sh` 即可。

---

## 参考

- MCP 规范：<https://modelcontextprotocol.io/>
- Python SDK：<https://github.com/modelcontextprotocol/python-sdk>
- Cline 文档：<https://docs.cline.bot/mcp-servers/configuring-mcp-servers>
