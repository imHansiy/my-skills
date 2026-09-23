"""异常体系。"""

from __future__ import annotations

from typing import Any, Optional


class TingwuError(Exception):
    """所有听悟错误的基类。"""


class AuthError(TingwuError):
    """鉴权失败（ticket 缺失/失效/被撤销）。

    对应服务端 ``code == "CMN.NotLogin"``。
    捕获后可刷新 ticket 并重试。
    """

    def __init__(self, message: str = "Not login", *, payload: Any = None) -> None:
        super().__init__(message)
        self.payload = payload


class APIError(TingwuError):
    """业务错误：HTTP 200 但 ``success != true``。

    Attributes:
        code: 服务端业务码，如 ``CMN.ServerError`` / ``-1``。
        message: 服务端消息。
        request_id: 便于向官方排查的 requestId。
        payload: 完整响应体。
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        request_id: Optional[str] = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id
        self.payload = payload

    def __str__(self) -> str:  # pragma: no cover - 展示用
        bits = [self.message]
        if self.code:
            bits.append(f"code={self.code}")
        if self.request_id:
            bits.append(f"requestId={self.request_id}")
        return " | ".join(bits)


class HTTPError(TingwuError):
    """HTTP 层错误（非 2xx）。"""

    def __init__(self, status_code: int, message: str, *, url: str = "", payload: Any = None) -> None:
        super().__init__(f"HTTP {status_code}: {message}")
        self.status_code = status_code
        self.url = url
        self.payload = payload


class LoginError(TingwuError):
    """协议登录流程失败。"""


class VerificationRequired(LoginError):
    """登录被风控拦截，需要短信/扫码等二次验证。

    听悟/阿里云的 IV（Identity Verification）风控会要求短信验证码。
    ``htoken`` 是继续验证流程的凭据，需交给 ``verify_sms()``。

    Attributes:
        htoken: IV 流程 token，后续 verify_sms 必需。
        phone: 掩码后的手机号，如 ``180****0544``。
        iv_token: 部分流程返回的 ivToken。
    """

    def __init__(
        self,
        message: str = "需要短信验证码",
        *,
        htoken: Optional[str] = None,
        phone: Optional[str] = None,
        iv_token: Optional[str] = None,
        payload: Any = None,
    ) -> None:
        super().__init__(message)
        self.htoken = htoken
        self.phone = phone
        self.iv_token = iv_token
        self.payload = payload
