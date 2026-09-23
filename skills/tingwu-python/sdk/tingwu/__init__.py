"""通义听悟 (tingwu.aliyun.com) 非官方 Python SDK。

协议级封装，直连官方 HTTP 接口，不依赖浏览器。

快速开始::

    from tingwu import TingwuClient

    # 方式一：从浏览器 cookie 串（推荐，最稳）
    client = TingwuClient.from_cookie("login_aliyunid_ticket=_wkpof_...")

    # 方式二：从 CDP 读运行中的浏览器
    from tingwu import extract_ticket_from_cdp
    client = TingwuClient(ticket=extract_ticket_from_cdp())

    # 方式三：协议账密登录（可能触发短信验证）
    from tingwu import PasswordLogin
    login = PasswordLogin("13800000000", "password")
    result = login.submit()

    # 用起来
    print(client.account.info()["userId"])
    for t in client.trans.list(dir_id=0):
        print(t["tag"]["showName"])

    tr = client.trans.result("zj78qpprw44rqxdp")
    print(tr.text[:200])
    print(tr.to_srt())

鉴权说明：听悟所有业务接口**只需一个 ``login_aliyunid_ticket`` cookie**，
无签名。该 ticket 实测有效期 ≥ 35 小时，不绑定 UA / IP，且值不轮换。
判断登录态请用 ``client.check()``（问服务端），不要看时钟。
"""

from __future__ import annotations

from ._encoding import enable_utf8_output
from .auth import (
    DEFAULT_TICKET_FILE,
    DEFAULT_UA,
    TICKET_COOKIE,
    TICKET_SAFE_TTL,
    PasswordLogin,
    Ticket,
    extract_ticket_from_cdp,
    extract_ticket_from_cookie_string,
)
from .client import BASE_URL, TingwuClient, client_from_env
from .exceptions import (
    APIError,
    AuthError,
    HTTPError,
    LoginError,
    TingwuError,
    VerificationRequired,
)
from .resources.meeting import (
    LANG_CN,
    LANG_EN,
    MEETING_TYPE,
    ORIGIN_LANG_CN,
    ORIGIN_LANG_EN,
    ROLE_SPLIT_DIALOG,
    ROLE_SPLIT_MULTI,
    ROLE_SPLIT_NONE,
    ROLE_SPLIT_SINGLE,
)
from .resources.export import (
    DOC_NOTE,
    DOC_ORIGINAL,
    DOC_PPT,
    DOC_SMART_SCAN,
    FILE_DOCX,
    FILE_MD,
    FILE_PDF,
    FILE_SRT,
)
from .resources import (
    AccountResource,
    CollectResource,
    DirectoryResource,
    DiscoverResource,
    ExportResource,
    LabResource,
    MeetingResource,
    NoticeResource,
    ShareResource,
    SubscriptionResource,
    TransResource,
    TrashResource,
)
from .resources.trans import (
    MEDIA_TYPES,
    STATUS_FAILED,
    STATUS_NAMES,
    STATUS_QUEUING,
    STATUS_SUCCESS,
    STATUS_TRANSLATING,
    STATUS_UPLOADING,
    Paragraph,
    Sentence,
    Transcript,
    parse_transcript,
)

__version__ = "0.1.0"

__all__ = [
    # 客户端
    "TingwuClient",
    "client_from_env",
    "enable_utf8_output",
    "BASE_URL",
    # 鉴权
    "Ticket",
    "PasswordLogin",
    "extract_ticket_from_cdp",
    "extract_ticket_from_cookie_string",
    "TICKET_COOKIE",
    "TICKET_SAFE_TTL",
    "DEFAULT_TICKET_FILE",
    "DEFAULT_UA",
    # 异常
    "TingwuError",
    "AuthError",
    "APIError",
    "HTTPError",
    "LoginError",
    "VerificationRequired",
    # 转写模型
    "Transcript",
    "Paragraph",
    "Sentence",
    "parse_transcript",
    "STATUS_UPLOADING",
    "STATUS_SUCCESS",
    "STATUS_FAILED",
    "STATUS_QUEUING",
    "STATUS_TRANSLATING",
    # 实时记录常量
    "MEETING_TYPE",
    "ROLE_SPLIT_NONE",
    "ROLE_SPLIT_SINGLE",
    "ROLE_SPLIT_DIALOG",
    "ROLE_SPLIT_MULTI",
    "LANG_CN",
    "LANG_EN",
    "ORIGIN_LANG_CN",
    "ORIGIN_LANG_EN",
    # 导出常量
    "DOC_ORIGINAL",
    "DOC_NOTE",
    "DOC_PPT",
    "DOC_SMART_SCAN",
    "FILE_DOCX",
    "FILE_PDF",
    "FILE_SRT",
    # 资源类（便于类型标注 / isinstance 判断）
    "AccountResource",
    "CollectResource",
    "DirectoryResource",
    "DiscoverResource",
    "ExportResource",
    "LabResource",
    "MeetingResource",
    "NoticeResource",
    "ShareResource",
    "SubscriptionResource",
    "TransResource",
    "TrashResource",
    # 上传媒体类型
    "MEDIA_TYPES",
    "STATUS_NAMES",
    "__version__",
]
