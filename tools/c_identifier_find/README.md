# c_identifier_find（MCP 端）

MCP 工具，通过 HTTP 调用 c_identifier_find Server 查询 C 符号。

## 工具

### find_c_identifier

查找 C 标识符的定义与声明。

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 标识符名称 |
| `fuzzy` | `bool` | 是否模糊匹配（默认精确） |

### c_index_status

查看 c_identifier_find Server 的索引状态。

## 配置

编辑 `tools/c_identifier_find/config.json`：

```json
{
    "server_url": "http://127.0.0.1:8089"
}
```

## 结果格式化

编辑 `formatter.py` 可自定义输出格式，修改后即时生效。

## 依赖

- 无额外依赖（使用 Python 标准库 urllib）
