"""等待转写完成，可选随后导出。

用法：
    python scripts/wait_trans.py TRANS_ID
    python scripts/wait_trans.py TRANS_ID --timeout 1800 --interval 15
    python scripts/wait_trans.py TRANS_ID --then-export srt --out-dir ./out
"""

from __future__ import annotations

import argparse

from _bootstrap import add_common, apply_sdk_arg, client, out

FILE_TYPES = {"docx": 0, "pdf": 1, "srt": 2, "md": 3}


def main() -> int:
    ap = argparse.ArgumentParser(description="等待转写完成")
    ap.add_argument("trans_id")
    ap.add_argument("--timeout", type=float, default=3600, help="超时秒数")
    ap.add_argument("--interval", type=float, default=10, help="轮询间隔秒数")
    ap.add_argument(
        "--then-export", choices=list(FILE_TYPES), help="完成后顺带导出该格式"
    )
    ap.add_argument("--out-dir", default=".", help="导出目录")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    ok = c.trans.wait(
        args.trans_id, timeout=args.timeout, interval=args.interval
    )
    if not ok:
        out({"transId": args.trans_id, "done": False}, as_json=args.json)
        if not args.json:
            print("等待超时，转写尚未完成")
        return 1

    if args.then_export:
        paths = c.export.save(
            args.trans_id,
            args.out_dir,
            file_type=FILE_TYPES[args.then_export],
            timeout=args.timeout,
        )
        if args.json:
            out({"transId": args.trans_id, "done": True, "files": paths},
                as_json=True)
        else:
            print("转写完成，已导出: " + ", ".join(paths))
        return 0

    if args.json:
        out({"transId": args.trans_id, "done": True}, as_json=True)
    else:
        print("转写完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
