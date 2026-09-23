"""上传本地音视频到通义听悟，可选等转写完成后直接导出。

「上传 → 转写 → 导出」主力闭环，一条命令做完。

用法：
    python scripts/upload.py 会议.mp4
    python scripts/upload.py 会议.mp4 --dir "工作/odoo"
    python scripts/upload.py 会议.mp4 --wait --format srt --out-dir ./out
    python scripts/upload.py 录音.mp3 --dir 319289 --wait --format docx --json

Note:
    --dir 接受文件夹名、路径（工作/odoo）或 dirId；名字找不到会报错，
    不会静默落到根目录。媒体类型按扩展名自动推断。
"""

from __future__ import annotations

import argparse
import os

from _bootstrap import add_common, apply_sdk_arg, client, die, out

FILE_TYPES = {"docx": 0, "pdf": 1, "srt": 2, "md": 3}
DOC_TYPES = {"original": 1, "note": 3, "ppt": 5, "scan": 7}


def main() -> int:
    ap = argparse.ArgumentParser(description="上传音视频并转写/导出")
    ap.add_argument("path", help="本地音视频文件")
    ap.add_argument("--title", default="", help="记录名（默认用文件名）")
    ap.add_argument(
        "--dir", default="0", help='目标文件夹：名/路径/dirId（默认 0=默认文件夹）'
    )
    ap.add_argument("--lang", default="cn", help="语言（默认 cn）")
    ap.add_argument("--wait", action="store_true", help="等转写完成后再导出")
    ap.add_argument(
        "--format", choices=list(FILE_TYPES), default="md", help="导出格式"
    )
    ap.add_argument(
        "--doc", choices=list(DOC_TYPES), default="original", help="导出内容"
    )
    ap.add_argument("--out-dir", default=".", help="导出目录")
    ap.add_argument("--timeout", type=float, default=3600, help="等待超时秒数")
    ap.add_argument("--interval", type=float, default=10, help="轮询间隔秒数")
    add_common(ap)
    args = ap.parse_args()

    if not os.path.isfile(args.path):
        die(f"文件不存在：{args.path}")

    apply_sdk_arg(args.sdk)
    c = client()

    # dir 传 "0"/数字走 ID；否则按名/路径解析
    dir_arg: object = args.dir
    if str(args.dir).isdigit():
        dir_arg = int(args.dir)

    try:
        r = c.trans.upload_file(
            args.path,
            title=args.title,
            dir=dir_arg,
            lang=args.lang,
        )
    except ValueError as e:  # 文件夹名找不到
        die(f"{e}\n用 scripts/list_dirs.py 看有哪些文件夹")

    trans_id = r.get("transId")
    if args.json:
        out({"upload": r}, as_json=True)
    else:
        print(f"已上传  : {os.path.basename(args.path)}")
        print(f"文件夹  : {r.get('dirName')} (dirId={r.get('dirId')})")
        print(f"媒体类型: {r.get('contentType')}（{'视频' if r.get('isVideo') else '音频'}）")
        print(f"transId : {trans_id}")

    if not args.wait:
        print("\n转写在后台进行。取结果：")
        print(f"  python scripts/get_result.py {trans_id} --format srt")
        return 0

    ok = c.trans.wait(trans_id, timeout=args.timeout, interval=args.interval)
    print(f"转写{'完成' if ok else '超时'}")

    paths = c.export.save(
        trans_id,
        args.out_dir,
        doc_type=DOC_TYPES[args.doc],
        file_type=FILE_TYPES[args.format],
        timeout=args.timeout,
    )
    if args.json:
        out({"transId": trans_id, "files": paths}, as_json=True)
    elif paths:
        print("已导出: " + ", ".join(paths))
    else:
        die("导出失败：服务端未返回文件。等一会儿重跑 scripts/export.py 即可"
            "（failReason=3 表示导出物还没准备好）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
