"""实时记录 / 实时会议（首页「开启实时记录」按钮 / 实时记录页 ``/doc/record``）。

点击「开启实时记录」并真正录音后，前端的实际调用链是::

    getAccountStatus(statusKey=BigModelUserProtocol)   # 先确认已同意大模型协议
        └─ statusValue == 1 才继续
    createMeeting(meetingType=101, dirId, tag{showName, fileType:"meeting", ...})
        └─ 返回 meetingId + meetingJoinUrl（WebSocket 推流地址） + transId
    configMeeting(meetingId, translateResultEnabled, tag{lang})   # 语言/翻译设置
    stopMeeting(meetingId, tag{roleSplitNum})                     # 结束录音

``roleSplitNum`` 来自结束录音弹窗的「选择发言人数」，取值见
:data:`ROLE_SPLIT_NONE` / :data:`ROLE_SPLIT_SINGLE` /
:data:`ROLE_SPLIT_DIALOG` / :data:`ROLE_SPLIT_MULTI`。

结束录音后页面跳到 ``/doc/transcripts/<transId>``，随后用
``/doc/getTransDocEdit?transId=`` 拉取正文（record 页「正文」编辑器内容）。

本模块封装这几步的 HTTP 部分。**音频推流本身不在范围内**：
``meetingJoinUrl`` 是 WebSocket 地址，需要实现实时音频协议才能真的录音，
SDK 只负责建会话、拿地址、改配置、停止。

Example:
    >>> m = client.meeting.create("我的会议")
    >>> print(m["meetingId"], m["meetingJoinUrl"])
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

#: 前端固定使用的会议类型
MEETING_TYPE = "101"

#: 结束录音弹窗「暂不体验」——不做发言人区分
ROLE_SPLIT_NONE = -1
#: 结束录音弹窗「单人演讲」
ROLE_SPLIT_SINGLE = 1
#: 结束录音弹窗「2人对话」
ROLE_SPLIT_DIALOG = 2
#: 结束录音弹窗「多人讨论」
ROLE_SPLIT_MULTI = 3

#: 音频语言（「音频语言」三个按钮写入 ``tag.lang``）
LANG_CN = "cn"
LANG_EN = "en"
#: 选择「其他语言」后，下拉里选的具体语种
#: 写成 :data:`ORIGIN_LANG_VALUES` 里的数字，落进 ``tag.originLanguageValue``
ORIGIN_LANG_CN = 1
ORIGIN_LANG_EN = 2

class MeetingResource:
    """实时会议：创建、配置、查询、停止。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    # ------------------------------------------------------------------
    # 前置检查
    # ------------------------------------------------------------------

    def protocol_accepted(self) -> bool:
        """是否已同意大模型用户协议。

        未同意时 ``createMeeting`` 会被前端拦住，所以创建前先查这个。
        """
        try:
            res = self._c.request(
                "getAccountStatus", params={"statusKey": "BigModelUserProtocol"}
            )
        except Exception:
            return False
        return bool(res.get("statusValue")) if isinstance(res, dict) else False

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------

    def create(
        self,
        show_name: str = "",
        *,
        dir_id: int = 0,
        lang: str = "cn",
        meeting_type: str = MEETING_TYPE,
        **tag_extra: Any,
    ) -> dict[str, Any]:
        """创建一场实时记录。

        Args:
            show_name: 记录名称。留空时前端会填 ``"YYYY-MM-DD HH:MM 记录"``，
                这里同样用当前时间生成。
            dir_id: 归属文件夹。
            lang: 语言，如 ``"cn"``。
            meeting_type: 会议类型，前端固定 ``"101"``。

        Returns:
            含 ``meetingId``、``meetingJoinUrl``（WebSocket 推流地址）、
            ``transId`` 等。

        Note:
            返回的 ``transId`` 可直接喂给
            :meth:`~tingwu.resources.trans.TransResource.result` 取转写结果。

            本方法会**真的创建一场会议**，不要放进自动化测试或循环里。
        """
        if not show_name:
            show_name = f"{datetime.now():%Y-%m-%d %H:%M} 记录"
        tag = {
            "showName": show_name,
            "fileType": "meeting",
            "lang": lang,
            "meetingPgPartial": "1",
            "nFix": "1",
            "client": "web",
        }
        tag.update(tag_extra)
        return self._c.request(
            "createMeeting",
            params={
                "meetingType": meeting_type,
                "dirId": dir_id,
                "tag": tag,
            },
        )

    def info(self, trans_id: str) -> Any:
        """实时会议详情（含 ``liveStatus`` / ``showName`` / 语言配置）。

        Args:
            trans_id: :meth:`create` 返回的 ``transId``。

        Note:
            实测**必须传 ``transId``**；传 ``meetingId`` 会返回
            ``TRS.ParamError``。
        """
        return self._c.request("getLiveMeetingInfo", params={"transId": trans_id})

    def live_info(self, live_id: str) -> Any:
        """实时转写中间态（未结束时的部分结果）。

        Args:
            live_id: 实时会话 ID（``/meeting/live/request``，与 meeting 模块不同路径）。
        """
        return self._c.request("getLiveInfo", params={"liveId": live_id})

    def config(
        self,
        meeting_id: str,
        *,
        lang: str = "cn",
        translate_target_lang: str = "",
        translate_result_enabled: bool = False,
        **params: Any,
    ) -> Any:
        """修改会议配置（语言、是否开启翻译）。"""
        return self._c.request(
            "configMeeting",
            params={
                "meetingId": meeting_id,
                "translateResultEnabled": translate_result_enabled,
                "translateTargetLang": translate_target_lang,
                "tag": {"lang": lang},
                **params,
            },
        )

    def bind(self, **params: Any) -> Any:
        """绑定实时会议到某条记录。参数随场景变化，透传。"""
        return self._c.request("bindLiveMeeting", params=params)

    def start(self, meeting_id: str, *, live_id: str = "", meeting_join_url: str = "") -> Any:
        """开始实时记录（推流）。

        Args:
            meeting_id: :meth:`create` 返回的 ``meetingId``。
            live_id: 实时会话 ID，部分场景需要。
            meeting_join_url: :meth:`create` 返回的 WebSocket 推流地址。

        Note:
            UI 上的「开始录音」按钮实际是 :meth:`create` 建会话后，
            通过 ``meetingJoinUrl`` 走 WebSocket 推流；本方法只覆盖
            其 HTTP 侧的 ``startLiveMeeting`` 调用。
        """
        params: dict[str, Any] = {
            "meetingType": MEETING_TYPE,
            "meetingId": meeting_id,
        }
        if live_id:
            params["liveId"] = live_id
        if meeting_join_url:
            params["meetingJoinUrl"] = meeting_join_url
        return self._c.request("startLiveMeeting", params=params)

    def stop(
        self,
        meeting_id: str,
        *,
        role_split_num: int = ROLE_SPLIT_NONE,
        live_id: str = "",
        **params: Any,
    ) -> Any:
        """结束实时记录。

        Args:
            meeting_id: :meth:`create` 返回的 ``meetingId``。
            role_split_num: 发言人数，对应结束录音弹窗里的选项。
                默认 :data:`ROLE_SPLIT_NONE`（「暂不体验」，不做发言人区分）。
            live_id: 实时会话 ID，部分场景需要。

        Note:
            前端在结束录音弹窗里选了发言人数后，把该值放进
            ``tag.roleSplitNum`` 一并提交；选「暂不体验」时传 ``-1``。
            结束后记录进入转写，页面跳到 ``/doc/transcripts/<transId>``。
        """
        body: dict[str, Any] = {
            "meetingId": meeting_id,
            "tag": {"roleSplitNum": role_split_num},
        }
        if live_id:
            body["liveId"] = live_id
        body.update(params)
        return self._c.request("stopMeeting", params=body)

    def clear(self, **params: Any) -> Any:
        """清理实时记录的分段缓存。参数随场景变化，透传。"""
        return self._c.request("clearLiveMeetingPg", params=params)

    # ------------------------------------------------------------------
    # 标签 / 翻译
    # ------------------------------------------------------------------

    def sync_tag(self, trans_id: str, tag: "dict[str, Any]") -> Any:
        """更新实时记录的转写标签（如开关翻译）。

        Args:
            trans_id: :meth:`create` 返回的 ``transId``。
            tag: 要合并的标签字段，如 ``{"translateSwitch": 0,
                "originLanguageValue": 1}``。

        Note:
            前端在建会话后**连续调用两次**：先带
            ``{translateSwitch, originLanguageValue}``，再补
            ``transTargetValue``。这里不模拟该行为，调用方按需传全。

            record 页的「音频语言」「翻译」按钮也都走这里：
            选「中文」/「英语」写入 ``tag.lang``，选「其他语言」后
            再在下拉里写入 ``tag.originLanguageValue``；「保存」按钮
            则通过本方法提交 ``tag.showName`` 改标题。
        """
        return self._c.request("syncTransTag", params={"transId": trans_id, "tag": tag})

    def set_translate(
        self, trans_id: str, *, enabled: bool, target_value: int = 0
    ) -> Any:
        """开关实时翻译。"""
        return self.sync_tag(
            trans_id,
            {
                "translateSwitch": 1 if enabled else 0,
                "originLanguageValue": 1,
                "transTargetValue": target_value,
            },
        )

    def meeting_translate(self, **params: Any) -> Any:
        """会议翻译配置。参数透传。"""
        return self._c.request("meetingTranslate", params=params)

    def realtime_translate(self, **params: Any) -> Any:
        """实时翻译。参数透传。"""
        return self._c.request("realtimeTranslate", params=params)

    def transient_translate(
        self,
        meeting_id: str,
        *,
        source_language: str,
        target_language: str,
        text_list: "list[str]",
    ) -> Any:
        """临时翻译一段文本（不落库）。"""
        return self._c.request(
            "transientTranslate",
            params={
                "meetingId": meeting_id,
                "sourceLanguage": source_language,
                "targetLanguage": target_language,
                "textList": text_list,
            },
        )

    def save_doc_result(self, **params: Any) -> Any:
        """保存实时会议生成的文档结果。参数透传。"""
        return self._c.request("saveMeetingDocResult", params=params)

    # ------------------------------------------------------------------
    # 正文（实时记录 / 记录详情共用）
    # ------------------------------------------------------------------

    def doc_edit(self, trans_id: str, **params: Any) -> Any:
        """读取「正文」编辑器内容。

        Args:
            trans_id: 记录 ID（:meth:`create` 返回的 ``transId``）。

        Returns:
            ``data`` 里的 ``content`` 即正文文本，转写未完成时常为空串。

        Note:
            走独立路径 ``POST /api/doc/getTransDocEdit?c=web``，
            不在 ``/api/trans/request`` 上；结束录音后页面跳到
            ``/doc/transcripts/<transId>`` 时就会拉这个接口渲染正文。
        """
        return self._c.request(
            "getTransDocEdit",
            params={"userId": "", "transId": trans_id, **params},
        )

    @staticmethod
    def build_doc_content(text: str) -> str:
        """把纯文本包成「正文」编辑器用的钉钉文档结构。

        Args:
            text: 要写入正文的文本。

        Returns:
            可传给 :meth:`doc_save` 的 ``content`` 字符串。

        Note:
            前端正文走钉钉文档（``docEditFormat="dingDoc"``），
            内容是 JSON 化的节点树；空正文形如
            ``["root",{},["p",{},["span",{"data-type":"text"},
            ["span",{"sz":12,"szUnit":"pt","data-type":"leaf"},""]]]]``。
            写入文字后 ``hasNote`` 会变 ``true``。
        """
        import json

        return json.dumps(
            [
                "root",
                {},
                [
                    "p",
                    {},
                    [
                        "span",
                        {"data-type": "text"},
                        ["span", {"sz": 12, "szUnit": "pt", "data-type": "leaf"}, text],
                    ],
                ],
            ],
            ensure_ascii=False,
        )

    def doc_save(self, trans_id: str, content: str, *, has_note: bool = True, **params: Any) -> Any:
        """保存「正文」编辑器内容。

        Args:
            trans_id: 记录 ID。
            content: 正文内容，可用 :meth:`build_doc_content` 从纯文本生成。
            has_note: 正文非空标记，前端在写完字后传 ``true``。

        Note:
            record 页点「保存」时，若正文有改动会先发这个请求，
            再发一次 :meth:`sync_tag` 提交标题。
        """
        return self._c.request(
            "saveTransDocEdit",
            params={
                "userId": "",
                "transId": trans_id,
                "content": content,
                "tag": {"docEditFormat": "dingDoc", "hasNote": has_note},
                **params,
            },
        )

    def rename(self, trans_id: str, show_name: str, **params: Any) -> Any:
        """重命名实时记录（改标题）。

        Args:
            trans_id: 记录 ID。
            show_name: 新标题。

        Note:
            record 页点「保存」时，标题改动通过
            ``syncTransTag`` 的 ``tag.showName`` 提交。
        """
        return self.sync_tag(trans_id, {"showName": show_name}, **params)
