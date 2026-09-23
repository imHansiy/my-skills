"""批量导出多条记录（自动处理频控，逐条间隔）。

用法：
    python scripts/batch_export.py ID1 ID2 ID3 --format srt --out-dir ./out
    python scripts/batch_export.py --name 周会 --format md --out-dir ./out
    python scripts/batch_export.py --dir 319289 --format docx

Note:
    服务端对连续导出有 EPO.RequestTooFast 频控，本脚本逐条之间等待
    --sleep 秒（默认 8）。个别记录失败不中断，最后汇总。
"""

from __future__ import annotations

import argparse
import time

from _bootstrap import add_common, apply_sdk_arg, client, die, out

FILE_TYPES = {"docx": 0, "pdf": 1, "srt": 2, "md": 3}
DOC_TYPES = {"original": 1, "note": 3, "ppt": 5, "scan": 7}
ALL_STATUS = [0, 1, 2, 3, 4, 11]


def main() -> int:
    ap = argparse.ArgumentParser(description="批量导出转写记录")
    ap.add_argument("trans_ids", nargs="*", help="记录 ID（可多个）")
    ap.add_argument("--name", help="按名称筛选（不传 ID 时用）")
    ap.add_argument("--dir", type=int, help="按文件夹筛选（不传 ID 时用）")
    ap.add_argument(
        "--format", choices=list(FILE_TYPES), default="srt", help="导出格式"
    )
    ap.add_argument(
        "--doc", choices=list(DOC_TYPES), default="original", help="导出内容"
    )
    ap.add_argument("--out-dir", default=".", help="导出目录")
    ap.add_argument("--limit", type=int, default=20, help="按名称筛时最多条数")
    ap.add_argument("--sleep", type=float, default=8.0, help="每条之间等待秒数")
    ap.add_argument("--timeout", type=float, default=300, help="单次导出超时")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    if args.trans_ids:
        ids = list(args.trans_ids)
    else:
        items = list(
            c.trans.iter_all(
                status=ALL_STATUS,
                dir_id=args.dir,
                show_name=args.name or "",
                max_items=args.limit,
            )
        )
        ids = [it.get("transId") for it in items if it.get("transId")]
        if not ids:
            die("没有匹配的记录。用 --name / --dir 或直接给 ID")

    print(f"共 {len(ids)} 条，格式 {args.format}")
    ok_list: list[str] = []
    failed: list[dict[str, str]] = []

    for i, tid in enumerate(ids, 1):
        try:
            paths = c.export.save(
                tid,
                args.out_dir,
                doc_type=DOC_TYPES[args.doc],
                file_type=FILE_TYPES[args.format],
                timeout=args.timeout,
            )
        except Exception as e:
            failed.append({"transId": tid, "error": str(e)[:200]})
            print(f"[{i}/{len(ids)}] {tid} 失败：{str(e)[:80]}")
        else:
            if paths:
                ok_list.extend(paths)
                print(f"[{i}/{len(ids)}] {tid} -> {len(paths)} 个文件")
            else:
                failed.append({"transId": tid, "error": "服务端未返回文件"})
                print(f"[{i}/{len(ids)}] {tid} 未返回文件")
        if i < len(ids):
            time.sleep(args.sleep)

    summary = {"ok": len(ok_list), "failed": len(failed), "files": ok_list}
    if failed:
        summary["errors"] = failed
    if args.json:
        out(summary, as_json=True)
    else:
        print(f"\n完成：成功 {len(ok_list)} 个文件，失败 {len(failed)} 条")
        for f in failed:
            print(f"  {f['transId']}: {f['error']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
