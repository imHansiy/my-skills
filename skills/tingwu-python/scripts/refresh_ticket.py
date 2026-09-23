"""从 anything-analyzer 的抓包库里提取听悟 ticket 并写入缓存。
登录态失效（CMN.NotLogin）时跑这个。它扫 anything-analyzer 抓到的
cookie 快照，找出最新的 `login_aliyunid_ticket`，验证有效后写入
`~/.tingwu/ticket.json`。

**仅限装了 anything-analyzer 的环境**。普通用户没有这个抓包库，
请改用 `set_ticket.py`（从浏览器 DevTools 复制 ticket）。

用法：
    python scripts/refresh_ticket.py              # 提取 + 验证 + 写入
    python scripts/refresh_ticket.py --dry-run    # 只看找不找得到，不写入
    python scripts/refresh_ticket.py --db <路径>  # 指定抓包库

Note:
    抓包库以**只读**方式打开，绝不写入。
    输出只显示 ticket 的前 8 位，完整值不打印。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

from _bootstrap import SDK_PATH, apply_sdk_arg

DEFAULT_DB = (
    r"C:\Users\Admin\AppData\Roaming\anything-analyzer\data\anything-register.db"
)
COOKIE_NAME = "login_aliyunid_ticket"




def _mask(v: str) -> str:
    """只留前 8 位，避免泄露完整凭证。"""
    return v[:8] + "..." if len(v) > 8 else "***"


def extract_candidates(db_path: str, limit: int = 20) -> list[dict]:
    """从抓包库里取 ticket 候选，按时间倒序（最新在前）。"""
    if not os.path.isfile(db_path):
        print(
            f"没找到 anything-analyzer 的抓包库：{db_path}\n"
            f"这个脚本只适用于装了 anything-analyzer 的环境。\n"
            f"普通用户请用 set_ticket.py —— 从浏览器 DevTools 复制 ticket：\n"
            f"  python scripts/set_ticket.py \"<login_aliyunid_ticket 的值>\"\n"
            f"取值方法见 references/AUTH.md。"
        )
        raise SystemExit(1)
    uri = f"file:{db_path}?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        rows = con.execute(
            "SELECT id, timestamp, data FROM storage_snapshots "
            "WHERE domain = ? AND storage_type = 'cookie' "
            "ORDER BY timestamp DESC",
            ("tingwu.aliyun.com",),
        ).fetchall()
    finally:
        con.close()

    found: list[dict] = []
    seen: set[str] = set()
    for sid, ts, raw in rows:
        try:
            data = json.loads(raw)
        except (TypeError, ValueError):
            continue
        # data 可能是 list[{name,value,...}] 或 dict
        items = data if isinstance(data, list) else [data]
        for it in items:
            if not isinstance(it, dict):
                continue
            if it.get("name") != COOKIE_NAME:
                continue
            val = (it.get("value") or "").strip()
            if not val or val in seen:
                continue
            seen.add(val)
            found.append({"id": sid, "timestamp": ts, "value": val})
            break
        if len(found) >= limit:
            break
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description="从抓包库提取并刷新听悟 ticket")
    ap.add_argument("--db", default=DEFAULT_DB, help="抓包库路径")
    ap.add_argument(
        "--dry-run", action="store_true", help="只报告，不写入缓存"
    )
    ap.add_argument("--limit", type=int, default=10, help="最多试几个候选")
    add = ap.add_argument_group()
    add.add_argument("--sdk", default=SDK_PATH, help="SDK 路径")
    args = ap.parse_args()

    cands = extract_candidates(args.db, limit=args.limit)
    if not cands:
        print(
            f"抓包库里没找到 {COOKIE_NAME}。\n"
            f"要么在 anything-analyzer 里重新访问 tingwu.aliyun.com 并登录，\n"
            f"让它抓到新 cookie；要么直接用 set_ticket.py：\n"
            f"  python scripts/set_ticket.py \"<login_aliyunid_ticket 的值>\""
        )
        return 1

    print(f"找到 {len(cands)} 个候选（按时间倒序）：")
    for i, cd in enumerate(cands, 1):
        print(f"  {i}. {_mask(cd['value'])}  (len={len(cd['value'])})")

    if args.dry_run:
        print("\n--dry-run：不验证、不写入")
        return 0

    apply_sdk_arg(args.sdk)
    sys.path.insert(0, args.sdk)
    from tingwu import TingwuClient, Ticket

    for i, cd in enumerate(cands, 1):
        val = cd["value"]
        try:
            ok = TingwuClient(ticket=val).check()
        except Exception as e:
            print(f"  [{i}] {_mask(val)} 校验异常：{type(e).__name__}: {e}")
            continue
        if not ok:
            print(f"  [{i}] {_mask(val)} 无效")
            continue

        # 用官方 Ticket.save() 落盘，保证格式与 Ticket.load() 一致
        p = Ticket(value=val, source="anything-analyzer-snapshot").save()
        print(f"  [{i}] {_mask(val)} 有效 —— 写入 {p}")
        print("验证：python scripts/whoami.py")
        return 0

    print(
        "\n所有候选都无效。抓包库里的 cookie 也已过期，"
        "需要重新登录听悟并让 anything-analyzer 抓到新 cookie。"
    )
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
