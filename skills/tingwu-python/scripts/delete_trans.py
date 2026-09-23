"""删除转写记录。

**只能软删** —— 服务端拒绝 deletePermanently=True（TRS.InvalidRequest），
软删后进回收站，可用 scripts/trash.py 查看。

用法：
    python scripts/delete_trans.py TRANS_ID
    python scripts/delete_trans.py ID1 ID2 ID3
    python scripts/delete_trans.py TRANS_ID --confirm   # 跳过交互确认
"""

from __future__ import annotations

import argparse

from _bootstrap import add_common, apply_sdk_arg, client, die, out


def main() -> int:
    ap = argparse.ArgumentParser(description="删除转写记录（软删到回收站）")
    ap.add_argument("trans_ids", nargs="+", help="记录 ID（可多个）")
    ap.add_argument("--confirm", action="store_true", help="跳过确认提示")
    add_common(ap)
    args = ap.parse_args()

    if not args.confirm:
        print(f"即将删除 {len(args.trans_ids)} 条：{', '.join(args.trans_ids)}")
        ans = input("确认？[y/N] ").strip().lower()
        if ans != "y":
            print("已取消")
            return 0

    apply_sdk_arg(args.sdk)
    c = client()

    # raw=True 才能看到真实 code / success
    res = c.request(
        "delTrans",
        params={
            "userId": "",
            "transIds": list(args.trans_ids),
            "deletePermanently": False,
        },
        raw=True,
    )
    ok = str(res.get("code")) == "0" or res.get("success") is True
    if args.json:
        out(res, as_json=True)
    elif ok:
        print(f"已删除 {len(args.trans_ids)} 条（软删，可在回收站找回）")
    else:
        die(f"删除失败：{res}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
