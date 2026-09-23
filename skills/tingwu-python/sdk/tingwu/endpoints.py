"""听悟 API 端点映射表。

全部端点从官方前端 bundle
``g.alicdn.com/idst-fe/mind-meeting-assistant2/0.1.32/umi.js``
中提取（``concat(C,"/<module>/request?<action>")`` 形式），并逐一实测确认。

调用约定（已实测验证）::

    POST https://tingwu.aliyun.com/api/<module>/request?<action>&c=web
    Content-Type: application/json
    body: {"action": "<action>", "version": "1.0", ...业务参数}

要点：
* ``?<action>`` 在 query 里，body 里也要有同名 ``action`` 字段，两者必须一致。
* ``&c=web`` 可省略，但保留更贴近真实客户端。
* 鉴权只靠 cookie，无需签名（见 ``auth.py``）。
"""

from __future__ import annotations

# API 版本号（前端常量 k = "1.0"）
DEFAULT_VERSION = "1.0"

#: 各业务模块的 endpoint 基路径（相对 /api）
MODULE_PATHS: dict[str, str] = {
    "account": "/account/request",
    "aliyundrive": "/aliyundrive/request",
    "authorization": "/authorization/request",
    "collect": "/collect/request",
    "commonspeaker": "/commonspeaker/request",
    "content_check": "/contentCheck/request",
    "directory": "/directory/request",
    "doc": "/doc/request",
    "export": "/export/request",
    "feedback": "/feedback/request",
    "helpdoc": "/helpdoc/request",
    "history": "/history/request",
    "hotword": "/hotword/request",
    "lab": "/lab/request",
    "meeting": "/meeting/request",
    "meeting_live": "/meeting/live/request",
    "notice": "/notice/request",
    "notify": "/notify/request",
    "operation_record": "/operationRecord/request",
    "record": "/record/request",
    "rss": "/explore/rss/request",
    "rss_category": "/explore/rss/category/request",
    "content": "/explore/content/request",
    "share": "/share/request",
    "subscribe": "/subscribe/request",
    "tag": "/tag/request",
    "trans": "/trans/request",
    "trans_brk": "/trans/brk/request",
    "translate": "/translate/request",
    "trash": "/trash/request",
    "training": "/training/request",
    "tingwu_account": "/tingwu/account/request",
}

