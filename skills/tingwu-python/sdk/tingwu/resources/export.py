"""导出（官方导出服务）。

服务端导出走 ``/api/export/request``（与阿里云盘那套 ``/aliyundrive/request``
是两个不同产品线，本模块只覆盖本地下载这一套）。

流程是异步的两步：

1. :meth:`ExportResource.create` → ``exportTaskId``
2. :meth:`ExportResource.status` 轮询 → ``exportStatus`` 1 后取 ``exportUrls``

``docType`` / ``fileType`` 取值均来自实测：

=========  ============  ==========================
docType    含义          产出文件名后缀
=========  ============  ==========================
1          原文          ``_原文.<ext>``
3          笔记          ``_笔记.pdf``
5          PPT           ``_PPT.pdf``
7          导读          ``_导读.pdf``
=========  ============  ==========================

``fileType`` 决定后缀：``0``=docx、``1``=pdf、``2``=srt、``3``=md。
并非所有组合都合法——实测笔记/PPT/导读只出 pdf，原文四种都能出。
"""

from __future__ import annotations

import time
from typing import Any, Optional, Sequence
from urllib.parse import parse_qs, unquote, urlparse

#: 导出内容类型（实测）
DOC_ORIGINAL = 1  # 原文
DOC_NOTE = 3  # 笔记
DOC_PPT = 5  # PPT
DOC_SMART_SCAN = 7  # 导读（智能速览）

DOC_NAMES = {
    DOC_ORIGINAL: "原文",
    DOC_NOTE: "笔记",
    DOC_PPT: "PPT",
    DOC_SMART_SCAN: "导读",
}

#: 导出文件格式（实测）
FILE_DOCX = 0
FILE_PDF = 1
FILE_SRT = 2
FILE_MD = 3

FILE_EXTS = {
    FILE_DOCX: "docx",
    FILE_PDF: "pdf",
    FILE_SRT: "srt",
    FILE_MD: "md",
}

#: :meth:`status` 的 ``exportStatus`` 取值
EXPORT_PENDING = 0
EXPORT_DONE = 1
EXPORT_FAILED = -1

#: 频控退避：连续导出会被 ``EPO.RequestTooFast`` 拒绝，等几秒重发即可
EXPORT_RETRIES = 5
EXPORT_RETRY_WAIT = 6.0

#: 刚转写完就导出时常拿到 ``success=false, failReason=3``——
#: 服务端还没把导出物准备好；等一会儿重发一次就好。
EXPORT_NOT_READY = 3
EXPORT_NOT_READY_RETRIES = 4
EXPORT_NOT_READY_WAIT = 20.0

EXPORT_ENDPOINT = "/export/request?exportTrans"
EXPORT_STATUS_ENDPOINT = "/export/request?getExportStatus"


