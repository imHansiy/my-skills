"""读取转写结果：全文 / 字幕 / 元信息。

本地生成字幕（不走官方导出服务，无需等导出任务）。

用法：
    python scripts/get_result.py TRANS_ID                 # 打印全文
    python scripts/get_result.py TRANS_ID --format srt    # SRT 字幕
    python scripts/get_result.py TRANS_ID --format vtt
    python scripts/get_result.py TRANS_ID --format md
    python scripts/get_result.py TRANS_ID --info          # 只看元信息
    python scripts/get_result.py TRANS_ID --format srt -o out.srt
"""

from __future__ import annotations

import argparse
import sys
import sys

from _bootstrap import add_common, apply_sdk_arg, client, die, out


def main() -> int:
    ap = argparse.ArgumentParser(description="读取转写结果")
    ap.add_argument("trans_id", help="转写记录 ID")
    ap.add_argument(
        "--format",
        choices=["text", "srt", "vtt", "md"],
        default="text",
        help="输出格式（默认 text）",
    )
    ap.add_argument("--info", action="store_true", help="只打印元信息")
    ap.add_argument("-o", "--output", help="写入文件（默认打印到 stdout）")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    try:
        tr = c.trans.result(args.trans_id)
    except Exception as e:
        die(f"取结果失败：{e}")

    if args.info:
        info = {
            "transId": args.trans_id,
            "showName": getattr(tr, "show_name", ""),
            "sentences": len(tr),
            "durationSeconds": getattr(tr, "duration", None),
            "speakers": getattr(tr, "speakers", []),
        }
        out(info, as_json=True)
        return 0

    if not len(tr):
        die("该记录还没有转写内容（可能仍在转写中，或音频无语音）")

    body = {
        "text": tr.to_text,
        "srt": tr.to_srt,
        "vtt": tr.to_vtt,
        "md": tr.to_markdown,
    }[args.format]()

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(body)
        print(f"已写入 {args.output}（{len(body)} 字符）")
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
