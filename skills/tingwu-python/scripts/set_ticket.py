"""给 ticket 值，验证并写入缓存。**不依赖任何抓包软件**。

适用：从浏览器 DevTools 里复制出 `login_aliyunid_ticket` 的值之后。

取值方法（任选其一）：
  1. 打开 https://tingwu.aliyun.com 并登录 → F12 → Application（应用）
     → Cookies → https://tingwu.aliyun.com → 找 `login_aliyunid_ticket`
     → 复制 Value 一列
  2. F12 → Network（网络）→ 随便点一个请求 → 请求头里找 `Cookie:`
     → 复制整段，或只抠 `login_aliyunid_ticket=` 后面那一段

用法：
    python scripts/set_ticket.py "<ticket值>"
    python scripts/set_ticket.py "Cookie: a=1; login_aliyunid_ticket=XXX; b=2"
    python scripts/set_ticket.py @cookie.txt      # 从文件读
    python scripts/set_ticket.py "<值>" --dry-run # 只验证不写入

Note:
    只打印 ticket 前 8 位，完整值不落日志。
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import SDK_PATH, apply_sdk_arg


def _mask(v: str) -> str:
    return v[:8] + "..." if len(v) > 8 else "***"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="用 ticket 值登录（不需抓包软件）"
    )
    ap.add_argument(
        "value",
        help='ticket 值、整段 Cookie，或 @文件路径',
    )
    ap.add_argument("--dry-run", action="store_true", help="只验证不写入")
    ap.add_argument("--sdk", default=SDK_PATH, help="SDK 路径")
    args = ap.parse_args()

    raw = args.value
    if raw.startswith("@"):
        try:
            with open(raw[1:], encoding="utf-8") as f:
                raw = f.read()
        except OSError as e:
            print(f"读文件失败：{e}")
            return 1

    apply_sdk_arg(args.sdk)
    sys.path.insert(0, args.sdk)
    from tingwu import TingwuClient, Ticket
    from tingwu.auth import extract_ticket_from_cookie_string

    val = extract_ticket_from_cookie_string(raw)
    if not val:
        print(
            "没能从输入里认出 ticket。\n"
            "要给 `login_aliyunid_ticket` 的值本身，或含它的整段 Cookie。\n"
            "取值方法见本文件顶部注释，或 references/AUTH.md。"
        )
        return 1

    print(f"识别到 ticket：{_mask(val)} (len={len(val)})")

    try:
        ok = TingwuClient(ticket=val).check()
    except Exception as e:
        print(f"校验异常：{type(e).__name__}: {e}")
        return 1

    if not ok:
        print(
            "这个 ticket 无效（服务端返回未登录）。\n"
            "常见原因：已过期，或你在别处重新登录过导致旧 ticket 失效。\n"
            "重新从浏览器复制一个新的再试。"
        )
        return 1

    print("校验通过：登录有效")
    if args.dry_run:
        print("--dry-run：不写入")
        return 0

    p = Ticket(value=val, source="manual-cookie").save()
    print(f"已写入 {p}")
    print("验证：python scripts/whoami.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
