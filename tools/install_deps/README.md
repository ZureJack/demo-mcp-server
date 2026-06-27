# install_deps — 依赖安装能力

按需安装各能力模块的 Python 依赖。

## 工具

### install_deps_for_modules

安装指定能力模块的依赖（读取模块目录下的 `requirements.txt`）。

| 参数 | 类型 | 说明 |
|------|------|------|
| `modules` | `list[str] \| None` | 能力模块名列表（如 `["time_tools", "file_tools"]`），不传或传 `None` 则安装所有模块 |

**返回**：每个模块的安装结果汇总。

## CLI 用法

```bash
python tools/install_deps/install-deps.py                    # 安装所有模块
python tools/install_deps/install-deps.py time_tools         # 仅指定模块
```

## 依赖

无（仅使用 Python 标准库）。
