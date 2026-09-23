"""列出转写记录。

用法：
    python scripts/list_trans.py                    # 进行中的记录
    python scripts/list_trans.py --status history   # 历史（已完成的）
    python scripts/list_trans.py --status all
    python scripts/list_trans.py --dir 319289       # 只看某文件夹
    python scripts/list_trans.py --name 周会        # 按名称模糊搜
    python scripts/list_trans.py --limit 50 --json
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, out

STATUS = {
    "processing": [0],
    "history": [1, 2, 3, 4, 11],
    "all": [0, 1, 2, 3, 4, 11],
}

STATUS_NAME = {
    0: "进行中",
    1: "已完成",
    2: "已完成",
    3: "失败",
    4: "转写中",
    9: "已删除",
    10: "已删除",
    11: "已完成",
}


def main() -> int:
    ap = argparse.ArgumentParser(description="列出通义听悟转写记录")
    ap.add_argument(
        "--status",
        choices=list(STATUS),
        default="processing",
        help="processing 进行中 / history 历史 / all 全部（默认 processing）",
    )
    ap.add_argument("--dir", type=int, default=None, help="文件夹 dirId")
    ap.add_argument("--name", default="", help="按名称模糊搜索")
    ap.add_argument("--limit", type=int, default=20, help="每页条数")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    items = c.trans.list(
        dir_id=args.dir,
        status=STATUS[args.status],
        show_name=args.name,
        page_size=args.limit,
    )
    if args.json:
        out(items, as_json=True)
        return 0

    if not items:
        print("(无记录)")
        return 0
    print()
    print(f"{'transId':<20} {'状态':<8} {'字数':>7}  名称")
    print("-" * 70)
    for it in items:
        tag = it.get("tag") or {}
        st = STATUS_NAME.get(it.get("status"), str(it.get("status")))
        print(
            f"{it.get('transId', ''):<20} {st:<8} "
            f"{str(it.get('wordCount') or '-'):>7}  {tag.get('showName', '')}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
