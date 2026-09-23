"""文件夹管理：新建、重命名、删除，以及把记录移动到文件夹。

用法：
    python scripts/dir.py create 项目A                 # 根目录新建
    python scripts/dir.py create 子目录 --parent 319288  # 在某文件夹下新建
    python scripts/dir.py rename 382553 新名字
    python scripts/dir.py delete 382553                # 会二次确认
    python scripts/dir.py delete 382553 --yes
    python scripts/dir.py move TRANS_ID --to 319289    # 记录移到文件夹（0=默认）
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, die, out


def _resolve_dir(c, value: str) -> int:
    """把文件夹名 / 路径 / dirId 统一解析成 dirId。"""
    try:
        return int(value)
    except ValueError:
        pass
    for d in c.directory.flatten():
        if d.get("dirName") == value or d.get("path") == value:
            return int(d["dirId"])
    die(f"找不到文件夹：{value}（用 list_dirs.py 看有哪些）")


def _cmd_create(c, args) -> int:
    parent = -1
    if args.parent:
        parent = _resolve_dir(c, args.parent)
    res = c.directory.create(args.name, parent_dir_id=parent, raw=True)
    if str(res.get("code")) != "0":
        die(f"创建失败：{res.get('code')} {res.get('message')}")
    data = res.get("data") or {}
    focus = data.get("focusDir") or {}
    if args.json:
        out({"dirId": focus.get("dirId"), "dirName": focus.get("dirName")}, as_json=True)
    else:
        print(f"已创建  {focus.get('dirId')}  {focus.get('dirName')}")
    return 0


def _cmd_rename(c, args) -> int:
    dir_id = _resolve_dir(c, args.dir)
    res = c.directory.rename(dir_id, args.new_name, raw=True)
    if str(res.get("code")) != "0":
        die(f"重命名失败：{res.get('code')} {res.get('message')}")
    if args.json:
        out({"dirId": dir_id, "dirName": args.new_name}, as_json=True)
    else:
        print(f"已重命名  {dir_id} -> {args.new_name}")
    return 0


def _cmd_delete(c, args) -> int:
    dir_id = _resolve_dir(c, args.dir)

    # 文件夹下所有记录会同步删除，先如实告知当前状态
    name = None
    for d in c.directory.flatten():
        if int(d["dirId"]) == dir_id:
            name = d.get("path") or d.get("dirName")
    if dir_id != 0:
        try:
            if c.directory.has_processing(dir_id):
                print(f"注意：{name} 下有进行中的转写任务，删除后会转入默认文件夹")
        except Exception:
            pass  # 查状态失败不阻断删除，下面的确认才是关键

    label = f"{dir_id} ({name})" if name else str(dir_id)
    if not args.yes:
        print(f"即将删除文件夹 {label}，其下记录会一并删除。")
        if input("确认？[y/N] ").strip().lower() != "y":
            print("已取消")
            return 0

    res = c.directory.delete(dir_id, raw=True)
    if str(res.get("code")) != "0":
        die(f"删除失败：{res.get('code')} {res.get('message')}")
    print(f"已删除  {label}")
    return 0


def _cmd_move(c, args) -> int:
    dest = _resolve_dir(c, args.to)
    res = c.directory.move_trans(args.trans_ids, dest, raw=True)
    if str(res.get("code")) != "0":
        die(f"移动失败：{res.get('code')} {res.get('message')}")
    if args.json:
        out({"destDirId": dest, "transIds": args.trans_ids}, as_json=True)
    else:
        print(f"已移动 {len(args.trans_ids)} 条记录 -> {dest}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="文件夹管理（新建/重命名/删除/移动记录）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("create", help="新建文件夹")
    p.add_argument("name")
    p.add_argument("--parent", help="父文件夹（名字/路径/dirId），缺省根目录")
    add_common(p)

    p = sub.add_parser("rename", help="重命名文件夹")
    p.add_argument("dir", help="文件夹名/路径/dirId")
    p.add_argument("new_name")
    add_common(p)

    p = sub.add_parser("delete", help="删除文件夹（其下记录一并删除）")
    p.add_argument("dir", help="文件夹名/路径/dirId")
    p.add_argument("--yes", action="store_true", help="跳过确认")
    add_common(p)

    p = sub.add_parser("move", help="把转写记录移动到文件夹")
    p.add_argument("trans_ids", nargs="+", help="记录 ID（可多个）")
    p.add_argument("--to", required=True, help="目标文件夹（名字/路径/dirId，0=默认）")
    add_common(p)

    args = ap.parse_args()
    apply_sdk_arg(args.sdk)
    c = client()

    handlers = {
        "create": _cmd_create,
        "rename": _cmd_rename,
        "delete": _cmd_delete,
        "move": _cmd_move,
    }
    return handlers[args.cmd](c, args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
