"""站内通知接口。"""

from __future__ import annotations

from typing import Any, Optional


class NoticeResource:
    """站内通知 / 公告。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def list(self, *, unread_only: bool = False) -> list[dict[str, Any]]:
        """通知列表。

        Args:
            unread_only: 仅返回未读（``read == 0``）。
        """
        data = self._c.direct("notice_list", method="GET")
        items = data or []
        if unread_only:
            items = [n for n in items if not n.get("read")]
        return items

    def home(self) -> Any:
        """首页通知摘要。"""
        return self._c.direct("notice_home")

    def detail_link(self, notice_id: int) -> Optional[str]:
        """取某条通知的详情链接。"""
        for n in self.list():
            if n.get("id") == notice_id:
                return n.get("detailLink")
        return None

    def op(self, **params: Any) -> Any:
        """标记已读等操作。"""
        return self._c.request("opNotice", params=params)
