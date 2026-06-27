"""时间相关能力。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP


def register(mcp: "FastMCP") -> None:
    @mcp.tool()
    def get_current_time(tz: Optional[str] = None) -> str:
        """获取当前时间。

        Args:
            tz: 可选 IANA 时区名（例如 "Asia/Shanghai", "UTC",
                "America/New_York"）。未提供时使用系统本地时区。

        Returns:
            ISO-8601 格式的时间字符串。
        """
        if tz:
            try:
                now = datetime.now(ZoneInfo(tz))
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"未知的时区: {tz}") from exc
        else:
            now = datetime.now(timezone.utc).astimezone()
        return now.isoformat(timespec="seconds")