#: action -> 模块。用于 ``client.request("getTransList")`` 这类按 action 直调。
#:
#: 注意：以下 3 个 action 在服务端存在**两套 endpoint**（不同产品线），
#: 这里取听悟主站那一套；需要另一套时用 ``endpoint=`` 显式覆盖。
#:   * ``exportTrans`` / ``getExportStatus``：``/aliyundrive/request``（TIG） 或 ``/export/request``（EPO）
#:   * ``fuzzySearchInBiz``：``/tingwu/account/request``（实测 ``/account/request`` 返回 404）
ACTION_MODULE: dict[str, str] = {
    # ---- account ----
    "fuzzySearchInBiz": "tingwu_account",
    "getAccountStatus": "tingwu_account",
    "updateAccountStatus": "tingwu_account",
    "generateReportPicLink": "tingwu_account",
    "getUserInfo": "tingwu_account",
    # ---- aliyundrive（阿里云盘）----
    # exportTrans / getExportStatus 默认落在云盘这条路径上；
    # 本地下载那套由 c.export 用 endpoint= 显式改到 /export/request。
    "exportTrans": "aliyundrive",
    "getExportStatus": "aliyundrive",
    # ---- collect（收藏）----
    "cancelCollect": "collect",
    "collectContent": "collect",
    "getCollectList": "collect",
    # ---- commonspeaker（常用说话人）----
    "addCommonSpeaker": "commonspeaker",
    "listCommonSpeakers": "commonspeaker",
    "removeCommonSpeaker": "commonspeaker",
    # ---- contentCheck（内容审核）----
    "appealIllegalContent": "content_check",
    "delReportPic": "content_check",
    "getContentCheckStatus": "content_check",
    "reportIllegalContent": "content_check",
    "addUserReport": "content_check",
    # ---- authorization（授权）----
    "getAuthorization": "authorization",
    "delAuthorization": "authorization",
    # ---- training ----
    "checkFileNum": "training",
    "delFile": "training",
    "getFileList": "training",
    "syncFileLink": "training",
    "manageLabTraining": "training",
    "generateFileLink": "training",
    # ---- directory（文件夹）----
    "addDir": "directory",
    "changeDir": "directory",
    "delDir": "directory",
    "existProcessingTrans": "directory",
    "getDirList": "directory",
    "updateDir": "directory",
    # ---- doc（文档/笔记）----
    "applyRoleSplit": "doc",
    "applyTransDocEditTemplate": "doc",
    "resyncTransDocSrc": "doc",
    "saveTransDocEdit": "doc",
    "saveTransDocResult": "doc",
    "getTransDocEdit": "doc",
    # ---- export（导出）----
    "exportPptPic": "export",
    # ---- feedback ----
    "sendFeecback": "feedback",
    "submitFeedback": "feedback",
    # ---- helpdoc ----
    "getHelpDocTree": "helpdoc",
    "getHelpDocUrlByPath": "helpdoc",
    "searchHelpDoc": "helpdoc",
    "searchHelpDocTitle": "helpdoc",
    # ---- history（搜索历史）----
    "delTransDocSearchHistory": "history",
    "getTransDocSearchHistory": "history",
    "updateTransDocSearchHistory": "history",
    # ---- hotword（热词）----
    "addHotWords": "hotword",
    "delHotWords": "hotword",
    "getHotWordList": "hotword",
    "updateHotWord": "hotword",
    # ---- lab（AI 实验室/智能速览/问答）----
    "addLabFeedback": "lab",
    "addLabFeedbackDetail": "lab",
    "addLabResult": "lab",
    "clearAiSearchHistory": "lab",
    "delLabPptPic": "lab",
    "delLabQaResult": "lab",
    "delLabResult": "lab",
    "getAiHistorySearch": "lab",
    "getAiQuestionData": "lab",
    "getAiSearchFeedback": "lab",
    "getAiSearchStatus": "lab",
    "getAiSearchUrl": "lab",
    "getAllLabInfo": "lab",
    "getLabKeyStatus": "lab",
    "labRecommendQuestionsInfo": "lab",
    "modAiSearchFeedback": "lab",
    "modLabFeedback": "lab",
    "modLabResult": "lab",
    "modMoreLabResult": "lab",
    "startAiSearchIndex": "lab",
    "getFileTextPolish": "lab",
    "openFileTextPolish": "lab",
    # ---- meeting（实时会议）----
    "clearLiveMeetingPg": "meeting",
    "configMeeting": "meeting",
    "createMeeting": "meeting",
    "getLiveMeetingInfo": "meeting",
    "getLiveInfo": "meeting",
    "bindLiveMeeting": "meeting",
    "meetingTranslate": "meeting",
    "realtimeTranslate": "meeting",
    "saveMeetingDocResult": "meeting",
    "startLiveMeeting": "meeting",
    "stopMeeting": "meeting",
    "transientTranslate": "meeting",
    # ---- notify（钉钉待办）----
    "getDingToDoDetails": "notify",
    "getDingToDoHistory": "notify",
    "getDingUnionId": "notify",
    "sendDingToDo": "notify",
    "createDingToDo": "notify",
    # ---- notice ----
    "opNotice": "notice",
    # ---- operationRecord ----
    "getOperationRecord": "operation_record",
    "syncOperationRecord": "operation_record",
    # ---- record（客户端记录）----
    "getClientRecord": "record",
    "syncClientRecord": "record",
    # ---- rss（订阅内容）----
    "getSubscribedRssList": "rss",
    "syncRssSubscribeStatus": "rss",
    "getRssInfo": "rss",
    "getCategoryRssList": "rss",
    "addRssFeedback": "rss",
    "searchRssEs": "rss",
    "getPublicRssContent": "content",
    "getPersonalRssContent": "content",
    "getContentWithTransId": "content",
    "getSubscribeUpdateStatus": "content",
    "getContentCollectStatus": "content",
    "getContentInRss": "content",
    "getContentStatus": "content",
    "getPushCard": "content",
    "addRssSearchFeedback": "rss",
    "searchRssItemEs": "rss",
    "getRssCategoryList": "rss_category",
    "syncRssCategorySubscribeStatus": "rss_category",
    # ---- share（分享）----
    "generateSharePosterPutLink": "share",
    "getInviteShareInfo": "share",
    "getShareConfig": "share",
    "queryShareUpdate": "share",
    "saveExploreRss": "share",
    "syncShareConfig": "share",
    "updateShare": "share",
    "getShare": "share",
    "getSharePublicConfig": "share",
    "shareToUsers": "share",
    "cancelShareToUser": "share",
    "getShareCarrier": "share",
    "getShareListInfo": "share",
    "getShareUserHistory": "share",
    "saveShare": "share",
    "delShareMe": "trans",
    # ---- subscribe ----
    "getSubscribeStatus": "subscribe",
    "updateSubscribeStatus": "subscribe",
    # ---- tag ----
    "getTransTag": "tag",
    "getUserTag": "tag",
    "syncTransTag": "tag",
    "syncUserTag": "tag",
    # ---- trans（转写核心）----
    "delTrans": "trans",
    "disableUploadingTrans": "trans",
    "generatePutLink": "trans",
    "getTransList": "trans",
    "getTransStatus": "trans",
    "startTrans": "trans",
    "syncPutLink": "trans",
    "triggerRoleSplit": "trans",
    "parseNetSourceUrl": "trans",
    "putNetSourceUrl": "trans",
    "queryNetSourceParse": "trans",
    "queryNetSourceUpload": "trans",
    "getPublicShareTransList": "trans",
    # ---- trans_brk ----
    "getMeetingResult": "trans_brk",
    "getTransUserInfo": "trans_brk",
    "saveDocResult": "trans_brk",
    # ---- translate ----
    "getTransTranslateTargetLang": "translate",
    "openFileTranslate": "translate",
    "translateParagraph": "translate",
    "getFileTranslation": "translate",
    "getLabTranslation": "translate",
    "openFileTranslation": "translate",
    # ---- trans（结果直取，非 /request 形式，见 DIRECT_ENDPOINTS）----
    "getTransResult": "trans",
    "getUserSummaryDayEquity": "tingwu_account",
    # ---- 前端埋点（非 API，仅出现在 bundle 中）----
    "checkAfs": "tingwu_account",
    # ---- trash（回收站）----
    "delAllTrashes": "trash",
    "delTrashes": "trash",
    "getTrashList": "trash",
    "revertTrashes": "trash",
}

