"""播客 / 网络音频链接转写。

用法：
    python scripts/netsource.py "https://example.com/episode.mp3"
    python scripts/netsource.py URL --title 我的播客 --dir 319289
    python scripts/netsource.py URL --json
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, die, out


def main() -> int:
    ap = argparse.ArgumentParser(description="播客/网络链接转写")
    ap.add_argument("url", help="音频直链")
    ap.add_argument("--title", default="", help="记录名")
    ap.add_argument("--dir", type=int, default=0, help="文件夹 dirId")
    ap.add_argument("--lang", default="cn", help="语言")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    # 先解析链接拿到标题/时长等元信息
    try:
        meta = c.trans.parse_net_source(args.url)
    except Exception as e:
        die(f"解析链接失败：{e}")

    entries = (meta or {}).get("data") or []
    if not entries:
        die(
            f"链接里没解析出音频条目：{meta!r}"
            "——确认给的是音频直链（.mp3/.m4a 等），不是网页地址"
        )
    if args.json:
        print("== 解析结果")
        out(meta, as_json=True)
    else:
        print(f"解析到 {len(entries)} 个条目")

    r = c.trans.transcribe_net_source(
        args.url,
        title=args.title,
        dir_id=args.dir,
        lang=args.lang,
    )
    if args.json:
        print("== 提交结果")
        out(r, as_json=True)
        return 0

    trans_id = r.get("transId") if isinstance(r, dict) else None
    if trans_id:
        print(f"transId: {trans_id}")
        print(f"取结果：python scripts/get_result.py {trans_id} --format srt")
    else:
        print(f"已提交：{r}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
