"""数学相关能力。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


_ALLOWED_EXPR_CHARS = frozenset("0123456789+-*/().% \t")


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def add(a: float, b: float) -> float:
        """计算两个数之和。"""
        return a + b

    @mcp.tool()
    def calculate(expression: str) -> str:
        """对一个简单的算术表达式求值。

        仅允许数字、空白以及 ``+ - * / ( ) . %`` 运算符，
        禁止任何变量、函数或属性访问，以避免代码注入。

        Args:
            expression: 例如 ``"1 + 2 * (3 - 4)"``。

        Returns:
            表达式的字符串化结果。
        """
        if not expression or any(ch not in _ALLOWED_EXPR_CHARS for ch in expression):
            raise ValueError("表达式包含非法字符，仅允许数字与 + - * / ( ) . %")
        try:
            # 使用受限的 eval：禁用 builtins 与全部名字。
            result = eval(expression, {"__builtins__": {}}, {})  # noqa: S307
        except Exception as exc:  # pragma: no cover - 防御性
            raise ValueError(f"表达式求值失败: {exc}") from exc
        return str(result)

