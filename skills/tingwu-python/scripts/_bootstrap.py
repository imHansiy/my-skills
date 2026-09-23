"""所有 scripts 共用的引导层：定位 SDK、建客户端、统一输出。

别的脚本只需：

    from _bootstrap import client, out, die

把重复的「插 sys.path / 加载 ticket / 检查登录态 / UTF-8 输出」集中在这里，
scripts 目录下的脚本不要再自己拼一遍。
"""

from __future__ import annotations

import json
import os
import sys

for _stream in (sys.stdout, sys.stderr):
    # Windows 终端是 GBK，不切 UTF-8 中文会乱码（乱码≠数据损坏）
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

#: SDK 源码路径。解析顺序：环境变量 TINGWU_SDK > 同级 sdk/ 目录 > 已安装的 tingwu 包。
#: 这样 skill 仓库里开箱即用，SDK 单独放在别处时也能用环境变量指过去。
def _default_sdk_path() -> str:
    env = os.environ.get("TINGWU_SDK")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(os.path.dirname(here), "sdk")
    if os.path.isdir(os.path.join(bundled, "tingwu")):
        return bundled
    return bundled  # 不存在时由 die() 给出安装提示


SDK_PATH = _default_sdk_path()

def _ensure_path() -> None:
    if SDK_PATH not in sys.path:
        sys.path.insert(0, SDK_PATH)


def client(check: bool = True):
    """返回一个已登录的 TingwuClient。

    Args:
        check: True 时先验证登录态，失效直接退出（退出码 1）。

    Note:
        ``TingwuClient()`` **不会**自动加载 ticket 缓存，必须显式传入。
    """
    _ensure_path()
    try:
        from tingwu import TingwuClient, Ticket
    except ImportError as e:  # 未安装
        die(
            f"无法导入 tingwu：{e}\n"
            f'先执行：pip install -e "{SDK_PATH}"'
        )
    try:
        c = TingwuClient(ticket=Ticket.load().value)
    except Exception as e:
        die(f"读取 ticket 失败：{e}\n见 references/AUTH.md 重新获取")
    if check and not c.check():
        die("登录态失效（ticket 过期或已轮换）。见 references/AUTH.md 重新获取")
    return c


def out(data, *, as_json: bool = False) -> None:
    """统一输出：JSON 或对象。"""
    if as_json:
        print(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    else:
        print(data)


def emit(items, *, as_json: bool = False, empty_msg: str = "(无记录)") -> None:
    """输出一组结果；空时给一句人话而不是空列表。"""
    if not items:
        print(empty_msg)
        return
    out(items, as_json=as_json)


def die(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[valid-type]
    """打印错误并退出。"""
    print(f"错误：{msg}", file=sys.stderr)
    raise SystemExit(code)


def add_common(parser) -> None:
    """给 argparse 加上 --json / --sdk 公共参数。"""
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--sdk", default=SDK_PATH, help=f"SDK 路径（默认 {SDK_PATH}）"
    )


def apply_sdk_arg(sdk: str) -> None:
    """把 --sdk 的值接进 sys.path（要在 client() 之前调用）。"""
    global SDK_PATH
    SDK_PATH = sdk
    _ensure_path()
