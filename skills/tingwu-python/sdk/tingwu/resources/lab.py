"""AI 实验室（智能速览 / 问答 / 脑图）接口。

听悟把这些能力统称 "lab"，结果按类型区分：
``labSummaryInfo``（速览）、``labPptInfo``（PPT）、``labQaInfo``（问答）等。
"""

from __future__ import annotations

from typing import Any, Optional


class LabResource:
    """AI 生成内容：摘要、思维导图、问答、翻译。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def all_info(
        self, trans_id: str, *, content: "Optional[list[str]]" = None
    ) -> dict[str, Any]:
        """取某转写的全部 AI 结果（关键词、摘要、脑图、待办等）。

        Args:
            trans_id: 转写记录 ID。
            content: 要取的卡片类型列表。默认 ``["labInfo"]``（速览）。

        Note:
            **必须带 ``content``**，否则服务端返回 ``CMN.ServerError``。
            实测 ``["labRecommendQuestionsInfo"]`` 取「猜你想问」。
        """
        return self._c.request(
            "getAllLabInfo",
            params={
                "transId": trans_id,
                "content": content if content is not None else ["labInfo"],
            },
        )

    def key_status(self, trans_id: str) -> Any:
        """查询 AI 结果生成进度。"""
        return self._c.request("getLabKeyStatus", params={"transId": trans_id})

    def add(self, trans_id: str, lab_type: str, **params: Any) -> Any:
        """触发生成某类 AI 结果。

        Args:
            lab_type: 结果类型，如 ``"labSummaryInfo"`` / ``"labQaInfo"``。
        """
        return self._c.request(
            "addLabResult", params={"transId": trans_id, "labType": lab_type, **params}
        )

    def update(self, trans_id: str, lab_type: str, content: str, **params: Any) -> Any:
        """编辑 AI 结果（智能速览支持编辑）。"""
        return self._c.request(
            "modLabResult",
            params={"transId": trans_id, "labType": lab_type, "content": content, **params},
        )

    def delete(self, trans_id: str, lab_type: str, **params: Any) -> Any:
        """删除 AI 结果。"""
        return self._c.request(
            "delLabResult", params={"transId": trans_id, "labType": lab_type, **params}
        )

    # ---- AI 搜索式问答 ----

    def ask(self, trans_id: str, question: str, **params: Any) -> dict[str, Any]:
        """对转写内容提问。

        Returns:
            含搜索任务的标识，通常需配合 :meth:`ask_status` 轮询。
        """
        return self._c.request(
            "getAiSearchUrl", params={"transId": trans_id, "question": question, **params}
        )

    def ask_status(self, **params: Any) -> Any:
        """查询问答进度。"""
        return self._c.request("getAiSearchStatus", params=params)

    def ask_result(self, **params: Any) -> Any:
        """取问答结果。"""
        return self._c.request("getAiQuestionData", params=params)

    def ask_history(self, trans_id: str, **params: Any) -> Any:
        """问答历史。"""
        return self._c.request("getAiHistorySearch", params={"transId": trans_id, **params})

    def clear_history(self, trans_id: str) -> Any:
        """清空问答历史。"""
        return self._c.request("clearAiSearchHistory", params={"transId": trans_id})

    def recommend_questions(self, trans_id: str) -> Any:
        """「猜你想问」推荐问题列表。

        Note:
            前端并不是调独立 action ``labRecommendQuestionsInfo``
            （该 action 实测返回 ``code=-1``），而是调 ``getAllLabInfo``
            并传 ``content=["labRecommendQuestionsInfo"]``。
        """
        return self.all_info(trans_id, content=["labRecommendQuestionsInfo"])

    # ---- 反馈 ----

    def feedback(self, **params: Any) -> Any:
        """对 AI 结果点赞/点踩。"""
        return self._c.request("addLabFeedback", params=params)