#: 不走 ``/request?action`` 形式的独立接口（path 已含全部信息）
DIRECT_ENDPOINTS: dict[str, str] = {
    # 账号
    "account_info": "/tingwu/account/info",
    "aliyun_user_info": "/account/v2/user/info",
    "aliyun_user_source": "/account/v2/user/source",
    "aliyun_user_third_info": "/account/v2/user/third/info",
    "aliyundrive_bind": "/account/v2/user/aliyundriver/bind",
    "aliyundrive_unbind": "/account/v2/user/aliyundriver/unbind",
    "send_edu_email": "/account/v1/email/sendEduEmail",
    # 转写结果（注意：不是 /request 形式）
    "trans_result": "/trans/getTransResult",
    "net_source_parse": "/trans/parseNetSourceUrl",
    "net_source_query": "/trans/queryNetSourceParse",
    "public_share_trans_list": "/trans/getPublicShareTransList",
    # 翻译
    "open_file_translation": "/translate/openFileTranslation",
    "get_file_translation": "/translate/getFileTranslation",
    "get_lab_translation": "/translate/getLabTranslation",
    # 通知
    "notice_list": "/notice/list",
    "notice_home": "/notice/home",
    # 上传
    "upload_lab_pic": "/lab/uploadLabPic",
    "upload_hotword_file": "/hotword/uploadFile",
    # 订阅/权益
    "gain_equity": "/subscription/equity/gainEquity",
    "login_warning": "/subscription/equity/loginWarning",
    "equity_status_v2": "/subscription/equity/queryAliyunDriveEquityStatusV2",
    "bring_new_user_ranking": "/subscription/equity/getBringNewUserRanking",
    "promotion_status": "/subscription/promotion/getPromotionStatus",
    "sync_promotion_tip": "/subscription/promotion/syncPromotionTipStatus",
    # 其他
    "precheck": "/one/precheck",
    "get_trans_doc_edit": "/doc/getTransDocEdit",
    "content_search": "/explore/content/search",
    "public_rss_content": "/explore/content/getPublicRssContent",
    "content_collect_status": "/explore/content/getContentCollectStatus",
    "rss_search": "/explore/rss/search",
    "rss_search_top": "/explore/rss/searchRssTop",
    "rss_category_list": "/explore/rss/category/getRssCategoryList",
    "push_card": "/explore/recommend/getPushCard",
    "ka_config": "/distribute/ka/config",
}