class ExportResource:
    """官方导出：把转写结果导出为 docx / pdf / srt / md 并拿下载链接。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    def create(
        self,
        trans_ids: "str | Sequence[str]",
        *,
        doc_type: int = DOC_ORIGINAL,
        file_type: int = FILE_MD,
        with_speaker: bool = True,
        with_timestamp: bool = True,
        raw: bool = False,
    ) -> Any:
        """发起导出任务。

        Args:
            trans_ids: 单个或多个 transId。
            doc_type: 内容类型，见模块常量（1 原文 / 3 笔记 / 5 PPT / 7 导读）。
            file_type: 文件格式，见模块常量（0 docx / 1 pdf / 2 srt / 3 md）。
            with_speaker: 是否带说话人。
            with_timestamp: 是否带时间戳。
            raw: True 返回完整响应体（含 ``code`` / ``success``）。

        Returns:
            ``exportTaskId``（``raw=True`` 时返回整个 body）。

        Note:
            服务端对同一账号的导出有频控（``EPO.RequestTooFast``），
            连续导出时会自动退避重试，调用方不需要自己处理。

            ``fileType=4/5`` 实测返回 ``EPO.InvalidRequest``。
        """
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        details = [
            {
                "docType": doc_type,
                "fileType": file_type,
                "withSpeaker": with_speaker,
                "withTimeStamp": with_timestamp,
            }
        ]
        res = self._request_export(ids, details, raw=raw)
        if raw:
            return res
        return (res or {}).get("exportTaskId")

    def _request_export(
        self, ids: list[str], details: list[dict[str, Any]], *, raw: bool
    ) -> Any:
        """发起导出并自动退避重试。

        服务端对同一账号的导出有频控（``EPO.RequestTooFast``），
        连续导出多个文件时必然触发；这里等一会儿重发即可。
        """
        last: Optional[Exception] = None
        for attempt in range(EXPORT_RETRIES):
            try:
                return self._c.request(
                    "exportTrans",
                    params={"transIds": ids, "exportDetails": details},
                    endpoint=EXPORT_ENDPOINT,
                    raw=raw,
                )
            except Exception as e:  # 频控是响应体错误，落在这里
                if "TooFast" not in str(e) and "EPO.RequestTooFast" not in str(e):
                    raise
                last = e
                time.sleep(EXPORT_RETRY_WAIT * (attempt + 1))
        assert last is not None
        raise last

    def status(self, export_task_id: str, *, raw: bool = False) -> Any:
        """查导出进度。

        Args:
            export_task_id: :meth:`create` 返回的 ID。
            raw: True 返回完整响应体。

        Returns:
            ``data``：``{"exportStatus": 0|1|-1, "exportUrls": [...]}``。
            ``exportStatus`` 0=进行中、1=完成、-1=失败。
        """
        return self._c.request(
            "getExportStatus",
            params={"exportTaskId": export_task_id},
            endpoint=EXPORT_STATUS_ENDPOINT,
            raw=raw,
        )

    def wait(
        self,
        export_task_id: str,
        *,
        timeout: float = 300.0,
        interval: float = 3.0,
    ) -> dict[str, Any]:
        """轮询直到导出完成或失败。

        Returns:
            最后一次 ``data``（含 ``exportStatus`` 与 ``exportUrls``）。
            超时返回 ``{"exportStatus": "timeout"}``。
        """
        deadline = time.time() + timeout
        while True:
            data = self.status(export_task_id) or {}
            if data.get("exportStatus") in (EXPORT_DONE, EXPORT_FAILED):
                return data
            if time.time() >= deadline:
                return {"exportStatus": "timeout"}
            time.sleep(interval)

    def download(
        self,
        trans_ids: "str | Sequence[str]",
        *,
        doc_type: int = DOC_ORIGINAL,
        file_type: int = FILE_MD,
        with_speaker: bool = True,
        with_timestamp: bool = True,
        timeout: float = 300.0,
    ) -> list[dict[str, Any]]:
        """一步式导出：发起任务 -> 等完成 -> 下载全部文件。

        Returns:
            每项 ``{"transId", "docType", "success", "url", "filename", "content"}``。
            ``content`` 是文件字节（``success=False`` 时为 ``b""``）。
        """
        out: list[dict[str, Any]] = []
        wait_s = EXPORT_NOT_READY_WAIT
        for attempt in range(EXPORT_NOT_READY_RETRIES):
            task_id = self.create(
                trans_ids,
                doc_type=doc_type,
                file_type=file_type,
                with_speaker=with_speaker,
                with_timestamp=with_timestamp,
            )
            if not task_id:
                return out
            data = self.wait(task_id, timeout=timeout)
            out = self._collect(data, file_type, timeout)
            # 只有「导出物还没准备好」才值得重发；其它失败直接返回。
            if not any(u.get("failReason") == EXPORT_NOT_READY for u in out):
                return out
            if attempt + 1 < EXPORT_NOT_READY_RETRIES:
                time.sleep(wait_s)
                wait_s *= 1.5
        return out

    def _collect(
        self, data: dict[str, Any], file_type: int, timeout: float
    ) -> list[dict[str, Any]]:
        """按 ``exportUrls`` 下载文件（:meth:`download` 的单轮实现）。"""
        out: list[dict[str, Any]] = []
        for u in data.get("exportUrls") or []:
            if not u.get("success"):
                out.append(
                    {
                        "transId": u.get("transIdStr"),
                        "docType": u.get("docType"),
                        "success": False,
                        "url": "",
                        "filename": "",
                        "content": b"",
                        "failReason": u.get("failReason"),
                    }
                )
                continue
            item = {
                "transId": u.get("transIdStr"),
                "docType": u.get("docType"),
                "success": bool(u.get("success")),
                "url": u.get("url", ""),
                "filename": filename_of(u.get("url", "")),
                "content": b"",
            }
            if item["success"] and item["url"]:
                r = self._c.session.get(item["url"], timeout=max(timeout, 60))
                r.raise_for_status()
                item["content"] = r.content
            out.append(item)
        return out

    def save(
        self,
        trans_ids: "str | Sequence[str]",
        out_dir: str = ".",
        *,
        doc_type: int = DOC_ORIGINAL,
        file_type: int = FILE_MD,
        with_speaker: bool = True,
        with_timestamp: bool = True,
        timeout: float = 300.0,
    ) -> list[str]:
        """导出并落盘，返回写入的文件路径列表。

        文件名取服务端 ``response-content-disposition`` 里的名字，
        拿不到时用 ``<transId>.<ext>`` 兜底。
        """
        import os

        os.makedirs(out_dir, exist_ok=True)
        written: list[str] = []
        for item in self.download(
            trans_ids,
            doc_type=doc_type,
            file_type=file_type,
            with_speaker=with_speaker,
            with_timestamp=with_timestamp,
            timeout=timeout,
        ):
            if not item["success"]:
                continue
            name = item["filename"] or f"{item['transId']}.{FILE_EXTS.get(file_type, 'bin')}"
            path = os.path.join(out_dir, name)
            with open(path, "wb") as f:
                f.write(item["content"])
            written.append(path)
        return written


def filename_of(url: str) -> str:
    """从导出 URL 的 ``response-content-disposition`` 里解出文件名。

    URL 里文件名是 RFC 5987 形式（``attachment;filename*=UTF-8''%E5%8E%9F...``），
    双重 URL 编码，需要解两次。
    """
    if not url:
        return ""
    disp = parse_qs(urlparse(url).query).get("response-content-disposition") or [""]
    raw = disp[0]
    if "UTF-8''" not in raw:
        return ""
    return unquote(raw.split("UTF-8''", 1)[1])
