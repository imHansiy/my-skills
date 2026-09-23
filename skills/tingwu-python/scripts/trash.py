"""回收站：查看软删的记录。

删除走 scripts/delete_trans.py（软删），记录会进这里。

用法：
    python scripts/trash.py
    python scripts/trash.py --keyword 周会
    python scripts/trash.py --json
"""

from __future__ import annotations

import argparse
import sys
import time

from _bootstrap import add_common, apply_sdk_arg, client, out
from _bootstrap import add_common, apply_sdk_arg, client, out


def main() -> int:
    ap = argparse.ArgumentParser(description="查看回收站")
    ap.add_argument("--keyword", default="", help="按名称过滤")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    items = c.trash.list(keyword=args.keyword)
    if args.json:
        out(items, as_json=True)
        return 0
    if not items:
        print("(回收站为空)")
        return 0
    print(f"{'trashId':<12} {'删除时间':<18} 名称")
    print("-" * 60)
    for it in items:
        ts = it.get("deleteTime")
        when = (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(ts / 1000))
            if ts
            else "-"
        )
        print(f"{str(it.get('trashId', '')):<12} {when:<18} {it.get('showName', '')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