#: 虽然出现在 ``action:"..."`` 里，但实际**不走** ``/<module>/request?<action>``
#: 形式，而是独立路径。调用方应改用 :data:`DIRECT_ENDPOINTS` 中的别名。
#:
#: ``getTransResult`` 实测：``/trans/request?getTransResult`` 返回
#: ``Action error``，正确路径是 ``/trans/getTransResult``。
PATH_OVERRIDES: dict[str, str] = {
    "getTransResult": "/trans/getTransResult",
    "parseNetSourceUrl": "/trans/parseNetSourceUrl",
    "queryNetSourceParse": "/trans/queryNetSourceParse",
    "getPublicShareTransList": "/trans/getPublicShareTransList",
    "openFileTranslation": "/translate/openFileTranslation",
    "getFileTranslation": "/translate/getFileTranslation",
    "getTransDocEdit": "/doc/getTransDocEdit",
    "getPublicRssContent": "/explore/content/getPublicRssContent",
    "getContentCollectStatus": "/explore/content/getContentCollectStatus",
    "getContentInRss": "/explore/content/getContentInRss",
    "getContentStatus": "/explore/content/getContentStatus",
    "getRssCategoryList": "/explore/rss/category/getRssCategoryList",
    "getPushCard": "/explore/recommend/getPushCard",
    "getAllLabInfo": "/lab/getAllLabInfo",
    "getLabTranslation": "/translate/getLabTranslation",
    "getRssInfo": "/explore/rss/getRssInfo",
    "getFileTextPolish": "/lab/getFileTextPolish",
}


def endpoint_for_action(action: str) -> str:
    """把 action 名解析成 ``/api`` 之后的路径。

    优先查 :data:`PATH_OVERRIDES`（独立路径），再退回
    ``<module>/request?<action>`` 形式。

    Raises:
        KeyError: action 未在映射表中（可能是新增接口，需更新本表）。
    """
    if action in PATH_OVERRIDES:
        return PATH_OVERRIDES[action]
    module = ACTION_MODULE.get(action)
    if module is None:
        raise KeyError(
            f"未知 action: {action!r}。已知 {len(ACTION_MODULE)} 个。"
            f"若为新增接口，请更新 tingwu.endpoints.ACTION_MODULE"
        )
    return f"{MODULE_PATHS[module]}?{action}"
