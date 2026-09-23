"""对真实接口的集成测试。

需要环境变量 ``TINGWU_TICKET``。
运行： ``python tests/test_live.py``
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tingwu import TingwuClient, Transcript  # noqa: E402
from tingwu._encoding import enable_utf8_output  # noqa: E402

enable_utf8_output()  # Windows 控制台默认 gbk，不切会让下面的中文全乱码

PASS, FAIL = [], []


def check(name: str, fn):
    try:
        r = fn()
        PASS.append(name)
        print(f"  [PASS] {name}")
        return r
    except Exception as e:
        FAIL.append((name, e))
        print(f"  [FAIL] {name}: {type(e).__name__}: {e}")
        return None


def main() -> int:
    raw = os.environ.get("TINGWU_TICKET")
    if not raw:
        print("请设置 TINGWU_TICKET")
        return 2

    c = TingwuClient.from_cookie(raw, timeout=60)
    print(f"client: {c}\n")

    print("== account ==")
    acc = check("account.info", c.account.info)
    if acc:
        print(f"     userId={acc.get('userId')} accountId={acc.get('accountId')}")
    aliyun = check("account.aliyun_info", c.account.aliyun_info)
    if aliyun:
        print(f"     aliyunUserId={aliyun.get('aliyunUserId')} name={aliyun.get('aliyunUserName')}")
    check("account.third_info", c.account.third_info)
    check("account.is_login", c.account.is_login)

    print("\n== directory ==")
    tree = check("directory.list", c.directory.list)
    if tree:
        print(f"     roots={len(tree)}")
    flat = check("directory.flatten", c.directory.flatten)
    if flat:
        print(f"     dirs={len(flat)} sample={[d['path'] for d in flat[:3]]}")

    print("\n== trans ==")
    lst = check("trans.list(processing)", lambda: c.trans.list(status=[0]))
    if lst is not None:
        print(f"     processing={len(lst)}")
    hist = check("trans.list(history)", lambda: c.trans.list(status=[1, 2, 3, 4, 11], page_size=5))
    if hist is not None:
        print(f"     history(first 5)={len(hist)}")
    allrec = check("trans.iter_all(max 5)", lambda: list(c.trans.iter_all(status=[0], max_items=5)))
    if allrec is not None:
        print(f"     iterated={len(allrec)}")

    # 取一个真实 transId 测结果解析
    tid = None
    for src in (lst, hist):
        for it in src or []:
            if it.get("transId"):
                tid = it["transId"]
                break
        if tid:
            break

    tr: Transcript | None = None
    if tid:
        print(f"\n== trans.result (transId={tid}) ==")
        tr = check("trans.result", lambda: c.trans.result(tid))
        if tr:
            print(f"     sentences={len(tr)} chars={len(tr.text)}")
            print(f"     duration={tr.duration}s speakers={tr.speakers}")
            print(f"     showName={tr.show_name}")
            print(f"     text head: {tr.text[:60]}...")
        check("trans.result_raw", lambda: c.trans.result_raw(tid))
        check("trans.status", lambda: c.trans.status([tid]))

        if tr and len(tr):
            print("\n== 导出格式 ==")
            srt = check("Transcript.to_srt", tr.to_srt)
            if srt:
                print(f"     srt lines={len(srt.splitlines())}")
                print("     " + "\n     ".join(srt.splitlines()[:4]))
            vtt = check("Transcript.to_vtt", tr.to_vtt)
            if vtt:
                print(f"     vtt starts={vtt.splitlines()[0]!r}")
            check("Transcript.to_text", lambda: tr.to_text(with_timestamps=True)[:80])
            check("Transcript.to_markdown", lambda: tr.to_markdown()[:80])
            check("Transcript.by_speaker", tr.by_speaker)
            check("Transcript.to_srt(speaker)", lambda: tr.to_srt(with_speaker=True)[:80])

    print("\n== share ==")
    inv = check("share.invite_info", c.share.invite_info)
    if inv:
        print(f"     inviteCode={inv.get('inviteCode')}")

    print("\n== notice ==")
    nl = check("notice.list", c.notice.list)
    if nl is not None:
        print(f"     notices={len(nl)}")

    print("\n== subscription ==")
    eq = check("subscription.gain_daily", c.subscription.gain_daily)
    if eq:
        print(
            f"     remaining={eq.get('timeFlow', 0) / 3600:.1f}h "
            f"days={eq.get('count')} already={eq.get('isAlreadyGain')}"
        )
    check("subscription.remaining_hours", c.subscription.remaining_hours)
    check("subscription.promotion_status", c.subscription.promotion_status)

    print("\n== 错误处理 ==")
    from tingwu import APIError, AuthError

    def bad_auth():
        bad = TingwuClient.from_cookie("login_aliyunid_ticket=invalid_value_xxx")
        bad.account.info()
        return "should have raised"

    try:
        bad_auth()
        FAIL.append(("bad ticket raises AuthError", Exception("no raise")))
        print("  [FAIL] bad ticket did not raise")
    except AuthError as e:
        PASS.append("bad ticket raises AuthError")
        print(f"  [PASS] bad ticket -> AuthError: {str(e)[:50]}")

    def unknown_action():
        try:
            c.request("noSuchActionXyz")
        except KeyError as e:
            return str(e)[:60]
        return "no raise"

    r = check("unknown action raises KeyError", unknown_action)
    if r:
        print(f"     {r}")

    print(f"\n{'=' * 56}")
    print(f"PASS={len(PASS)}  FAIL={len(FAIL)}")
    if FAIL:
        for n, e in FAIL:
            print(f"  FAIL {n}: {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
