"""命令行工具。

安装后可直接用::

    tingwu whoami
    tingwu ls                       # 进行中的任务
    tingwu ls --status history
    tingwu dirs
    tingwu get <transId>            # 打印全文
    tingwu srt <transId> -o out.srt
    tingwu md  <transId> -o out.md
    tingwu search 关键词
    tingwu ticket --from-cdp        # 从浏览器导出 ticket 并缓存

也支持 ``python -m tingwu ...``。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

from ._encoding import enable_utf8_output
from .auth import DEFAULT_TICKET_FILE, Ticket, extract_ticket_from_cdp
from .client import TingwuClient
from .exceptions import TingwuError


def _build_client(args: argparse.Namespace) -> TingwuClient:
    """按优先级取 ticket：命令行 > 环境变量 > 缓存文件。"""
    if getattr(args, "ticket", None):
        return TingwuClient.from_cookie(args.ticket)
    env = os.environ.get("TINGWU_TICKET")
    if env:
        return TingwuClient.from_cookie(env)
    tk = Ticket.load(getattr(args, "ticket_file", None) or DEFAULT_TICKET_FILE)
    if tk:
        return TingwuClient(ticket=tk)
    print(
        "未找到 ticket。请任选一种：\n"
        "  1) export TINGWU_TICKET='login_aliyunid_ticket=...'\n"
        "  2) tingwu ticket --from-cdp\n"
        f"  3) tingwu ticket --cookie 'login_aliyunid_ticket=...'  (会缓存到 {DEFAULT_TICKET_FILE})",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _fmt_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "-"
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _fmt_size(n: Optional[int]) -> str:
    if not n:
        return "-"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _status_name(code: Any) -> str:
    from .resources.trans import STATUS_NAMES

    try:
        return STATUS_NAMES.get(int(code), f"status{code}")
    except (TypeError, ValueError):
        return str(code)


# --------------------------------------------------------------------------
# 子命令
# --------------------------------------------------------------------------


def cmd_check(args: argparse.Namespace) -> int:
    """探测登录态是否真实有效（问服务端，不看时钟）。"""
    c = _build_client(args)
    ok = c.check()
    if ok:
        me = c.account.info()
        print(f"登录态有效  userId={me.get('userId')}  accountId={me.get('accountId')}")
        tk = c.ticket
        if tk is not None:
            age = tk.age
            if age is not None:
                print(f"ticket 年龄  {age / 3600:.1f} 小时（签发时刻已知）")
            else:
                print(f"ticket 年龄  未知（来源 {tk.source}，无法得知签发时刻）")
        return 0
    print("登录态无效，请更新 ticket", file=sys.stderr)
    return 1


def cmd_whoami(args: argparse.Namespace) -> int:
    c = _build_client(args)
    info = c.whoami()
    tw = info.get("tingwu") or {}
    al = info.get("aliyun") or {}
    print(f"听悟 userId     : {tw.get('userId')}")
    print(f"听悟 accountId  : {tw.get('accountId')}")
    print(f"encodedUsername : {tw.get('encodedUsername')}")
    if al:
        print(f"阿里云 userId   : {al.get('aliyunUserId')}")
        print(f"昵称            : {al.get('aliyunUserName')}")
        print(f"手机            : {al.get('phone')}")
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    c = _build_client(args)
    status = {
        "processing": [0],
        "history": [1, 2, 3, 4, 11],
        "all": [0, 1, 2, 3, 4, 11],
    }[args.status]
    items = c.trans.list(dir_id=args.dir_id, status=status, page_size=args.limit)
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    if not items:
        print("(无记录)")
        return 0
    print(f"{'transId':<20} {'状态':<10} {'时长':>9}  {'字数':>7}  名称")
    print("-" * 78)
    for it in items:
        tag = it.get("tag") or {}
        print(
            f"{it.get('transId', ''):<20} "
            f"{_status_name(it.get('status')):<10} "
            f"{_fmt_duration(it.get('duration')):>9}  "
            f"{str(it.get('wordCount') or '-'):>7}  "
            f"{tag.get('showName', '')}"
        )
    return 0


def cmd_dirs(args: argparse.Namespace) -> int:
    c = _build_client(args)
    flat = c.directory.flatten()
    if args.json:
        print(json.dumps(flat, ensure_ascii=False, indent=2))
        return 0
    for d in flat:
        print(f"{d['dirId']:<10} {d['path']}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    c = _build_client(args)
    tr = c.trans.result(args.trans_id)
    print(f"# {tr.show_name or tr.trans_id}")
    print(f"时长 {_fmt_duration(tr.duration)} | 句数 {len(tr)} | 说话人 {tr.speakers}")
    print()
    if args.speaker:
        print(tr.to_text(with_speaker=True))
    else:
        print(tr.text)
    return 0


def _export(args: argparse.Namespace, kind: str) -> int:
    c = _build_client(args)
    tr = c.trans.result(args.trans_id)
    if kind == "srt":
        out = tr.to_srt(with_speaker=args.speaker)
    elif kind == "vtt":
        out = tr.to_vtt(with_speaker=args.speaker)
    elif kind == "md":
        out = tr.to_markdown()
    else:
        out = tr.to_text(with_timestamps=args.speaker, with_speaker=args.speaker)

    if args.output:
        import pathlib

        out_path = pathlib.Path(args.output)
        if out_path.parent and not out_path.parent.exists():
            out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(out, encoding="utf-8")
        print(f"已写入 {out_path}（{len(out)} 字符）")
    else:
        print(out)
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    c = _build_client(args)
    items = list(
        c.trans.iter_all(
            status=[0, 1, 2, 3, 4, 11], show_name=args.keyword, max_items=args.limit
        )
    )
    if args.json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return 0
    for it in items:
        tag = it.get("tag") or {}
        print(f"{it.get('transId'):<20} {tag.get('showName', '')}")
    if not items:
        print("(无匹配)")
    return 0


def cmd_quota(args: argparse.Namespace) -> int:
    c = _build_client(args)
    eq = c.subscription.gain_daily()
    print(f"连续签到 : {eq.get('count')} 天")
    print(f"今日已领 : {eq.get('isAlreadyGain')}")
    print(f"时长上限 : {eq.get('maxTimeFlow', 0) / 3600:.0f} 小时")
    print(f"timeFlow : {eq.get('timeFlow')} 秒（语义未证实，详见文档）")
    return 0


def cmd_invite(args: argparse.Namespace) -> int:
    c = _build_client(args)
    info = c.share.invite_info()
    print(f"邀请码   : {info.get('inviteCode')}")
    print(f"微信二维码: {info.get('inviteWeChatQRCodeLink')}")
    return 0


def cmd_ticket(args: argparse.Namespace) -> int:
    """导出/缓存 ticket。"""
    if args.from_cdp:
        tk = extract_ticket_from_cdp(args.cdp_filter, cdp_http=args.cdp)
    elif args.cookie:
        tk = Ticket(value="", source="manual")
        c = TingwuClient.from_cookie(args.cookie)
        assert c.ticket is not None
        tk = c.ticket
    elif args.value:
        tk = Ticket(value=args.value, source="manual")
    else:
        print("请指定 --from-cdp / --cookie / --value 之一", file=sys.stderr)
        return 2

    if args.stdout:
        print(tk.value)
        return 0

    p = tk.save(args.output)
    print(f"已缓存到 {p}")
    print(f"来源 {tk.source} | 长度 {len(tk.value)}")
    return 0


def cmd_raw(args: argparse.Namespace) -> int:
    """直接调任意 action（逃生舱，便于探索未封装接口）。"""
    c = _build_client(args)
    params: dict[str, Any] = {}
    if args.params:
        params = json.loads(args.params)
    if args.path:
        res = c.call_path(args.path, method=args.method, body=params, raw=True)
    else:
        res = c.request(args.action, params=params, method=args.method, raw=True)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


def cmd_collect(args: argparse.Namespace) -> int:
    """列出收藏（侧边栏「我的收藏」）。"""
    c = _build_client(args)
    res = c.collect.list(keyword=args.keyword, page=args.page,
                         page_size=args.limit, raw=True)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    items = res.get("data") or []
    print(f"共 {res.get('total', len(items))} 条收藏")
    for it in items:
        tag = it.get("tag") or {}
        print(f"  {it.get('transId')}  {tag.get('showName', '(无标题)')}")
    return 0


def cmd_trash(args: argparse.Namespace) -> int:
    """列出回收站（侧边栏「回收站」）。"""
    c = _build_client(args)
    res = c.trash.list(page=args.page, page_size=args.limit, raw=True)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    items = res.get("data") or []
    print(f"共 {res.get('total', len(items))} 条")
    for it in items:
        tag = it.get("tag") or {}
        print(f"  {it.get('transId')}  {tag.get('showName', '(无标题)')}")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    """发现页（侧边栏「发现」）：分类 / 推荐 / 分类下的播客。"""
    c = _build_client(args)
    if args.what == "categories":
        res = c.discover.categories()
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        for x in res:
            print(f"  {x.get('rssCategoryId'):>3}  {x.get('name')}")
        return 0
    if args.what == "rss":
        res = c.discover.category_rss(args.category_id, page_size=args.limit)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        for x in res:
            print(f"  {x.get('rssId')}  {x.get('title')}  {x.get('xmlLink', '')}")
        return 0
    # content
    res = c.discover.public_content(need_num=args.limit, raw=True)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    items = res.get("data") or []
    print(f"推荐 {len(items)} 条")
    for it in items:
        info = (it.get("rssItemInfo") or {}).get("rssDTO") or {}
        title = (it.get("rssItemInfo") or {}).get("title") or ""
        print(f"  {it.get('contentId')}  [{info.get('title', '')}] {title}")
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    """上传本地音视频到指定文件夹，可选等转写完成后直接导出。

    这是「上传 → 指定位置 → 下载文档/SRT」的完整流程：
    不带 ``--wait`` 时只上传并打印 transId；带 ``--wait`` 时等转写完，
    再按 ``--format`` 导出到 ``--out-dir``。
    """
    import pathlib

    c = _build_client(args)
    path = pathlib.Path(args.path)
    if not path.is_file():
        print(f"文件不存在: {path}", file=sys.stderr)
        return 2

    res = c.trans.upload_file(
        str(path),
        title=args.title or "",
        dir=args.dir if args.dir is not None else args.dir_id,
        lang=args.lang,
    )
    trans_id = res.get("transId")
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"已上传  : {path.name}（{_fmt_size(path.stat().st_size)}）")
        print(f"文件夹  : {res.get('dirName')} (dirId={res.get('dirId')})")
        print(f"媒体类型: {res.get('contentType')}"
              f"{'（视频）' if res.get('isVideo') else '（音频）'}")
        print(f"transId : {trans_id}")

    if not args.wait:
        if not args.json:
            print("\n转写在后台进行，可用  tingwu get <transId>  取结果，"
                  "或下次加 --wait 直接等到完成。")
        return 0

    st = c.trans.wait(trans_id, timeout=args.timeout, interval=args.interval, quiet=args.json)
    code = st.get("status")
    if args.json:
        print(json.dumps({"status": code, "transId": trans_id}, ensure_ascii=False))
    if code != 1:
        print(f"转写未完成（status={code}），跳过导出。", file=sys.stderr)
        return 1
    if not args.json:
        print(f"转写完成: {_status_name(code)}")

    files = c.export.save(
        trans_id,
        args.out_dir,
        doc_type=_DOC_TYPES[args.doc],
        file_type=_FILE_TYPES[args.format],
        timeout=args.timeout,
    )
    for f in files:
        print(f"已导出: {f}" if not args.json else f)
    if not files:
        print("导出失败：服务端未返回文件。", file=sys.stderr)
        return 1
    return 0


#: 导出内容类型：CLI 名字 -> docType
_DOC_TYPES = {"original": 1, "note": 3, "ppt": 5, "scan": 7}
#: 导出文件格式：CLI 名字 -> fileType
_FILE_TYPES = {"docx": 0, "pdf": 1, "srt": 2, "md": 3}


def cmd_export(args: argparse.Namespace) -> int:
    """导出已有记录为文档 / SRT（走官方导出服务）。"""
    c = _build_client(args)
    fmt = args.format or ("srt" if args.srt else "md")
    files = c.export.save(
        args.trans_id,
        args.out_dir,
        doc_type=_DOC_TYPES[args.doc],
        file_type=_FILE_TYPES[fmt],
        with_speaker=not args.no_speaker,
        with_timestamp=not args.no_timestamp,
        timeout=args.timeout,
    )
    if args.json:
        print(json.dumps(files, ensure_ascii=False, indent=2))
        return 0
    for f in files:
        print(f"已导出: {f}")
    if not files:
        print("导出失败：服务端未返回文件"
              "（笔记/PPT/导读只支持 pdf，原文支持 docx/pdf/srt/md）。", file=sys.stderr)
        return 1
    return 0


def cmd_netsource(args: argparse.Namespace) -> int:
    """播客链接转写（首页「播客链接转写」）。"""
    c = _build_client(args)
    res = c.trans.transcribe_net_source(
        args.url, dir_id=args.dir_id, lang=args.lang, limit=args.limit
    )
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0
    print("已提交播客链接转写")
    return 0


def cmd_meeting(args: argparse.Namespace) -> int:
    """实时记录：建会话 / 配置 / 停止 / 标签翻译。"""
    c = _build_client(args)
    m = c.meeting

    if args.action == "create":
        res = m.create(args.name or "", dir_id=args.dir_id, lang=args.lang)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return 0
        print(f"meetingId     : {res.get('meetingId')}")
        print(f"transId       : {res.get('transId')}")
        print(f"meetingJoinUrl: {res.get('meetingJoinUrl')}")
        print("")
        print("推流地址是 WebSocket，SDK 不负责音频推流；")
        print("转写完成后可用  tingwu get <transId>  取结果。")
        return 0

    if args.action == "status":
        ok = m.protocol_accepted()
        if args.json:
            print(json.dumps({"protocolAccepted": ok}, ensure_ascii=False))
        else:
            print(f"已同意大模型协议: {ok}")
        return 0

    if args.action == "config":
        res = c.request(
            "configMeeting",
            params={
                "meetingId": int(args.meeting_id),
                "translateResultEnabled": args.translate,
                "tag": {"lang": args.lang},
            },
            raw=True,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
              else f"config: code={res.get('code')} success={res.get('success')}")
        return 0

    if args.action == "stop":
        res = c.request(
            "stopMeeting",
            params={
                "meetingId": int(args.meeting_id),
                "tag": {"roleSplitNum": args.role_split},
            },
            raw=True,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
              else f"stop: code={res.get('code')} success={res.get('success')}")
        return 0

    if args.action == "rename":
        res = c.request(
            "syncTransTag",
            params={"transId": args.trans_id, "tag": {"showName": args.name}},
            raw=True,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
              else f"rename: code={res.get('code')} success={res.get('success')}")
        return 0

    if args.action == "tag":
        tag: dict = {}
        if args.lang:
            tag["lang"] = args.lang
        if args.origin_lang is not None:
            tag["originLanguageValue"] = args.origin_lang
        if args.translate_switch is not None:
            tag["translateSwitch"] = args.translate_switch
            tag["transTargetValue"] = args.translate_switch
        if not tag:
            print("请至少指定 --lang / --origin-lang / --translate-switch 之一", file=sys.stderr)
            return 2
        res = c.request("syncTransTag", params={"transId": args.trans_id, "tag": tag}, raw=True)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
              else f"syncTransTag: code={res.get('code')} success={res.get('success')}")
        return 0

    print(f"未知 action: {args.action}", file=sys.stderr)
    return 2


def cmd_doc(args: argparse.Namespace) -> int:
    """正文：读取 / 写入实时记录与记录详情的正文编辑器内容。"""
    c = _build_client(args)
    m = c.meeting
    if args.action == "get":
        res = c.request("getTransDocEdit",
                        params={"userId": "", "transId": args.trans_id}, raw=True)
        content = (res.get("data") or {}).get("content")
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(content or "")
        return 0
    # set
    text = args.text
    if text is None:
        text = sys.stdin.read()
    res = c.request(
        "saveTransDocEdit",
        params={
            "userId": "",
            "transId": args.trans_id,
            "content": m.build_doc_content(text),
            "tag": {"docEditFormat": "dingDoc", "hasNote": bool(text.strip())},
        },
        raw=True,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2) if args.json
          else f"saveTransDocEdit: code={res.get('code')} success={res.get('success')}")
    return 0



# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tingwu", description="通义听悟命令行工具（非官方）"
    )
    p.add_argument("--ticket", help="cookie 串或 ticket 值（覆盖环境变量）")
    p.add_argument("--ticket-file", help=f"ticket 缓存路径（默认 {DEFAULT_TICKET_FILE}）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("check", help="探测登录态是否有效（退出码 0/1）")
    sp.set_defaults(func=cmd_check)

    sp = sub.add_parser("whoami", help="显示当前登录账号")
    sp.set_defaults(func=cmd_whoami)

    sp = sub.add_parser("ls", help="列出转写记录")
    sp.add_argument("--status", choices=["processing", "history", "all"], default="processing")
    sp.add_argument("--dir-id", type=int, default=None, help="限定文件夹")
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_ls)

    sp = sub.add_parser("dirs", help="列出文件夹")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_dirs)

    sp = sub.add_parser("get", help="打印某条转写全文")
    sp.add_argument("trans_id")
    sp.add_argument("--speaker", action="store_true", help="显示说话人")
    sp.set_defaults(func=cmd_get)

    for kind, name in (("srt", "srt"), ("vtt", "vtt"), ("md", "md"), ("txt", "txt")):
        sp = sub.add_parser(name, help=f"导出 {kind.upper()} 字幕/文本")
        sp.add_argument("trans_id")
        sp.add_argument("-o", "--output", help="输出文件（默认打印）")
        sp.add_argument("--speaker", action="store_true", help="含说话人标记")
        sp.set_defaults(func=lambda a, k=kind: _export(a, k))

    sp = sub.add_parser("search", help="按名称搜索转写")
    sp.add_argument("keyword")
    sp.add_argument("--limit", type=int, default=50)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("quota", help="签到并显示权益")
    sp.set_defaults(func=cmd_quota)

    sp = sub.add_parser("invite", help="邀请码与二维码")
    sp.set_defaults(func=cmd_invite)

    sp = sub.add_parser("ticket", help="导出/缓存 ticket")
    sp.add_argument("--from-cdp", action="store_true", help="从运行中的浏览器读取")
    sp.add_argument("--cdp", default="http://127.0.0.1:9222")
    sp.add_argument("--cdp-filter", default="aliyun.com")
    sp.add_argument("--cookie", help="从 cookie 串解析")
    sp.add_argument("--value", help="直接给 ticket 值")
    sp.add_argument("-o", "--output", help="缓存路径")
    sp.add_argument("--stdout", action="store_true", help="只打印值")
    sp.set_defaults(func=cmd_ticket)

    sp = sub.add_parser("collect", help="列出收藏（我的收藏）")
    sp.add_argument("--keyword", default="")
    sp.add_argument("--page", type=int, default=1)
    sp.add_argument("--limit", type=int, default=12)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_collect)

    sp = sub.add_parser("trash", help="列出回收站")
    sp.add_argument("--page", type=int, default=1)
    sp.add_argument("--limit", type=int, default=12)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_trash)

    sp = sub.add_parser("discover", help="发现页：分类/播客/推荐")
    sp.add_argument("what", choices=["categories", "rss", "content"], nargs="?",
                    default="content")
    sp.add_argument("--category-id", type=int, default=4, help="rss 分类 ID（默认 4=科技）")
    sp.add_argument("--limit", type=int, default=12)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser(
        "upload", help="上传音视频到默认/指定文件夹，可等转写完后直接导出"
    )
    sp.add_argument("path")
    sp.add_argument("--title", default="", help="记录名（默认用文件名）")
    sp.add_argument("--dir", help="目标文件夹名或 dirId（默认 0=默认文件夹）")
    sp.add_argument("--dir-id", type=int, default=0, help="同 --dir，只接受 ID（保留兼容）")
    sp.add_argument("--lang", default="cn")
    sp.add_argument("--wait", action="store_true", help="等转写完成后再执行导出")
    sp.add_argument(
        "--format", choices=sorted(_FILE_TYPES), default="md",
        help="--wait 时的导出格式（默认 md）",
    )
    sp.add_argument(
        "--doc", choices=sorted(_DOC_TYPES), default="original",
        help="导出内容：original 原文 / note 笔记 / ppt / scan 导读（默认原文）",
    )
    sp.add_argument("--out-dir", default=".", help="导出目录（默认当前目录）")
    sp.add_argument("--timeout", type=float, default=3600.0, help="等待/导出超时秒数")
    sp.add_argument("--interval", type=float, default=10.0, help="轮询间隔秒数")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_upload)

    sp = sub.add_parser("export", help="导出记录为文档 / SRT（官方导出服务）")
    sp.add_argument("trans_id")
    sp.add_argument(
        "--format", choices=sorted(_FILE_TYPES),
        help="文件格式（默认 md；--srt 等价于 --format srt）",
    )
    sp.add_argument("--srt", action="store_true", help="等价于 --format srt")
    sp.add_argument(
        "--doc", choices=sorted(_DOC_TYPES), default="original",
        help="导出内容：original 原文 / note 笔记 / ppt / scan 导读（默认原文）",
    )
    sp.add_argument("--out-dir", default=".", help="导出目录（默认当前目录）")
    sp.add_argument("--timeout", type=float, default=300.0, help="导出超时秒数")
    sp.add_argument("--no-speaker", action="store_true", help="不带说话人")
    sp.add_argument("--no-timestamp", action="store_true", help="不带时间戳")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("netsource", help="播客链接转写")
    sp.add_argument("url")
    sp.add_argument("--dir-id", type=int, default=0)
    sp.add_argument("--lang", default="cn")
    sp.add_argument("--limit", type=int, default=1, help="取解析结果前 N 集")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_netsource)

    sp = sub.add_parser("meeting", help="实时记录（开启实时记录）")
    sp.add_argument(
        "action",
        choices=["create", "status", "config", "stop", "rename", "tag"],
        nargs="?", default="status",
    )
    sp.add_argument("--name", default="", help="记录名（create / rename 时用）")
    sp.add_argument("--dir-id", type=int, default=0)
    sp.add_argument("--lang", default="cn", help="音频语言：cn / en（tag 时写入 tag.lang）")
    sp.add_argument("--meeting-id", help="config / stop 用的 meetingId")
    sp.add_argument("--trans-id", help="rename / tag 用的 transId")
    sp.add_argument(
        "--role-split", type=int, default=-1,
        help="结束录音的发言人数：-1 暂不体验 / 1 单人演讲 / 2 2人对话 / 3 多人讨论",
    )
    sp.add_argument("--translate", action="store_true", help="config：开启翻译结果")
    sp.add_argument("--origin-lang", type=int, help="tag：其他语言的语种编号")
    sp.add_argument("--translate-switch", type=int, help="tag：翻译开关 0/1")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_meeting)

    sp = sub.add_parser("doc", help="正文编辑器内容（读取 / 写入）")
    sp.add_argument("action", choices=["get", "set"], nargs="?", default="get")
    sp.add_argument("--trans-id", required=True)
    sp.add_argument("--text", help="set 时的正文文本，不给则从 stdin 读")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_doc)

    sp = sub.add_parser("raw", help="调任意 action（探索用）")
    sp.add_argument("action", nargs="?", help="action 名，如 getTransList")
    sp.add_argument("--path", help="直接指定 /api 之后路径")
    sp.add_argument("--params", help="JSON 参数")
    sp.add_argument("--method", default="POST")
    sp.set_defaults(func=cmd_raw)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    enable_utf8_output()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except TingwuError as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
