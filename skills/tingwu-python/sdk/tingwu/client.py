"""核心 HTTP 客户端。"""

from __future__ import annotations

import time
from typing import Any, Callable, Mapping, Optional

from .auth import DEFAULT_UA, TICKET_COOKIE, Ticket, extract_ticket_from_cookie_string
from .endpoints import (
    ACTION_MODULE,
    DEFAULT_VERSION,
    DIRECT_ENDPOINTS,
    MODULE_PATHS,
    endpoint_for_action,
)
from .exceptions import APIError, AuthError, HTTPError

BASE_URL = "https://tingwu.aliyun.com"
API_PREFIX = "/api"

#: 服务端表示未登录的业务码
NOT_LOGIN_CODE = "CMN.NotLogin"

#: 默认重试次数（仅对网络错误与 5xx）
DEFAULT_RETRIES = 2

#: 默认超时（秒）。取 60 而非 30：``/trans/getTransResult`` 对大记录
#: （实测 2.7 万字）响应耗时可达 25 秒，30 秒会偶发超时。
DEFAULT_TIMEOUT = 60.0


class TingwuClient:
    """通义听悟客户端。

    典型用法::

        from tingwu import TingwuClient

        # 1) 从浏览器 cookie 串
        client = TingwuClient.from_cookie("login_aliyunid_ticket=_wkpof_...")

        # 2) 或从磁盘缓存（首次会提示登录）
        client = TingwuClient(ticket=Ticket.load())

        # 3) 直接用现成 ticket
        client = TingwuClient(ticket="login_aliyunid_ticket=_wkpof_...")

        client.account.info()
        for t in client.trans.list(dir_id=0):
            print(t["showName"], t["transId"])

    Args:
        ticket: :class:`~tingwu.auth.Ticket`、cookie 串或裸 ticket 值。
        user_agent: 覆盖默认 UA（通常不需要，服务端不校验）。
        timeout: 单请求超时秒数。
        retries: 网络错误/5xx 的重试次数。
        auto_refresh: 遇 ``CMN.NotLogin`` 时是否调用 ``on_auth_expired``。
        on_auth_expired: 刷新回调，返回新的 :class:`Ticket` 或 cookie 串。
            没有该回调时直接抛 :class:`~tingwu.exceptions.AuthError`。
        session: 复用外部 ``requests.Session``。
    """

    def __init__(
        self,
        ticket: "Ticket | str | None" = None,
        *,
        user_agent: str = DEFAULT_UA,
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRIES,
        auto_refresh: bool = True,
        on_auth_expired: Optional[Callable[[], "Ticket | str | None"]] = None,
        session: Any = None,
        base_url: str = BASE_URL,
    ) -> None:
        import requests

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = max(0, retries)
        self.auto_refresh = auto_refresh
        self.on_auth_expired = on_auth_expired
        self.user_agent = user_agent
        self.session = session or requests.Session()
        self._ticket: Optional[Ticket] = None

        if ticket is not None:
            self.ticket = ticket

        # 子模块（延迟绑定，见下方 property）
        self._account = None
        self._trans = None
        self._directory = None
        self._share = None
        self._notice = None
        self._subscription = None
        self._trash = None
        self._lab = None
        self._collect = None
        self._discover = None
        self._export = None
        self._meeting = None

    # ------------------------------------------------------------------
    # ticket
    # ------------------------------------------------------------------

    @property
    def ticket(self) -> Optional[Ticket]:
        return self._ticket

    @ticket.setter
    def ticket(self, value: "Ticket | str") -> None:
        if isinstance(value, Ticket):
            self._ticket = value
        else:
            v = extract_ticket_from_cookie_string(value)
            if not v:
                raise ValueError(f"无法解析 ticket：{value[:40]!r}")
            self._ticket = Ticket(value=v, source="manual")

    @classmethod
    def from_cookie(cls, cookie: str, **kw: Any) -> "TingwuClient":
        """从 cookie 串构造（整段 ``Cookie:`` 头也行）。"""
        return cls(ticket=cookie, **kw)

    @classmethod
    def from_ticket_file(cls, path: Any = None, **kw: Any) -> "TingwuClient":
        """从磁盘缓存构造；无缓存时抛 :class:`~tingwu.exceptions.AuthError`。"""
        from .auth import DEFAULT_TICKET_FILE

        tk = Ticket.load(path or DEFAULT_TICKET_FILE)
        if tk is None:
            raise AuthError(f"未找到 ticket 缓存：{path or DEFAULT_TICKET_FILE}")
        return cls(ticket=tk, **kw)

    def refresh_ticket(self) -> bool:
        """调用 ``on_auth_expired`` 刷新 ticket。成功返回 True。"""
        if not self.on_auth_expired:
            return False
        new = self.on_auth_expired()
        if new is None:
            return False
        self.ticket = new
        return True

    # ------------------------------------------------------------------
    # 登录态探测
    # ------------------------------------------------------------------

    def check(self, *, refresh: Optional[bool] = None) -> bool:
        """主动探测登录态是否真实有效。

        比按时间估算（:attr:`Ticket.is_probably_valid`）可靠得多：
        实测 ticket 存活可达 35+ 小时，远超任何固定阈值，所以
        **判断是否该刷新应该问服务端，而不是看时钟**。

        Args:
            refresh: 失效时是否尝试刷新后重试。
                ``None``（默认）沿用客户端的 ``auto_refresh`` 设置。

        Returns:
            True 表示登录态有效（或刷新后有效）。

        Note:
            本方法**不抛** :class:`~tingwu.exceptions.AuthError`——探测失败
            返回 False 即可，便于直接用在 ``if`` 里。

        Example:
            >>> if not client.check():
            ...     client.ticket = extract_ticket_from_cdp()
        """
        do_refresh = self.auto_refresh if refresh is None else refresh
        # 临时关掉自动刷新，避免 check 内部抛 AuthError
        prev = self.auto_refresh
        self.auto_refresh = False
        try:
            try:
                self.direct("account_info", method="GET")
                return True
            except AuthError:
                if not do_refresh:
                    return False
                # 刷新后重试一次
                if not self.refresh_ticket():
                    return False
                try:
                    self.direct("account_info", method="GET")
                    return True
                except AuthError:
                    return False
            except (APIError, HTTPError):
                # 网络/服务端问题，不代表登录态失效
                raise
        finally:
            self.auto_refresh = prev

    def ensure_login(self, refresh: Optional[bool] = None) -> None:
        """确保登录态有效，否则抛 :class:`~tingwu.exceptions.AuthError`。

        适合放在长任务开头，避免跑到一半才发现掉线。

        Example:
            >>> client.ensure_login()
            >>> for item in client.trans.iter_all():
            ...     process(item)
        """
        if not self.check(refresh=refresh):
            raise AuthError("登录态无效，且未能刷新。请更新 ticket。")

    def check_or_raise(self) -> dict[str, Any]:
        """:meth:`check` 的严格版：返回账号信息，失败抛异常。

        适合需要"顺便拿到账号信息"的场景，省掉一次请求。

        Returns:
            :meth:`~tingwu.resources.account.AccountResource.info` 的结果。

        Example:
            >>> me = client.check_or_raise()
            >>> print(me["userId"])
        """
        self.ensure_login()
        return self.account.info()

    # ------------------------------------------------------------------
    # 请求
    # ------------------------------------------------------------------

    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> dict[str, str]:
        h = {
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{self.base_url}/home",
            "Origin": self.base_url,
        }
        if self._ticket is not None:
            h["Cookie"] = self._ticket.cookie_header()
        if extra:
            h.update(extra)
        return h

    def request(
        self,
        action: str,
        /,
        *,
        endpoint: Optional[str] = None,
        params: Optional[Mapping[str, Any]] = None,
        method: str = "POST",
        version: str = DEFAULT_VERSION,
        with_version: bool = True,
        raw: bool = False,
    ) -> Any:
        """按 action 调用接口（自动定位模块与路径）。

        Args:
            action: 接口动作名，如 ``"getTransList"``。
            endpoint: 覆盖自动解析出的路径（``/api`` 之后的部分）。
            params: 业务参数，会与 ``action`` / ``version`` 合并。
            method: ``POST``（默认）或 ``GET``。
            version: 协议版本，默认 ``1.0``。
            with_version: 是否在 body 里带 ``version``。
            raw: 为 True 时返回完整响应体（不剥 ``data``）。

        Returns:
            响应体里的 ``data`` 字段（``raw=True`` 时返回整个 body）。
        """
        path = endpoint or endpoint_for_action(action)
        body: dict[str, Any] = {"action": action}
        if with_version:
            body["version"] = version
        if params:
            body.update(params)
        return self._call(path, method=method, body=body, raw=raw)

    def call_path(
        self,
        path: str,
        /,
        *,
        method: str = "POST",
        body: Optional[Mapping[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        """直接按路径调用（用于 :data:`~tingwu.endpoints.DIRECT_ENDPOINTS`）。"""
        return self._call(path, method=method, body=dict(body) if body else None, raw=raw)

    def direct(
        self,
        name: str,
        /,
        *,
        method: str = "POST",
        body: Optional[Mapping[str, Any]] = None,
        raw: bool = False,
    ) -> Any:
        """按 :data:`~tingwu.endpoints.DIRECT_ENDPOINTS` 里的别名调用。"""
        if name not in DIRECT_ENDPOINTS:
            raise KeyError(f"未知 direct endpoint：{name!r}")
        return self._call(
            DIRECT_ENDPOINTS[name], method=method, body=dict(body) if body else None, raw=raw
        )

    # ---- 内部 ----

    def _call(
        self,
        path: str,
        *,
        method: str,
        body: Optional[dict[str, Any]],
        raw: bool,
    ) -> Any:
        url = f"{self.base_url}{API_PREFIX}{path}"
        sep = "&" if "?" in path else "?"
        if "c=web" not in path:
            url = f"{url}{sep}c=web"

        method = method.upper()
        last_exc: Optional[Exception] = None
        refreshed = False

        for attempt in range(self.retries + 1):
            try:
                if method == "GET":
                    r = self.session.get(url, headers=self._headers(), timeout=self.timeout)
                else:
                    r = self.session.post(
                        url,
                        json=body,
                        headers=self._headers({"Content-Type": "application/json"}),
                        timeout=self.timeout,
                    )
            except Exception as e:  # 网络层
                last_exc = e
                if attempt < self.retries:
                    time.sleep(0.5 * (2**attempt))
                    continue
                raise HTTPError(0, f"请求失败：{e}", url=url) from e

            # 5xx 重试
            if r.status_code >= 500 and attempt < self.retries:
                last_exc = HTTPError(r.status_code, r.text[:200], url=url)
                time.sleep(0.5 * (2**attempt))
                continue

            # 未登录：若配置了刷新回调，刷新后原地重试一次；
            # 刷新过仍失败（或没有回调）则判定为鉴权失效。
            if self._is_not_login(r):
                if not refreshed and self.auto_refresh and self.refresh_ticket():
                    refreshed = True
                    continue  # 重放本次请求
                raise AuthError("登录态已失效，请刷新 ticket", payload=r.text[:500])

            return self._parse(r, url, raw=raw)

        raise HTTPError(0, f"重试耗尽：{last_exc}", url=url)

    @staticmethod
    def _is_not_login(r: Any) -> bool:
        """判断响应是否表示未登录（不抛异常）。"""
        if r.status_code in (401, 403):
            return True
        try:
            body = r.json()
        except ValueError:
            # 非 JSON（HTML 登录页）
            try:
                return "login" in r.text[:2000].lower()
            except Exception:
                return False
        if isinstance(body, dict) and body.get("code") == NOT_LOGIN_CODE:
            return True
        return False

    def _parse(self, r: Any, url: str, *, raw: bool) -> Any:
        """解析响应。未登录已在 :meth:`_call` 里处理，这里只处理业务错误。"""
        if not (200 <= r.status_code < 300):
            raise HTTPError(r.status_code, r.text[:300], url=url)

        try:
            body = r.json()
        except ValueError:
            raise APIError(f"响应不是 JSON：{r.text[:200]}", payload=r.text[:500])

        if not isinstance(body, dict):
            return body

        if body.get("success") is False:
            raise APIError(
                body.get("message") or "接口返回失败",
                code=str(body["code"]) if body.get("code") is not None else None,
                request_id=body.get("requestId"),
                payload=body,
            )

        return body if raw else body.get("data", body)

    # ------------------------------------------------------------------
    # 子模块
    # ------------------------------------------------------------------

    @property
    def account(self) -> Any:
        if self._account is None:
            from .resources.account import AccountResource

            self._account = AccountResource(self)
        return self._account

    @property
    def trans(self) -> Any:
        if self._trans is None:
            from .resources.trans import TransResource

            self._trans = TransResource(self)
        return self._trans

    @property
    def directory(self) -> Any:
        if self._directory is None:
            from .resources.directory import DirectoryResource

            self._directory = DirectoryResource(self)
        return self._directory

    @property
    def share(self) -> Any:
        if self._share is None:
            from .resources.share import ShareResource

            self._share = ShareResource(self)
        return self._share

    @property
    def notice(self) -> Any:
        if self._notice is None:
            from .resources.notice import NoticeResource

            self._notice = NoticeResource(self)
        return self._notice

    @property
    def subscription(self) -> Any:
        if self._subscription is None:
            from .resources.subscription import SubscriptionResource

            self._subscription = SubscriptionResource(self)
        return self._subscription

    @property
    def trash(self) -> Any:
        if self._trash is None:
            from .resources.trash import TrashResource

            self._trash = TrashResource(self)
        return self._trash

    @property
    def lab(self) -> Any:
        if self._lab is None:
            from .resources.lab import LabResource

            self._lab = LabResource(self)
        return self._lab

    @property
    def collect(self) -> Any:
        """收藏夹（侧边栏「我的收藏」）。"""
        if self._collect is None:
            from .resources.collect import CollectResource

            self._collect = CollectResource(self)
        return self._collect

    @property
    def discover(self) -> Any:
        """发现页（侧边栏「发现」）：播客分类、订阅源、推荐内容。"""
        if self._discover is None:
            from .resources.discover import DiscoverResource

            self._discover = DiscoverResource(self)
        return self._discover

    @property
    def meeting(self) -> Any:
        """实时记录 / 实时会议（首页「开启实时记录」）。"""
        if self._meeting is None:
            from .resources.meeting import MeetingResource

            self._meeting = MeetingResource(self)
        return self._meeting


    @property
    def export(self) -> Any:
        """官方导出（导出为 docx / pdf / srt / md 并拿下载链接）。"""
        if self._export is None:
            from .resources.export import ExportResource

            self._export = ExportResource(self)
        return self._export
    # ---- 便捷 ----

    def whoami(self) -> dict[str, Any]:
        """返回当前登录用户信息（听悟侧 + 阿里云侧合并）。"""
        tw = self.account.info()
        out: dict[str, Any] = {"tingwu": tw}
        try:
            out["aliyun"] = self.account.aliyun_info()
        except (APIError, AuthError):
            pass
        return out

    def __repr__(self) -> str:
        has = "yes" if self._ticket else "no"
        return f"<TingwuClient ticket={has} base={self.base_url}>"


def client_from_env(**kw: Any) -> TingwuClient:
    """从环境变量 ``TINGWU_TICKET`` 构造客户端。"""
    import os

    raw = os.environ.get("TINGWU_TICKET")
    if not raw:
        raise AuthError("环境变量 TINGWU_TICKET 未设置")
    return TingwuClient(ticket=raw, **kw)
