"""发现页（侧边栏「发现」）：RSS 播客分类、订阅、推荐内容。

对应前端页面 ``/discover``。首页「播客链接转写」按钮提交 RSS 链接后，
内容也会出现在这里。

接口分布在三个模块上：

* ``/api/explore/rss/category/request`` —— 分类
* ``/api/explore/rss/request`` —— 订阅源
* ``/api/explore/content/request`` —— 内容条目

Note:
    ``getPublicRssContent`` / ``getPersonalRssContent`` 虽然以 ``action``
    形式出现，但走独立路径（见
    :data:`~tingwu.endpoints.PATH_OVERRIDES`），所以用 ``request()`` 调用，
    而不是 ``direct()``。
"""

from __future__ import annotations
from typing import Any, Optional

from ..endpoints import DIRECT_ENDPOINTS

# 搜索接口不走 ``<module>/request?action``，而是独立路径（实测：
# 走 request 形式会返回 CMN.ServerError）。
DIRECT_SEARCH_RSS: str = DIRECT_ENDPOINTS["rss_search"]
DIRECT_SEARCH_CONTENT: str = DIRECT_ENDPOINTS["content_search"]

class DiscoverResource:
    """发现：播客/RSS 分类、订阅源、推荐内容。

    Example:
        >>> for c in client.discover.categories():
        ...     print(c["name"])
        >>> client.discover.public_content(need_num=12)
    """

    def __init__(self, client: Any) -> None:
        self._c = client

    # ------------------------------------------------------------------
    # 分类
    # ------------------------------------------------------------------

    def categories(
        self, *, page: int = 1, page_size: int = 100, raw: bool = False
    ) -> Any:
        """RSS 分类列表（实测 13 个：财富/社会与文化/历史/科技/商业…）。

        Returns:
            分类列表，元素含 ``rssCategoryId`` / ``code`` / ``name``。
        """
        res = self._c.request(
            "getRssCategoryList",
            params={"pageNo": page, "pageSize": page_size},
            raw=True,
        )
        return res if raw else res.get("data", res)

    def category_rss(
        self, rss_category_id: int, *, page: int = 1, page_size: int = 20
    ) -> Any:
        """某分类下的播客源列表。

        Args:
            rss_category_id: :meth:`categories` 返回的 ``rssCategoryId``。
                实测传空字符串返回空列表，传 ``categoryId``（非
                ``rssCategoryId``）也返回空——字段名不能写错。

        Example:
            >>> client.discover.category_rss(4)   # 科技
        """
        res = self._c.request(
            "getCategoryRssList",
            params={
                "rssCategoryId": rss_category_id,
                "pageNo": page,
                "pageSize": page_size,
            },
            raw=True,
        )
        return res.get("data", res)

    def sync_category_subscribe(self, **params: Any) -> Any:
        """订阅/退订某个分类。参数透传。"""
        return self._c.request("syncRssCategorySubscribeStatus", params=params)

    # ------------------------------------------------------------------
    # 订阅源
    # ------------------------------------------------------------------

    def subscribed(self, *, page: int = 1, page_size: int = 20, **params: Any) -> Any:
        """我已订阅的 RSS 源。"""
        return self._c.request(
            "getSubscribedRssList",
            params={"userId": "", "pageNo": page, "pageSize": page_size, **params},
        )

    def subscribe_status(self) -> Any:
        """订阅源是否有更新（``subscriptionUpdateNum``）。"""
        return self._c.request("getSubscribeUpdateStatus")

    def rss_info(self, **params: Any) -> Any:
        """单个 RSS 源详情。参数透传（需带 ``rssId``）。"""
        return self._c.request("getRssInfo", params=params)

    def sync_subscribe(self, **params: Any) -> Any:
        """订阅/退订某个 RSS 源。参数透传。"""
        return self._c.request("syncRssSubscribeStatus", params=params)

    def search(self, keyword: str, *, page: int = 1, page_size: int = 5, raw: bool = False) -> Any:
        """搜索播客（RSS 源）。

        Args:
            keyword: 搜索词（参数名是 ``matchText``，不是 ``keyword``）。
            page: 页码（从 1 起）。
            page_size: 每页条数（前端用 5）。
            raw: True 返回完整响应（含 ``total``，在 ``data`` 里）。

        Returns:
            命中列表；``raw=True`` 时返回整个响应体。

        Note:
            路径是 ``/explore/rss/search``，不是 ``/explore/rss/request``；
            结果在 ``data.highlights``（非 ``list``），标题带
            ``<span class="s1">`` 高亮标签，展示前需自行去标签。
        """
        res = self._c.request(
            "searchRssEs",
            endpoint=DIRECT_SEARCH_RSS,
            params={"matchText": keyword, "pageNo": page, "pageSize": page_size},
            raw=True,
        )
        if raw:
            return res
        return (res.get("data") or {}).get("highlights", [])

    def search_items(
        self, keyword: str, *, page: int = 1, page_size: int = 5, raw: bool = False
    ) -> Any:
        """搜索播客单集（内容条目），用法同 :meth:`search`。"""
        res = self._c.request(
            "searchRssItemEs",
            endpoint=DIRECT_SEARCH_CONTENT,
            params={"matchText": keyword, "pageNo": page, "pageSize": page_size},
            raw=True,
        )
        if raw:
            return res
        return (res.get("data") or {}).get("highlights", [])
    # ------------------------------------------------------------------
    # 内容
    # ------------------------------------------------------------------

    def public_content(
        self, *, need_num: int = 12, use_show_key: bool = True, raw: bool = False
    ) -> Any:
        """发现页推荐内容（首页/发现页默认展示的那些播客单集）。

        Args:
            need_num: 拉取条数（前端用 12）。
            use_show_key: 是否按展示键去重（前端传 ``true``）。

        Returns:
            内容列表；``raw=True`` 时返回含 ``total`` 的完整体。
            每项含 ``contentId`` / ``rssItemInfo.rssDTO``（播客元信息，
            含 ``xmlLink``，可直接喂给
            :meth:`~tingwu.resources.trans.TransResource.transcribe_net_source`）。
        """
        res = self._c.request(
            "getPublicRssContent",
            params={"needNum": need_num, "useShowKey": use_show_key},
            raw=True,
        )
        return res if raw else res.get("data", res)

    def personal_content(
        self,
        *,
        need_num: int = 12,
        before_cursor: Any = None,
        raw: bool = False,
        **params: Any,
    ) -> Any:
        """我订阅源下的内容条目（未订阅任何播客时为空）。

        Args:
            need_num: 拉取条数。
            before_cursor: 翻页游标（上一批最后一项的 ``cursor``）。

        Note:
            该接口走 ``/explore/content/request?getPersonalRssContent``
            （标准 ``?action`` 形式），与 ``getPublicRssContent`` 的独立
            路径不同——写错路径会 404。
        """
        body: dict[str, Any] = {"needNum": need_num, "useShowKey": True}
        if before_cursor is not None:
            body["beforeCursor"] = before_cursor
        body.update(params)
        res = self._c.request("getPersonalRssContent", params=body, raw=True)
        return res if raw else res.get("data", res)

    def push_card(self, *, raw: bool = False, **params: Any) -> Any:
        """发现页推荐卡片。"""
        res = self._c.request("getPushCard", params=params, raw=True)
        return res if raw else res.get("data", res)

    def rss_content(
        self, rss_id: Any, *, need_num: int = 12, before_cursor: Any = None
    ) -> Any:
        """某个播客源下的单集列表。"""
        body: dict[str, Any] = {"rssId": rss_id, "needNum": need_num, "useShowKey": True}
        if before_cursor is not None:
            body["beforeCursor"] = before_cursor
        return self._c.request("getContentInRss", params=body)

    def content_status(self, content_id: str) -> Any:
        """某条内容的处理状态（是否可转写等）。"""
        return self._c.request("getContentStatus", params={"contentId": content_id})

    def content_by_trans(
        self, trans_id: str, *, raw: bool = False, **params: Any
    ) -> Any:
        """按转写 ID 取 RSS 内容。

        Args:
            trans_id: 转写 ID。
            raw: True 返回完整响应（当前版本 ``data`` 恒为空列表，
                用 ``raw`` 才能看到真实 ``code``）。

        Note:
            参数是 ``transIdList``（数组），**不是** ``transId``——
            传 ``transId`` 会返回 ``CMN.ServerError``。
            对非 RSS 来源的转写，``data`` 为空列表（不代表报错）。
        """
        res = self._c.request(
            "getContentWithTransId",
            params={"transIdList": [trans_id], **params},
            raw=True,
        )
        return res if raw else res.get("data", res)
    def save_share(self, **params: Any) -> Any:
        """保存分享的 RSS 内容到我的记录。"""
        return self._c.request("saveExploreRss", params=params)
