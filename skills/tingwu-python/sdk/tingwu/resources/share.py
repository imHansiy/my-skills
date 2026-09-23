"""分享 / 邀请接口。"""

from __future__ import annotations

from typing import Any, Optional


class ShareResource:
    """转写分享、邀请码、分享配置。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def invite_info(self) -> dict[str, Any]:
        """邀请信息，含 ``inviteCode`` 与微信二维码链接。

        Returns:
            ``{"inviteCode": "...", "inviteWeChatQRCodeLink": "https://..."}``
        """
        return self._c.request("getInviteShareInfo")

    def invite_code(self) -> Optional[str]:
        """仅取邀请码。"""
        return self.invite_info().get("inviteCode")

    def list(self, **params: Any) -> Any:
        """分享配置（含已分享列表）。"""
        return self._c.request("getShareConfig", params=params)

    def config(self) -> Any:
        """分享配置。"""
        return self._c.request("getShareConfig")

    def update(self, **params: Any) -> Any:
        """创建/更新分享。"""
        return self._c.request("updateShare", params=params)

    def sync_config(self, **params: Any) -> Any:
        """同步分享配置。"""
        return self._c.request("syncShareConfig", params=params)

    def query_update(self, **params: Any) -> Any:
        """查询分享更新状态。"""
        return self._c.request("queryShareUpdate", params=params)

    def share_to_users(self, **params: Any) -> Any:
        """分享给指定用户。"""
        return self._c.request("shareToUsers", params=params)

    def get(self, share_id: str, **params: Any) -> Any:
        """取某个分享详情。"""
        return self._c.direct("getShare", body={"shareId": share_id, **params})

    def public_config(self) -> Any:
        """公开分享配置（无需登录）。"""
        return self._c.direct("getSharePublicConfig")

    def poster_put_link(self, **params: Any) -> Any:
        """申请分享海报上传地址。"""
        return self._c.request("generateSharePosterPutLink", params=params)
