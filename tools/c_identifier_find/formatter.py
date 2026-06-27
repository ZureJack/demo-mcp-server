from __future__ import annotations

KIND_LABEL = {"definition": "DEF", "declaration": "DEC"}
TYPE_LABEL = {
    "function": "函数",
    "variable": "变量",
    "type": "类型",
    "macro": "宏",
    "struct": "结构体",
    "union": "联合体",
    "enum": "枚举",
}


def format_results(data: list[dict], query: str) -> str:
    """将查询结果格式化为可读字符串。

    Args:
        data: HTTP 返回的 data 列表，每个元素为符号原始 JSON
        query: 本次查询的标识符名

    Returns:
        格式化后的字符串
    """
    if not data:
        return f"符号: {query}（未找到）"

    lines = [f"符号: {query}（共 {len(data)} 处）\n"]
    for r in data:
        kind = KIND_LABEL.get(r["kind"], r["kind"].upper())
        stype = TYPE_LABEL.get(r["symbol_type"], r["symbol_type"])
        file_ref = f"{r['file_path']}:{r['line']}:{r['column']}"
        header = f"  [{kind}] {file_ref}  ({stype})"
        if r["kind"] == "definition":
            lines.append(f"{header}\n\n```c\n{r['definition']}\n```")
        else:
            lines.append(f"{header}\n         {r['definition']}")

    return "\n\n".join(lines)


def _fallback_format(data: list[dict], query: str) -> str:
    """最简兜底格式，确保不崩溃。"""
    if not data:
        return f"符号 {query} 未找到"
    out = [f"符号 {query}: {len(data)} 处"]
    for r in data:
        out.append(f"  [{r['kind'][:4].upper()}] {r['file_path']}:{r['line']}")
    return "\n".join(out)
