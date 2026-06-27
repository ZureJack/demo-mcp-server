# demo-mcp-server

一个使用 **Python** 编写的 [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) Server，
可直接接入 [Cline](https://github.com/cline/cline) / Claude Desktop 等 MCP 客户端。

## 设计要点

- **始终在虚拟环境中运行**：`run.sh` 自动创建 `.venv`、安装依赖，Cline 配置只需一行 `command`。
- **主框架与能力解耦**：`server.py` 只负责启动与装配；所有业务工具 / 资源 / 提示位于 `tools/` 包内，新增能力无需改动任何现有文件。
- **能力自注册**：每个能力子包通过 `__register__.py` 自我注册，无需手动维护模块清单。
- **按需依赖**：每个能力子包维护自己的 `requirements.txt`，不使用的模块无需安装其依赖。

## 环境要求

- Python **3.10+**
- Linux / macOS（`run.sh` 为 Bash 脚本；Windows 见下方说明）

## 快速开始

### 方式一：run.sh（推荐）

```bash
git clone git@github.com:ZureJack/demo-mcp-server.git
cd demo-mcp-server
./run.sh
```

首次运行自动创建 `.venv/` 并安装核心依赖；再次启动直接进入 server。

### 方式二：pip install

```bash
pip install .
demo-mcp-server     # 启动 server
```

安装后可以直接在任意目录通过 `demo-mcp-server` 命令启动（无需 `run.sh`）。

### 可视化调试

```bash
source .venv/bin/activate
mcp dev server.py
```

## 内置能力

| 模块 | 说明 | 文档 |
|------|------|------|
| `basic` | 回显、系统信息 | [README](tools/basic/README.md) |
| `math_tools` | 算术运算 | [README](tools/math_tools/README.md) |
| `time_tools` | 当前时间（支持时区） | [README](tools/time_tools/README.md) |
| `file_tools` | 读取文本文件 | [README](tools/file_tools/README.md) |
| `resources` | MCP Resources（greeting） | [README](tools/resources/README.md) |
| `prompts` | MCP Prompts（summarize） | [README](tools/prompts/README.md) |
| `install_deps` | 按需安装模块依赖 | [README](tools/install_deps/README.md) |

## 在 Cline 中接入

在 `cline_mcp_settings.json` 中加入：

```jsonc
{
  "mcpServers": {
    "demo-mcp-server": {
      "command": "/home/loto/work/mcp/run.sh"
    }
  }
}
```

配置文件位置：
- VS Code (Linux)：`~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- VS Code (macOS)：`~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json`
- VS Code (Windows)：`%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json`

### Windows 用户

通过 WSL 调用：
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

## 添加新能力

得益于"主框架/能力"分离的设计，新增能力只需在 `tools/` 下新建一个子包，
**无需修改任何现有文件**。

### 子包结构

一个能力子包由 3 个文件组成：

```
tools/weather/               # 子包目录名即为能力名
├── __init__.py              # 能力实现：注册工具/资源/提示
├── __register__.py          # 自注册入口（一行代码）
└── requirements.txt         # （可选）本模块的外部依赖
```

### 各文件说明

#### `__init__.py`

能力实现文件。必须暴露一个 `register(mcp)` 函数，在此函数内通过装饰器注册工具/资源/提示。

```python
"""天气查询能力。"""          # 模块文档字符串

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

约定：
- 不要在模块顶层引用全局 `mcp`，保证模块与主框架解耦，便于独立导入和单元测试。
- 可以同时注册多个 tool/resource/prompt。
- 工具的参数类型注解会被 MCP SDK 自动转为 JSON Schema，客户端（如 Cline）会据此生成参数填写界面。

#### `__register__.py`

自注册入口。`register_all()` 会通过子进程执行此文件，将模块名写入 `.registry.json`。

```python
from lib.registry import register_module

register_module("weather")
```

仅此两行，不可省略。这个步骤让主框架知道存在这个能力模块。

#### `requirements.txt`（可选）

该模块的外部 Python 依赖，每行一个包名（标准 pip 格式）：

```txt
requests>=2.31.0
beautifulsoup4>=4.12.0
```

如果模块只使用 Python 标准库，此文件可以留空（或写注释说明无依赖）。

安装方式：
```bash
python tools/install_deps/install-deps.py           # 安装所有模块的依赖
python tools/install_deps/install-deps.py weather   # 只安装指定模块的依赖
```

AI agent 也可以直接调用 `install_deps_for_modules` 工具在线安装。

### 注册与生效

保存文件后，Cline 会自动发现变更并重启 MCP server。重启后即可看到新的工具——**`server.py` 和 `tools/__init__.py` 都不需要修改**。

如果想手动刷新注册信息（一般情况下不需要），可以在项目根目录执行：

```bash
PYTHONPATH=. python -c "
import tools
from mcp.server.fastmcp import FastMCP
mcp = FastMCP('test')
tools.register_all(mcp)
print('已注册模块:', tools.TOOL_MODULES)
"
```

## 常见问题

**Q1. `./run.sh: Permission denied`**
```bash
chmod +x run.sh
```

**Q2. `ModuleNotFoundError: No module named 'mcp'`**
删除 `.venv` 重新运行 `./run.sh` 即可。

**Q3. server 启动后没有任何输出**
正常行为：stdio 传输下 stdout 只用于 JSON-RPC，日志在 stderr。

**Q4. 想强制使用别的 Python 版本创建 venv**
```bash
PYTHON_BIN=/usr/bin/python3.12 ./run.sh
```

## 参考

- [MCP 规范](https://modelcontextprotocol.io/)
- [Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Cline 文档](https://docs.cline.bot/mcp-servers/configuring-mcp-servers)
