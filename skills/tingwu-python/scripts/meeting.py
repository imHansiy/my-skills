"""实时记录（会议）：创建 / 查状态 / 停止 / 改名。

用法：
    python scripts/meeting.py create --title 我的会议 --dir 0
    python scripts/meeting.py status MEETING_ID
    python scripts/meeting.py stop MEETING_ID --role-split 2
    python scripts/meeting.py rename TRANS_ID 新标题

Warning:
    create 会创建**真实会议**并开始录音，用完必须 stop，
    再用 scripts/delete_trans.py 删掉记录，否则一直占着。
    实时音频推流走 WebSocket，本库只做 HTTP，不支持。
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, die, out

ROLE_SPLIT = {
    "-1": ("暂不体验", -1),
    "1": ("单人演讲", 1),
    "2": ("两人对话", 2),
    "3": ("多人讨论", 3),
}


def main() -> int:
    ap = argparse.ArgumentParser(description="实时记录（会议）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create", help="创建并开启实时记录")
    p.add_argument("--title", default="", help="记录名")
    p.add_argument("--dir", type=int, default=0, help="文件夹 dirId")

    p = sub.add_parser("status", help="查会议状态")
    p.add_argument("meeting_id")

    p = sub.add_parser("stop", help="结束录音")
    p.add_argument("meeting_id")
    p.add_argument(
        "--role-split",
        choices=list(ROLE_SPLIT),
        default="-1",
        help="-1 暂不体验 / 1 单人 / 2 两人 / 3 多人",
    )

    p = sub.add_parser("rename", help="改记录名")
    p.add_argument("trans_id")
    p.add_argument("title")

    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()

    if args.cmd == "create":
        r = c.meeting.create(dir_id=args.dir, show_name=args.title)
        out(r, as_json=True)
        print(f"\n会议已创建。meetingId={r.get('meetingId')} transId={r.get('transId')}")
        print("结束录音：")
        print(f"  python scripts/meeting.py stop {r.get('meetingId')}")
        return 0

    if args.cmd == "status":
        out(c.meeting.info(args.meeting_id), as_json=True)
        return 0

    if args.cmd == "stop":
        label, num = ROLE_SPLIT[args.role_split]
        r = c.meeting.stop(args.meeting_id, role_split=num)
        out(r, as_json=True)
        print(f"已结束录音（{label}）")
        return 0

    if args.cmd == "rename":
        # raw=True：非 raw 写请求返回 data={}，拿不到真实 code
        r = c.request(
            "syncTransTag",
            params={"transId": args.trans_id, "tag": {"showName": args.title}},
            raw=True,
        )
        ok = str(r.get("code")) == "0" or r.get("success") is True
        if args.json:
            out(r, as_json=True)
        else:
            print("已改名" if ok else f"改名失败：{r}")
        return 0 if ok else 1

    die(f"未知子命令：{args.cmd}")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
