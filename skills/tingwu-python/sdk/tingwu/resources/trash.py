"""回收站接口。"""

from __future__ import annotations

from typing import Any, Sequence


class TrashResource:
    """回收站：列出、还原、彻底删除。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def list(
        self,
        *,
        keyword: str = "",
        page: int = 1,
        page_size: int = 12,
        raw: bool = False,
    ) -> Any:
        """回收站内容（侧边栏「回收站」）。

        Args:
            keyword: 按名称过滤（对应 ``filter.showNameKeyWord``）。
            page: 页码（从 1 起）。
            page_size: 每页数量（前端用 12）。
            raw: True 返回含 ``total`` 的完整体。

        Returns:
            回收站条目列表；``raw=True`` 时返回含 ``total`` 的完整体。
        """
        res = self._c.request(
            "getTrashList",
            params={
                "pageNo": page,
                "pageSize": page_size,
                "filter": {"showNameKeyWord": keyword},
            },
            raw=True,
        )
        return res if raw else res.get("data", res)

    def restore(self, trans_ids: "str | Sequence[str]", **extra: Any) -> Any:
        """还原。"""
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        return self._c.request("revertTrashes", params={"transIds": ids, **extra})

    def delete(self, trans_ids: "str | Sequence[str]", **extra: Any) -> Any:
        """彻底删除指定项。"""
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        return self._c.request("delTrashes", params={"transIds": ids, **extra})

    def empty(self, **extra: Any) -> Any:
        """清空回收站。"""
        return self._c.request("delAllTrashes", params=extra)
