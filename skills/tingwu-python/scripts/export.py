"""把已有转写记录导出为 docx / pdf / srt / md。

用法：
    python scripts/export.py TRANS_ID --format srt
    python scripts/export.py TRANS_ID --format docx --out-dir ./out
    python scripts/export.py TRANS_ID --format pdf --doc ppt
    python scripts/export.py TRANS_ID --format srt --no-timestamp

Note:
    「原文」四种格式都能出；笔记 / PPT / 导读只出 pdf。
    刚转写完立刻导出常拿到 failReason=3（服务端还没生成导出物），
    本脚本会自动重试；仍失败时隔一会儿重跑即可。
"""

from __future__ import annotations

import argparse

from _bootstrap import add_common, apply_sdk_arg, client, die, out

FILE_TYPES = {"docx": 0, "pdf": 1, "srt": 2, "md": 3}
DOC_TYPES = {"original": 1, "note": 3, "ppt": 5, "scan": 7}


def main() -> int:
    ap = argparse.ArgumentParser(description="导出转写记录为文档 / 字幕")
    ap.add_argument("trans_id", help="转写记录 ID")
    ap.add_argument(
        "--format", choices=list(FILE_TYPES), default="md", help="导出格式"
    )
    ap.add_argument(
        "--doc", choices=list(DOC_TYPES), default="original", help="导出内容"
    )
    ap.add_argument("--out-dir", default=".", help="导出目录")
    ap.add_argument("--timeout", type=float, default=300, help="超时秒数")
    ap.add_argument("--no-speaker", action="store_true", help="不带说话人")
    ap.add_argument("--no-timestamp", action="store_true", help="不带时间戳")
    add_common(ap)
    args = ap.parse_args()

    if args.doc != "original" and args.format not in ("pdf",):
        print(
            f"提示：{args.doc} 只支持 pdf，已按 pdf 导出"
            f"（--format {args.format} 会被服务端忽略或失败）"
        )

    apply_sdk_arg(args.sdk)
    c = client()

    paths = c.export.save(
        args.trans_id,
        args.out_dir,
        doc_type=DOC_TYPES[args.doc],
        file_type=FILE_TYPES[args.format],
        with_speaker=not args.no_speaker,
        with_timestamp=not args.no_timestamp,
        timeout=args.timeout,
    )
    if args.json:
        out({"transId": args.trans_id, "files": paths}, as_json=True)
        return 0
    if not paths:
        die(
            "导出失败：服务端未返回文件。\n"
            "常见原因是刚转写完、导出物尚未生成（failReason=3）——"
            "隔半分钟重跑一次即可，不是代码问题。"
        )
    print("已导出: " + ", ".join(paths))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
