"""按名称搜索转写记录。

用法：
    python scripts/search.py 周会
    python scripts/search.py 周会 --limit 50 --json
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, out

#: 0 进行中；1/2/3/4/11 历史
ALL_STATUS = [0, 1, 2, 3, 4, 11]


def main() -> int:
    ap = argparse.ArgumentParser(description="按名称搜索转写记录")
    ap.add_argument("keyword", help="名称关键词")
    ap.add_argument("--limit", type=int, default=20, help="最多返回条数")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    items = list(
        c.trans.iter_all(
            status=ALL_STATUS, show_name=args.keyword, max_items=args.limit
        )
    )
    if args.json:
        out(items, as_json=True)
        return 0
    if not items:
        print("(无匹配)")
        return 0
    for it in items:
        tag = it.get("tag") or {}
        print(f"{it.get('transId'):<20} {tag.get('showName', '')}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
