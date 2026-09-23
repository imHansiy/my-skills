"""鉴权：ticket 管理与协议登录。

## 鉴权机制（实测结论）

听悟所有业务接口**只认 cookie ``login_aliyunid_ticket``**，无签名、无 token 参数。

实测消融（对 ``/api/tingwu/account/info``）:

======================  ==========================
Cookie                  结果
======================  ==========================
无                       ``CMN.NotLogin``
仅 ``ticket``            ✅ 成功
完整 30+ 个 cookie       ✅ 成功
``pks``/``pk``/``yunpk``/``aui``/``cnaui``/``hssid``
（单独或组合）           ❌ 全部 ``CMN.NotLogin``
======================  ==========================

结论：**除 ticket 外的一切 cookie 都可省略**，包括那些 2027 年才过期的。

## 有效期

``login_aliyunid_ticket`` 在浏览器里是 session cookie（``expires=-1``），
但实测**服务端有效期 ≥ 35.6 小时**仍未失效，且期间**值从不轮换**——
同一份 ticket 在 35 小时里反复可用，而 ``isg`` / ``tfstk`` / ``atpsida``
这些风控 cookie 却在持续刷新。说明 ticket 不参与前端续期，
这个时长是它自身的寿命。

**因此不要用固定阈值判断是否该刷新**，请用
:meth:`~tingwu.client.TingwuClient.check` 直接问服务端。

不绑定 UA / Referer / Origin / 出口 IP；改动一个字符立即失效。

## 三种获取途径

1. :func:`extract_ticket_from_cdp` —— 从运行中的 Chrome/Electron 里读（最省事）
2. :func:`extract_ticket_from_cookie_string` —— 从手工复制的 cookie 串里解析
3. :class:`PasswordLogin` —— 纯协议账密登录（会撞短信风控，见类文档）
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .exceptions import LoginError, VerificationRequired

#: ticket cookie 名
TICKET_COOKIE = "login_aliyunid_ticket"

#: 本地启发式安全期（秒）。**仅供参考，不要用它决定是否刷新。**
#:
#: 实测 ticket 存活 **≥ 35.6 小时**仍未失效，且期间值从不轮换，
#: 所以任何固定阈值都只是猜测。判断登录态请用
#: :meth:`~tingwu.client.TingwuClient.check`（问服务端）。
#:
#: 保留此常量仅为 :attr:`Ticket.is_probably_valid` 提供一个宽松的粗判。
TICKET_SAFE_TTL = 24 * 60 * 60

#: 默认 UA，与真实 Chrome 对齐
DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
)

#: 默认 ticket 缓存路径
DEFAULT_TICKET_FILE = Path.home() / ".tingwu" / "ticket.json"


@dataclass
class Ticket:
    """一个听悟登录凭证。

    Attributes:
        value: ``login_aliyunid_ticket`` 的值。
        issued_at: 服务端**签发**时刻（unix 秒）。只有协议登录流程能观察到，
            从 cookie 串/CDP 拿到的 ticket 无从得知，为 ``None``。
        obtained_at: **本库拿到它**的时刻。注意这不等于签发时刻——
            从浏览器复制来的 ticket 可能已经用了很久。
        source: 来源标记，便于排查（``cdp`` / ``cookie`` / ``login`` / ``manual``）。
        extra_cookies: 额外 cookie（通常不需要，留作兜底）。
    """

    value: str
    issued_at: Optional[float] = None
    obtained_at: float = field(default_factory=time.time)
    source: str = "manual"
    extra_cookies: dict[str, str] = field(default_factory=dict)

    @property
    def age(self) -> Optional[float]:
        """ticket 真实已存在秒数。

        Returns:
            签发时刻已知时返回秒数；未知（从 cookie/CDP 获取）返回 ``None``。
        """
        if self.issued_at is None:
            return None
        return time.time() - self.issued_at

    @property
    def since_obtained(self) -> float:
        """本库持有它的秒数（与真实寿命无关）。"""
        return time.time() - self.obtained_at

    @property
    def is_probably_valid(self) -> Optional[bool]:
        """本地粗判：是否仍在安全期内。

        Returns:
            * ``True``  —— 签发时刻已知且未超 :data:`TICKET_SAFE_TTL`
            * ``False`` —— 签发时刻已知且已超
            * ``None``  —— **无法判断**（签发时刻未知）

        Warning:
            实测 ticket 存活可达 35+ 小时，任何固定阈值都只是猜测。
            本属性**不该**用来决定是否刷新；请用
            :meth:`~tingwu.client.TingwuClient.check` 直接问服务端。
            返回 ``None`` 时尤其不要当成"有效"。
        """
        age = self.age
        if age is None:
            return None
        return age < TICKET_SAFE_TTL

    def cookie_header(self) -> str:
        """拼成 Cookie 请求头。"""
        parts = [f"{TICKET_COOKIE}={self.value}"]
        parts.extend(f"{k}={v}" for k, v in self.extra_cookies.items())
        return "; ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "issued_at": self.issued_at,
            "obtained_at": self.obtained_at,
            "source": self.source,
            "extra_cookies": self.extra_cookies,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Ticket":
        return cls(
            value=d["value"],
            issued_at=(float(d["issued_at"]) if d.get("issued_at") else None),
            obtained_at=float(d.get("obtained_at") or time.time()),
            source=d.get("source", "cache"),
            extra_cookies=dict(d.get("extra_cookies") or {}),
        )

    # ---- 持久化 ----

    def save(self, path: os.PathLike[str] | str | None = None) -> Path:
        """写入磁盘（权限 0600）。"""
        p = Path(path) if path else DEFAULT_TICKET_FILE
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False), encoding="utf-8")
        try:  # Windows 下 chmod 基本无效，忽略
            os.chmod(p, 0o600)
        except OSError:
            pass
        return p

    @classmethod
    def load(cls, path: os.PathLike[str] | str | None = None) -> Optional["Ticket"]:
        """从磁盘读取；不存在或损坏时返回 ``None``。"""
        p = Path(path) if path else DEFAULT_TICKET_FILE
        if not p.is_file():
            return None
        try:
            return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, KeyError, OSError, ValueError):
            return None


def extract_ticket_from_cookie_string(raw: str) -> Optional[str]:
    """从任意 cookie 串里抠出 ticket。

    兼容整段 ``Cookie:`` 头、``name=value; name2=value2``、以及仅 ticket 值本身。

    >>> extract_ticket_from_cookie_string("a=1; login_aliyunid_ticket=XYZ; b=2")
    'XYZ'
    >>> extract_ticket_from_cookie_string("_wkpof_ABC")
    '_wkpof_ABC'
    """
    if not raw:
        return None
    s = raw.strip()
    # 完整 Cookie 头
    if s.lower().startswith("cookie:"):
        s = s.split(":", 1)[1]
    m = re.search(rf"(?:^|[\s;]){re.escape(TICKET_COOKIE)}=([^;\s]+)", s)
    if m:
        return m.group(1)
    # 传入的就是裸值：ticket 以 _wkpof_ / _ 开头且足够长
    if re.fullmatch(r"[A-Za-z0-9_\-.*$]{40,}", s):
        return s
    return None


def extract_ticket_from_cdp(
    url_filter: str = "aliyun.com",
    *,
    cdp_http: str = "http://127.0.0.1:9222",
) -> Ticket:
    """从已开启调试端口的 Chrome/Electron 里读取 ticket。

    需要浏览器以 ``--remote-debugging-port=9222`` 启动。
    听悟自己的客户端 ``anything-analyzer`` 就是 Electron，可直接读。

    Args:
        url_filter: 只取 domain 含该子串的 cookie。
        cdp_http: CDP HTTP 端点。

    Raises:
        LoginError: 连不上 CDP 或没找到 ticket。
    """
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{cdp_http}/json/version", timeout=5) as r:
            json.loads(r.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        raise LoginError(
            f"连不上 CDP ({cdp_http})：{e}。"
            f"请用 --remote-debugging-port=9222 启动浏览器。"
        ) from e

    # Network.getAllCookies 需要走 WS，这里用 /json 拿到的 ws 地址
    # 为免引入依赖，改用 CDP 的 HTTP 兼容路径不可行，故走 ws。
    try:
        import websocket  # type: ignore
    except ImportError as e:  # pragma: no cover
        raise LoginError(
            "读取 CDP 需要 websocket-client：pip install 'tingwu[browser]'"
        ) from e

    with urllib.request.urlopen(f"{cdp_http}/json/version", timeout=5) as r:
        ws_url = json.loads(r.read())["webSocketDebuggerUrl"]

    ws = websocket.create_connection(ws_url, timeout=15)
    try:
        ws.send(json.dumps({"id": 1, "method": "Network.getAllCookies"}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == 1:
                break
    finally:
        ws.close()

    if "error" in msg:
        raise LoginError(f"CDP 报错：{msg['error']}")

    for ck in msg.get("result", {}).get("cookies", []):
        if ck.get("name") != TICKET_COOKIE:
            continue
        if url_filter and url_filter not in (ck.get("domain") or ""):
            continue
        return Ticket(value=ck["value"], source="cdp")

    raise LoginError(
        f"CDP 里没找到 {TICKET_COOKIE}。请先在浏览器里登录 tingwu.aliyun.com。"
    )


# --------------------------------------------------------------------------
# 协议登录
# --------------------------------------------------------------------------

LOGIN_PAGE_URL = (
    "https://passport.aliyun.com/havanaone/login/login.htm"
    "?lang=zh_CN&appName=gpt&appEntrance=tingwu&styleType=vertical"
    "&notLoadSsoView=true&notKeepLogin=true&isMobile=false"
    "&oauth_callback=https%3A%2F%2Ftingwu.aliyun.com%2Fhome"
)

LOGIN_POST_URL = (
    "https://passport.aliyun.com/havanaone/loginLegacy/password/login.do?_bx-v=2.5.11"
)

IV_UPLOAD_URL = "https://passport.aliyun.com/iv/identity/upload_env.do"
IV_SEND_URL = "https://passport.aliyun.com/iv/mobileRpc/ivsend.do"
IV_VERIFY_URL = "https://passport.aliyun.com/iv/identity/verify_ajax.do"

_RETURN_URL = (
    "https://account.aliyun.com/login/login_aliyun?resType=html"
    "&boxEntrance=mini&loginScene=fastLogin"
    "&oauth_callback=https%3A%2F%2Ftingwu.aliyun.com%2Fhome"
    "&log_channel=dialog&log_platform=pc"
    "&login_log_entrance=official&login_method=pwd_login"
    "&log_biz=tingwu"
    "&bizPassParams=%7B%22isDialogReg%22%3Atrue%2C%22action%22"
    "%3A%22login%22%2C%22tenantName%22%3A%22tingwu%22%7D"
)


@dataclass
class LoginResult:
    """登录状态。"""

    success: bool
    ticket: Optional[Ticket] = None
    message: str = ""
    code: Optional[str] = None
    raw: Any = None


class PasswordLogin:
    """阿里云账密协议登录。

    ## 流程

    .. code-block:: text

        GET  login.htm                     -> 提取 rsaModulus / rsaExponent / _csrf
        RSA(password, PKCS#1 v1.5)         -> password2 (512 hex)
        POST loginLegacy/password/login.do -> resultCode 100
           ├─ 直接成功      -> 下发 login_aliyunid_ticket
           └─ iframeRedirect -> IV 风控：upload_env -> ivsend -> verify_ajax
                                └─ verify_ajax 通过后才下发 ticket

    ## 重要：风控 IV

    实测该流程**大概率触发短信验证**（阿里云 baxia / 无影风控）。
    ``umidToken`` 可留空（实测成功请求里它为空、``umidTag=NOT_INIT``），
    但 ``bx-ua`` 指纹与账号历史会影响风控评分。

    因此本类设计为**半自动**：登录时若撞到 IV，抛
    :class:`~tingwu.exceptions.VerificationRequired` 并带上 ``htoken``，
    由调用方拿到短信码后调用 :meth:`verify_sms` 继续。

    Example:
        >>> login = PasswordLogin("13800000000", "secret")
        >>> try:
        ...     res = login.submit()
        ... except VerificationRequired as e:
        ...     code = input(f"短信码({e.phone}): ")
        ...     res = login.verify_sms(e.htoken, code)
        >>> res.ticket.value[:20]
        '_wkpof_...'
    """

    def __init__(
        self,
        login_id: str,
        password: str,
        *,
        session: Any = None,
        user_agent: str = DEFAULT_UA,
        timeout: float = 30.0,
    ) -> None:
        import requests

        self.login_id = login_id
        self.password = password
        self.ua = user_agent
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "sec-ch-ua": '"Not:A-Brand";v="24", "Chromium";v="134"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
            }
        )
        self._csrf: Optional[str] = None
        self._modulus: Optional[str] = None
        self._exponent: Optional[str] = None

    # ---- RSA ----

    def _fetch_login_config(self) -> None:
        """拉登录页并提取公钥与 csrf。"""
        r = self.session.get(LOGIN_PAGE_URL, timeout=self.timeout)
        r.raise_for_status()
        html = r.text
        m = re.search(r'"rsaModulus":"([0-9a-fA-F]+)"', html)
        e = re.search(r'"rsaExponent":"([0-9a-fA-F]+)"', html)
        c = re.search(r'"_csrf":"([0-9a-fA-F]+)"', html)
        if not (m and e and c):
            raise LoginError(
                "登录页缺少 rsaModulus/rsaExponent/_csrf，页面结构可能已变更"
            )
        self._modulus, self._exponent, self._csrf = m.group(1), e.group(1), c.group(1)

    def _encrypt_password(self, plain: str) -> str:
        """复现前端 ohdave rsa.js 的 PKCS#1 v1.5 加密，输出小写 hex。"""
        try:
            from cryptography.hazmat.primitives.asymmetric import padding, rsa
        except ImportError as exc:  # pragma: no cover
            raise LoginError(
                "协议登录需要 cryptography：pip install 'tingwu[login]'"
            ) from exc

        if not (self._modulus and self._exponent):
            raise LoginError("请先调用 _fetch_login_config()")

        pub = rsa.RSAPublicNumbers(
            int(self._exponent, 16), int(self._modulus, 16)
        ).public_key()
        return pub.encrypt(plain.encode(), padding.PKCS1v15()).hex()

    # ---- 提交 ----

    def submit(self) -> LoginResult:
        """提交账密登录。

        Returns:
            :class:`LoginResult`；成功时 ``ticket`` 已填好。

        Raises:
            VerificationRequired: 撞到短信风控，需调用 :meth:`verify_sms`。
            LoginError: 密码错误或其他失败。
        """
        import secrets

        self._fetch_login_config()
        assert self._csrf is not None
        pw2 = self._encrypt_password(self.password)

        data = {
            "loginId": self.login_id,
            "password2": pw2,
            "keepLogin": "false",
            "isIframe": "true",
            "banThirdPartyCookie": "false",
            "documentReferer": "https://account.aliyun.com/",
            "ua": "",
            "umidGetStatusVal": "",
            "screenPixel": "1920x1080",
            "navlanguage": "zh-CN",
            "navUserAgent": self.ua,
            "navPlatform": "Win32",
            "hitRSA2048Gray": "true",
            "bizEntrance": "tingwu",
            "bizName": "gpt",
            "_csrf": self._csrf,
            "redirectType": "iframeRedirect",
            "returnUrl": _RETURN_URL,
            "bizPassParams": json.dumps(
                {"isDialogReg": True, "action": "login", "tenantName": "tingwu"},
                separators=(",", ":"),
            ),
            "umidToken": "",
            "umidTag": "NOT_INIT",
            "weiBoMpBridge": "",
            "ssoParams": "",
            "deviceId": "",
            "pageTraceId": secrets.token_hex(16),
        }
        r = self.session.post(
            LOGIN_POST_URL,
            data=data,
            timeout=self.timeout,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://passport.aliyun.com",
                "Referer": "https://passport.aliyun.com/",
                "bx-v": "2.5.11",
            },
        )
        r.raise_for_status()
        body = r.json()

        ck = self._ticket_from_session()
        if ck:
            return LoginResult(True, ck, "登录成功", raw=body)

        content = (body.get("content") or {}).get("data") or {}
        title = content.get("titleMsg") or ""
        redirect = content.get("iframeRedirectUrl")

        if redirect:
            m = re.search(r"havana_iv_token=([^&]+)", redirect)
            iv_token = m.group(1) if m else None
            htoken = self._start_iv(iv_token)
            raise VerificationRequired(
                f"触发风控验证：{title or '需短信验证'}",
                htoken=htoken,
                iv_token=iv_token,
                payload=body,
            )

        raise LoginError(f"登录失败：{title or body}", payload=body)

    # ---- IV 风控 ----

    def _start_iv(self, iv_token: Optional[str]) -> Optional[str]:
        """走 IV 流程，返回 htoken。"""
        if not iv_token:
            return None
        # upload_env 提交环境指纹；bx-ua 留空服务端也接受（实测）
        r = self.session.post(
            f"{IV_UPLOAD_URL}?htoken={iv_token}&umidfg=1&_bx-v=2.5.37",
            json={"bx-ua": "", "bx-umidtoken": ""},
            timeout=self.timeout,
            headers={"Content-Type": "text/javascript;charset=UTF-8"},
        )
        try:
            data = r.json()
            url = data.get("data") or ""
            m = re.search(r"htoken=([^&]+)", url)
            return m.group(1) if m else iv_token
        except (json.JSONDecodeError, AttributeError):
            return iv_token

    def send_sms(self, htoken: str) -> bool:
        """触发发送短信验证码。"""
        r = self.session.post(
            f"{IV_SEND_URL}?htoken={htoken}&_bx-v=2.5.37",
            json={"bx-ua": "", "bx-umidtoken": ""},
            timeout=self.timeout,
        )
        try:
            return bool(r.json().get("content", {}).get("success"))
        except (json.JSONDecodeError, AttributeError):
            return False

    def verify_sms(self, htoken: str, code: str) -> LoginResult:
        """提交短信验证码，完成后应拿到 ticket。"""
        files = {
            "_tb_token_": (None, ""),
            "tag": (None, "8"),
            "type": (None, "8"),
            "htoken": (None, htoken),
            "phonecheckcode": (None, code),
            "bx-ua": (None, ""),
        }
        r = self.session.post(
            f"{IV_VERIFY_URL}?htoken={htoken}&_bx-v=2.5.37",
            files=files,
            timeout=self.timeout,
        )
        body = r.json()
        content = body.get("content") or {}
        if content.get("isSuccess") == "true":
            ck = self._ticket_from_session()
            if ck:
                return LoginResult(True, ck, "验证成功", raw=body)
            return LoginResult(
                False, None, "验证通过但未拿到 ticket，可能还需跳转 continue.htm", raw=body
            )
        raise LoginError(f"短信验证失败：{body}", payload=body)

    # ---- 工具 ----

    def _ticket_from_session(self) -> Optional[Ticket]:
        """从 session cookie jar 里取 ticket。

        这是唯一能观察到**签发时刻**的路径（刚登录完），所以记下
        ``issued_at``，让 :attr:`Ticket.age` 有意义。
        """
        v = self.session.cookies.get(TICKET_COOKIE, domain=".aliyun.com")
        if not v:
            for ck in self.session.cookies:
                if ck.name == TICKET_COOKIE:
                    v = ck.value
                    break
        if not v:
            return None
        now = time.time()
        return Ticket(value=v, issued_at=now, obtained_at=now, source="login")
