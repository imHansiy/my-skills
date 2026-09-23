"""账号相关接口。"""

from __future__ import annotations

from typing import Any, Optional

from ..endpoints import ACTION_MODULE


class AccountResource:
    """账号信息、绑定状态、权益。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def info(self) -> dict[str, Any]:
        """听悟侧账号信息。

        Returns:
            含 ``userId``（听悟内部 ID）、``accountId``、``encodedUsername`` 等。

        Note:
            注意与 :meth:`aliyun_info` 的 ``userId`` 区分：听悟业务接口
            用的是本方法的 ``userId``。
        """
        return self._c.direct("account_info", method="GET")

    def aliyun_info(self) -> dict[str, Any]:
        """阿里云侧账号信息（含 ``aliyunUserId``、手机号、邮箱）。"""
        return self._c.direct("aliyun_user_info", method="GET")

    def third_info(self) -> dict[str, Any]:
        """第三方（阿里云盘）绑定信息。"""
        return self._c.direct("aliyun_user_third_info", method="GET")

    def report_source(self, source_type: str = "other", source_id: str = "5176.28158796") -> Any:
        """上报来源（前端进入页面时会调用，通常无需手动）。"""
        return self._c.direct(
            "aliyun_user_source",
            body={"sourceType": source_type, "sourceId": source_id, "client": "web"},
        )

    def is_login(self) -> bool:
        """探测登录态是否有效。"""
        try:
            self._c.direct("account_info", method="GET", body=None)
            return True
        except Exception:
            return False

    def fuzzy_search(self, keyword: str, **extra: Any) -> Any:
        """听悟内模糊搜索。"""
        return self._c.request("fuzzySearchInBiz", params={"keyword": keyword, **extra})

    # ---- 阿里云盘绑定 ----

    def bind_aliyundrive(self, **params: Any) -> Any:
        """绑定阿里云盘。"""
        return self._c.direct("aliyundrive_bind", body=params)

    def unbind_aliyundrive(self, **params: Any) -> Any:
        """解绑阿里云盘。"""
        return self._c.direct("aliyundrive_unbind", body=params)

    # ---- 教育邮箱 ----

    def send_edu_email(self, email: str) -> Any:
        """发送教育邮箱验证邮件。"""
        return self._c.direct("send_edu_email", body={"email": email})
