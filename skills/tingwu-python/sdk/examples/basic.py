"""使用示例。

运行前设置::

    export TINGWU_TICKET='login_aliyunid_ticket=_wkpof_...'
"""

from __future__ import annotations

import os

from tingwu import TingwuClient, Ticket, extract_ticket_from_cdp


def example_basic():
    """最简用法。"""
    c = TingwuClient.from_cookie(os.environ["TINGWU_TICKET"])
    me = c.account.info()
    print(f"登录为 userId={me['userId']}")


def example_list_and_export():
    """列出转写并导出成 SRT。"""
    c = TingwuClient.from_cookie(os.environ["TINGWU_TICKET"])

    for item in c.trans.list(status=[0], page_size=5):
        tag = item.get("tag") or {}
        print(f"{item['transId']}  {tag.get('showName')}")

    # 导出第一条
    items = c.trans.list(status=[0], page_size=1)
    if not items:
        print("没有进行中的任务")
        return
    tid = items[0]["transId"]
    tr = c.trans.result(tid)

    with open(f"{tid}.srt", "w", encoding="utf-8") as f:
        f.write(tr.to_srt(with_speaker=True))
    print(f"已导出 {tid}.srt（{len(tr)} 句，{tr.duration:.0f} 秒）")


def example_speaker_summary():
    """统计每个说话人说了多少。

    注意：要挑一条**已完成**的记录；失败/上传过期的记录没有 ``result``。
    """
    c = TingwuClient.from_cookie(os.environ["TINGWU_TICKET"])

    tr = None
    for item in c.trans.list(status=[0], page_size=5):
        if item.get("wordCount"):
            tr = c.trans.result(item["transId"])
            if len(tr):
                break
    if tr is None or not len(tr):
        print("没找到含结果的记录")
        return

    print(f"\n{tr.show_name}")
    for speaker, sentences in tr.by_speaker().items():
        chars = sum(len(s.text) for s in sentences)
        print(f"  说话人 {speaker}: {len(sentences):>5} 句 / {chars:>7} 字")


def example_search():
    """搜索历史任务。"""
    c = TingwuClient.from_cookie(os.environ["TINGWU_TICKET"])
    for item in c.trans.iter_all(show_name="会议", max_items=20):
        print((item.get("tag") or {}).get("showName"))


def example_refresh_on_expire():
    """ticket 失效时自动刷新。

    注意：写入磁盘时用 0600 权限；不要提交进版本库。
    """

    def refresh() -> Ticket:
        # 实际项目里可以从 CDP、密钥管理服务或环境变量重新取
        return extract_ticket_from_cdp()

    tk = Ticket.load()
    if tk is None:
        print("无缓存 ticket，先运行: tingwu ticket --from-cdp")
        return

    c = TingwuClient(ticket=tk, on_auth_expired=refresh)
    print(c.account.info()["userId"])


def example_raw():
    """调用未封装的接口。"""
    c = TingwuClient.from_cookie(os.environ["TINGWU_TICKET"])

    # 方式一：给 action 名，库自动定位 endpoint
    res = c.request(
        "getTransStatus",
        params={"userId": "", "transIds": ["someTransId"], "preview": 1},
    )
    print(res)

    # 方式二：直接给路径（用于 /trans/getTransResult 这类非标准形式）
    res = c.call_path(
        "/trans/getTransResult",
        body={"action": "getTransResult", "version": "1.0", "transId": "someTransId"},
    )
    print(res.get("duration"))


if __name__ == "__main__":
    example_basic()
    print("-" * 50)
    example_speaker_summary()
