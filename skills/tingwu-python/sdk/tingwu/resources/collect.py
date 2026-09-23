"""收藏夹（侧边栏「我的收藏」）。

对应前端页面 ``/favorites``，接口为 ``/api/collect/request?getCollectList``。

Note:
    收藏接口的 ``filter`` 结构与 :meth:`~tingwu.resources.trans.TransResource.list`
    的**不同**——它用 ``source`` / ``keyword`` / ``lang`` / ``mediaType``，
    没有 ``status`` / ``showName`` / ``dirId``。实测传 ``status`` 会报
    ``COL.InvalidRequest``。
"""

from __future__ import annotations

from typing import Any, Iterator, Optional, Sequence


class CollectResource:
    """收藏：列表、收藏、取消收藏。

    Example:
        >>> for item in client.collect.iter_all():
        ...     print(item["showName"])
    """

    def __init__(self, client: Any) -> None:
        self._c = client

    def list(
        self,
        *,
        keyword: str = "",
        source: Optional[Sequence[Any]] = None,
        lang: str = "",
        media_type: str = "",
        page: int = 1,
        page_size: int = 12,
        order_desc: bool = True,
        raw: bool = False,
    ) -> Any:
        """列出收藏。

        Args:
            keyword: 名称关键词。
            source: 来源过滤；``None`` 表示不过滤（前端传空数组）。
            lang: 语言过滤，如 ``"cn"``。
            media_type: 媒体类型过滤。
            page: 页码（从 1 起）。
            page_size: 每页数量（前端用 12）。
            order_desc: 倒序。
            raw: True 返回完整响应（含 ``total``）。

        Returns:
            收藏列表；``raw=True`` 时返回含 ``total`` 的完整体。
        """
        body = {
            "filter": {
                "source": list(source) if source is not None else [],
                "keyword": keyword,
                "lang": lang,
                "mediaType": media_type,
            },
            "pageNo": page,
            "pageSize": page_size,
            "orderDesc": order_desc,
            "orderType": 0,
        }
        res = self._c.request("getCollectList", params=body, raw=True)
        return res if raw else res.get("data", [])

    def iter_all(
        self, *, page_size: int = 100, max_items: Optional[int] = None, **kw: Any
    ) -> Iterator[dict[str, Any]]:
        """自动翻页遍历全部收藏。

        Note:
            ``getCollectList`` 的 ``total`` 在**响应顶层**，不在 ``data`` 里
            （``data`` 是列表），所以这里从整包响应取 ``total``。
        """
        page = 1
        got = 0
        while True:
            res = self.list(page=page, page_size=page_size, raw=True, **kw)
            items = res.get("data") or []
            if not items:
                return
            for it in items:
                yield it
                got += 1
                if max_items and got >= max_items:
                    return
            total = res.get("total")
            if total is not None and got >= int(total):
                return
            if len(items) < page_size:
                return
            page += 1
    def add(self, ids: Any, *, type_: int = 2) -> Any:
        """收藏内容。

        Args:
            ids: 内容 ID，或 ID 列表（单集 ``contentId`` / 播客 ``rssId``）。
            type_: 收藏类型，实测 **必须传 2**；0 和 1 返回
                ``CMN.ServerError``，3 返回 ``COL.InvalidRequest``。

        Note:
            参数是 ``{"type": ..., "idList": [...]}``；``idList`` 必须是
            数组，传单个字符串会报 ``CMN.ServerError``。
        """
        id_list = list(ids) if isinstance(ids, (list, tuple, set)) else [ids]
        return self._c.request(
            "collectContent", params={"type": type_, "idList": id_list}, raw=True
        )

    def remove(self, items: Any, *, type_: int = 2) -> Any:
        """取消收藏。

        Args:
            items: 内容 ID，或 ``[{"id":..., "type":...}]`` 形式的列表。
            type_: ``items`` 为裸 ID 时使用的收藏类型（默认 2，与 :meth:`add` 一致）。

        Note:
            参数是 ``{"cancelList": [{"id":..., "type":...}]}``，
            与 :meth:`add` 的 ``type/idList`` 形状不同。
        """
        if isinstance(items, (list, tuple)) and (
            not items or isinstance(items[0], dict)
        ):
            cancel_list = list(items)
        else:
            ids = list(items) if isinstance(items, (list, tuple, set)) else [items]
            cancel_list = [{"id": i, "type": type_} for i in ids]
        return self._c.request(
            "cancelCollect", params={"cancelList": cancel_list}, raw=True
        )
