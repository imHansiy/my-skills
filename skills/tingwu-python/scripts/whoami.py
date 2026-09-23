"""检查登录态与剩余权益。

用法：
    python scripts/whoami.py
    python scripts/whoami.py --json

退出码 0 = 登录有效。ticket 失效时提示如何恢复。
"""

from __future__ import annotations

import argparse

from _bootstrap import add_common, apply_sdk_arg, client, out

SECONDS_PER_HOUR = 3600


def main() -> int:
    ap = argparse.ArgumentParser(description="检查登录态与权益")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client(check=False)

    if not c.check():
        out({"loggedIn": False}, as_json=args.json)
        if not args.json:
            print("登录态失效：ticket 过期或已轮换。")
            print("重新获取见 references/AUTH.md")
        return 1

    w = c.whoami() or {}
    tw = w.get("tingwu") or {}
    al = w.get("aliyun") or {}
    info = {
        "loggedIn": True,
        "userId": tw.get("userId"),
        "accountId": tw.get("accountId"),
    }
    if al:
        info["aliyunUserId"] = al.get("aliyunUserId")
    try:
        info["remainingHours"] = c.subscription.remaining_hours()
    except Exception as e:
        info["remainingHours"] = f"查询失败：{str(e)[:80]}"

    if args.json:
        out(info, as_json=True)
    else:
        print(f"登录有效  userId={info['userId']}  accountId={info['accountId']}")
        print(f"剩余时长  {info['remainingHours']} 小时")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
