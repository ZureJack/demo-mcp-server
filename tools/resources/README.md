# resources — MCP Resources

通过 URI 模板暴露只读上下文给客户端。

## 资源

### greeting://{name}

返回一段问候语。

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | `str` | 被问候者名称 |

**返回**：问候语字符串。

## 依赖

无（仅使用 Python 标准库）。
