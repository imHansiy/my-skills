"""转写核心接口。"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from urllib.parse import urlparse
from typing import Any, Iterator, Optional, Sequence

from ..exceptions import APIError

#: 转写状态码（实测）
STATUS_UPLOADING = 0  # 上传中/转写中（取决于是否有 transStartTime）
STATUS_SUCCESS = 1
STATUS_FAILED = 2
STATUS_QUEUING = 3
STATUS_TRANSLATING = 4
STATUS_PAUSED = 11

STATUS_NAMES = {
    0: "processing",
    1: "success",
    2: "failed",
    3: "queuing",
    4: "translating",
    11: "paused",
}

#: 扩展名 -> (OSS Content-Type, 是否视频)。
#: 上传时 ``fileContentType`` 与 ``originalTag.isVideo`` 必须和真实媒体一致，
#: 否则服务端按音频处理，视频文件会转写失败。
MEDIA_TYPES: dict[str, tuple[str, bool]] = {
    # 视频
    "mp4": ("video/mp4", True),
    "mov": ("video/quicktime", True),
    "mkv": ("video/x-matroska", True),
    "webm": ("video/webm", True),
    "avi": ("video/x-msvideo", True),
    "flv": ("video/x-flv", True),
    "m4v": ("video/mp4", True),
    "wmv": ("video/x-ms-wmv", True),
    "ts": ("video/mp2t", True),
    "mpeg": ("video/mpeg", True),
    "mpg": ("video/mpeg", True),
    "3gp": ("video/3gpp", True),
    # 音频
    "mp3": ("audio/mpeg", False),
    "wav": ("audio/wav", False),
    "m4a": ("audio/mp4", False),
    "aac": ("audio/aac", False),
    "flac": ("audio/flac", False),
    "ogg": ("audio/ogg", False),
    "opus": ("audio/ogg", False),
    "wma": ("audio/x-ms-wma", False),
    "amr": ("audio/amr", False),
    "aiff": ("audio/aiff", False),
}

#: 未知扩展名时的兜底（按音频处理，与服务端默认一致）
DEFAULT_MEDIA_TYPE = ("audio/mpeg", False)


def media_type_of(fmt: str) -> "tuple[str, bool]":
    """按扩展名推断 (Content-Type, is_video)。

    未知扩展名返回 :data:`DEFAULT_MEDIA_TYPE`。
    """
    return MEDIA_TYPES.get((fmt or "").lstrip(".").lower(), DEFAULT_MEDIA_TYPE)


@dataclass
class Sentence:
    """一条句子（转写的最小单元）。"""

    text: str
    begin_ms: int
    end_ms: int
    sentence_index: int
    """全局句子序号（``si``），跨段落递增。"""
    speaker: str
    """说话人标识（``ui``，如 ``"1"`` / ``"2"``）。未开启角色分离时为单值。"""
    words: list[dict[str, Any]] = field(default_factory=list)
    """原始分词（若接口返回）。"""

    @property
    def begin(self) -> float:
        """起始秒。"""
        return self.begin_ms / 1000.0

    @property
    def end(self) -> float:
        """结束秒。"""
        return self.end_ms / 1000.0

    def __str__(self) -> str:
        return f"[{self.speaker}] {self.text}"


@dataclass
class Paragraph:
    """一个段落，含若干句子。"""

    ui: str
    pi: str
    sentences: list[Sentence] = field(default_factory=list)

    @property
    def speaker(self) -> str:
        return self.ui

    @property
    def text(self) -> str:
        return "".join(s.text for s in self.sentences)

    def __str__(self) -> str:
        return self.text


@dataclass
class Transcript:
    """一份完整转写结果。

    ``raw`` 保留服务端原始响应，``meta`` 是 ``data`` 里的元信息。
    """

    trans_id: str
    sentences: list[Sentence] = field(default_factory=list)
    paragraphs: list[Paragraph] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """全文（按句拼接）。"""
        return "".join(s.text for s in self.sentences)

    @property
    def duration_ms(self) -> Optional[int]:
        """时长（毫秒）。

        Note:
            服务端 ``duration`` 字段单位是**秒**（实测 ``1670`` 对应
            ``max(et)=1670200`` 毫秒），这里统一换算成毫秒。
        """
        d = self.meta.get("duration")
        return int(d) * 1000 if d else None

    @property
    def duration(self) -> Optional[float]:
        """时长（秒）。"""
        d = self.meta.get("duration")
        return float(d) if d else None

    @property
    def speakers(self) -> list[str]:
        """出现过的说话人（按首次出现排序）。"""
        seen: list[str] = []
        for s in self.sentences:
            if s.speaker not in seen:
                seen.append(s.speaker)
        return seen

    @property
    def show_name(self) -> Optional[str]:
        return (self.meta.get("tag") or {}).get("showName")

    @property
    def playback_url(self) -> Optional[str]:
        """在线播放地址（OSS 签名链接，会过期）。"""
        return self.meta.get("playback")

    def by_speaker(self) -> dict[str, list[Sentence]]:
        """按说话人分组。"""
        out: dict[str, list[Sentence]] = {}
        for s in self.sentences:
            out.setdefault(s.speaker, []).append(s)
        return out

    def to_srt(self, *, with_speaker: bool = False) -> str:
        """导出 SRT 字幕。

        Args:
            with_speaker: 是否在文本前加 ``[说话人]`` 前缀。
        """

        def fmt(ms: int) -> str:
            h, rem = divmod(ms, 3_600_000)
            m, rem = divmod(rem, 60_000)
            s, msec = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{msec:03d}"

        blocks = []
        for i, s in enumerate(self.sentences, 1):
            txt = f"[{s.speaker}] {s.text}" if with_speaker else s.text
            blocks.append(f"{i}\n{fmt(s.begin_ms)} --> {fmt(s.end_ms)}\n{txt}\n")
        return "\n".join(blocks)

    def to_vtt(self, *, with_speaker: bool = False) -> str:
        """导出 WebVTT 字幕。"""

        def fmt(ms: int) -> str:
            h, rem = divmod(ms, 3_600_000)
            m, rem = divmod(rem, 60_000)
            s, msec = divmod(rem, 1000)
            return f"{h:02d}:{m:02d}:{s:02d}.{msec:03d}"

        lines = ["WEBVTT", ""]
        for s in self.sentences:
            txt = f"<v {s.speaker}>{s.text}" if with_speaker else s.text
            lines += [f"{fmt(s.begin_ms)} --> {fmt(s.end_ms)}", txt, ""]
        return "\n".join(lines)

    def to_text(self, *, with_timestamps: bool = False, with_speaker: bool = False) -> str:
        """导出纯文本。"""
        out = []
        for s in self.sentences:
            parts = []
            if with_timestamps:
                parts.append(f"[{s.begin:.1f}s]")
            if with_speaker:
                parts.append(f"说话人{s.speaker}:")
            parts.append(s.text)
            out.append(" ".join(parts))
        return "\n".join(out)

    def to_markdown(self) -> str:
        """导出 Markdown（按段落 + 说话人）。"""
        lines = [f"# {self.show_name or self.trans_id}", ""]
        if self.duration:
            lines += [f"- 时长: {self.duration / 60:.1f} 分钟", f"- 说话人: {len(self.speakers)}", ""]
        cur = None
        for s in self.sentences:
            if s.speaker != cur:
                cur = s.speaker
                lines += ["", f"**说话人 {cur}**", ""]
            lines.append(s.text)
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.sentences)

    def __iter__(self) -> Iterator[Sentence]:
        return iter(self.sentences)


def parse_transcript(payload: dict[str, Any]) -> Transcript:
    """把 ``getTransResult`` 的响应 ``data`` 解析成 :class:`Transcript`。

    服务端结构（实测）::

        data.tag                    -> 元信息
        data.result                 -> JSON 字符串: {"pg": [...]}
        data.result.pg[i].ui        -> 说话人 id
        data.result.pg[i].sc[j]     -> {bt, et, id, si, tc}
                                       bt/et 毫秒, si 全局句序, tc 文本
    """
    trans_id = payload.get("transId") or ""
    t = Transcript(trans_id=trans_id, meta=payload, raw=payload)

    raw_result = payload.get("result")
    if not raw_result:
        return t
    try:
        parsed = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    except (json.JSONDecodeError, TypeError):
        return t

    for pgi, pg in enumerate(parsed.get("pg") or []):
        ui = str(pg.get("ui", ""))
        para = Paragraph(ui=ui, pi=str(pg.get("pi", pgi)))
        for sc in pg.get("sc") or []:
            sent = Sentence(
                text=sc.get("tc", ""),
                begin_ms=int(sc.get("bt") or 0),
                end_ms=int(sc.get("et") or 0),
                sentence_index=int(sc.get("si") or 0),
                speaker=ui or str(sc.get("ui", "")),
                words=sc.get("ws") or [],
            )
            para.sentences.append(sent)
            t.sentences.append(sent)
        t.paragraphs.append(para)
    return t


class TransResource:
    """转写列表、状态、结果、上传、删除。"""

    def __init__(self, client: Any) -> None:
        self._c = client

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list(
        self,
        *,
        dir_id: Optional[int] = None,
        status: Optional[Sequence[int]] = None,
        show_name: str = "",
        media_type: str = "",
        lang: str = "",
        begin_time: str = "",
        end_time: str = "",
        page: int = 1,
        page_size: int = 20,
        order_desc: bool = True,
        raw: bool = False,
    ) -> Any:
        """列出转写记录。

        Args:
            dir_id: 文件夹 ID；``None`` 表示全部（不传 dirId）。
            status: 状态过滤。默认 ``[0]``（进行中）。``[1,2,3,4,11]`` 为历史。
            show_name: 按名称模糊搜索。
            page: 页码（从 1 起）。
            page_size: 每页数量（前端最大用 1000）。
            raw: True 时返回完整响应（含 ``total``）。

        Returns:
            记录列表；``raw=True`` 时返回含 ``total`` / ``data`` 的完整体。

        Example:
            >>> client.trans.list(dir_id=0, status=[0])
            [{'transId': 'kvjonymem8ognlx3', 'tag': {...}, ...}]
        """
        filt: dict[str, Any] = {
            "status": list(status) if status is not None else [0],
            "fileTypes": [],
            "beginTime": begin_time,
            "mediaType": media_type,
            "endTime": end_time,
            "showName": show_name,
            "read": "",
            "lang": lang,
            "shareUserId": "",
            "client": "",
        }
        if dir_id is not None:
            filt["dirId"] = dir_id
        body = {
            "userId": "",
            "filter": filt,
            "orderType": 0,
            "orderDesc": order_desc,
            "preview": 1,
            "pageNo": page,
            "pageSize": page_size,
        }
        res = self._c.request("getTransList", params=body, raw=True)
        return res if raw else res.get("data", [])

    def iter_all(
        self,
        *,
        status: Optional[Sequence[int]] = None,
        page_size: int = 100,
        max_items: Optional[int] = None,
        **kw: Any,
    ) -> Iterator[dict[str, Any]]:
        """自动翻页遍历全部记录。"""
        page = 1
        got = 0
        while True:
            res = self.list(status=status, page=page, page_size=page_size, raw=True, **kw)
            items = res.get("data") or []
            if not items:
                return
            for it in items:
                yield it
                got += 1
                if max_items and got >= max_items:
                    return
            total = res.get("total")
            if total is not None and got >= int(total):
                return
            if len(items) < page_size:
                return
            page += 1

    def status(self, trans_ids: Sequence[str], *, preview: int = 1) -> list[dict[str, Any]]:
        """批量查询转写状态。"""
        return self._c.request(
            "getTransStatus",
            params={"userId": "", "transIds": list(trans_ids), "preview": preview},
        )

    def result(self, trans_id: str, *, parse: bool = True) -> Any:
        """取转写结果。

        Args:
            trans_id: 转写 ID。
            parse: True 返回 :class:`Transcript`；False 返回原始 ``data``。

        Note:
            该接口路径是 ``/trans/getTransResult``（不是 ``/request`` 形式），
            已由 :data:`~tingwu.endpoints.DIRECT_ENDPOINTS` 处理。
        """
        data = self._c.direct("trans_result", body={"action": "getTransResult", "version": "1.0", "transId": trans_id})
        return parse_transcript(data) if parse else data

    def result_raw(self, trans_id: str) -> dict[str, Any]:
        """取原始结果（含 ``result`` JSON 字符串、``playback`` 等）。"""
        return self._c.direct(
            "trans_result",
            body={"action": "getTransResult", "version": "1.0", "transId": trans_id},
        )

    def detail(self, trans_id: str) -> dict[str, Any]:
        """结果 + 元信息的完整原始响应。"""
        return self.result_raw(trans_id)

    # ------------------------------------------------------------------
    # 删除 / 回收站
    # ------------------------------------------------------------------

    def delete(self, trans_ids: "str | Sequence[str]", *, permanent: bool = False) -> Any:
        """删除转写（默认进回收站）。"""
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        return self._c.request(
            "delTrans", params={"userId": "", "transIds": ids, "deletePermanently": permanent}
        )

    def delete_from_share(self, trans_ids: "str | Sequence[str]") -> Any:
        """从"分享给我"里移除。"""
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        return self._c.request("delShareMe", params={"userId": "", "transIds": ids})

    def stop_uploading(self, trans_ids: "str | Sequence[str]") -> Any:
        """中断上传中的任务。"""
        ids = [trans_ids] if isinstance(trans_ids, str) else list(trans_ids)
        return self._c.request("disableUploadingTrans", params={"userId": "", "transIds": ids})

    # ------------------------------------------------------------------
    # 上传（三步：generatePutLink -> PUT OSS -> syncPutLink）
    # ------------------------------------------------------------------

    def generate_put_link(
        self,
        *,
        file_id: str,
        file_size: int,
        title: str,
        file_format: str,
        file_type: str = "local",
        dir_id: int = 0,
        lang: str = "cn",
        role_split_num: int = 0,
        translate_switch: int = 0,
        trans_target_value: int = 0,
        is_video: int = 0,
        use_sts: int = 0,
        file_content_type: str = "",
        **tag_extra: Any,
    ) -> dict[str, Any]:
        """第一步：申请 OSS 上传地址。

        Returns:
            含上传 URL / objectKey 等，直接喂给 :meth:`upload_bytes`。

        Note:
            完整上传链路（含 OSS PUT 与 :meth:`sync_put_link`）尚未在本库中
            实现为一步式方法，因为涉及 OSS 直传与断点续传策略。
            当前提供三个原子步骤，便于调用方自行编排。
        """
        tag = {
            "showName": title,
            "fileFormat": file_format,
            "fileType": file_type,
            "lang": lang,
            "roleSplitNum": role_split_num,
            "translateSwitch": translate_switch,
            "transTargetValue": trans_target_value,
            "originalTag": json.dumps({"isVideo": is_video}),
        }
        tag.update(tag_extra)
        return self._c.request(
            "generatePutLink",
            params={
                "taskId": file_id,
                "useSts": use_sts,
                "fileSize": file_size,
                "dirId": dir_id,
                "fileContentType": file_content_type,
                "tag": tag,
            },
        )

    def sync_put_link(
        self, file_link: str, trans_id: str, file_size: int, duration: int = 0
    ) -> Any:
        """第三步：通知服务端上传完成，触发转写。

        Args:
            file_link: **必须是** :meth:`generate_put_link` 返回的 ``getLink``，
                不能是 ``putLink`` 或 OSS objectKey——实测传 objectKey 会返回
                ``CMN.ServerError``。
            trans_id: :meth:`generate_put_link` 返回的 ``transId``。
            file_size: 文件字节数。
            duration: 音视频时长，**单位是秒**（前端传 ``Math.floor(ms/1000)``）。

        Note:
            这一步成功（``code: "0"``）后任务状态会变成转写中，可用
            :meth:`status` 跟进。
        """
        return self._c.request(
            "syncPutLink",
            params={
                "fileLink": file_link,
                "transId": trans_id,
                "fileSize": file_size,
                "duration": duration,
            },
        )

    def upload_bytes(
        self,
        data: bytes,
        *,
        title: str,
        file_format: str = "mp3",
        dir_id: int = 0,
        lang: str = "cn",
        duration: int = 0,
        content_type: Optional[str] = None,
        role_split_num: int = 0,
        translate_switch: int = 0,
        is_video: Optional[bool] = None,
        **tag_extra: Any,
    ) -> dict[str, Any]:
        """一步式上传：申请直传地址 -> PUT 到 OSS -> 通知服务端转写。

        对应首页「上传音视频」按钮的完整链路，三步已实测跑通。

        Args:
            data: 文件二进制内容。
            title: 记录名称。
            file_format: 扩展名，如 ``"mp3"`` / ``"mp4"`` / ``"wav"``。
            dir_id: 归属文件夹，默认根目录。
            lang: 语言，如 ``"cn"``。
            duration: 时长（秒），不传时服务端自行探测。
            content_type: OSS 的 ``Content-Type``。
            role_split_num: 说话人数量，0 为自动。
            translate_switch: 是否开启翻译。
            is_video: 是否视频（影响服务端后处理）。

        Returns:
            :meth:`generate_put_link` 的 ``data``，额外带 ``transId`` 可直接查状态。

        Note:
            ``content_type`` / ``is_video`` 留空时按 :data:`MEDIA_TYPES` 从
            ``file_format`` 推断——mp4/mov 等会按视频提交，mp3/wav 按音频。
            显式传入则以传入值为准。

        Example:
            >>> with open("meeting.mp3", "rb") as f:
            ...     r = client.trans.upload_bytes(f.read(), title="部门周会")
            >>> print(r["transId"])

        Note:
            超大文件建议自行分片或用 :meth:`generate_put_link` 配合 OSS SDK；
            这里直接用 ``session.put`` 单次提交。
        """
        task_id = f"sdk-{uuid.uuid4().hex[:16]}"
        if content_type is None or is_video is None:
            guess_type, guess_video = media_type_of(file_format)
            if content_type is None:
                content_type = guess_type
            if is_video is None:
                is_video = guess_video
        link = self.generate_put_link(
            file_id=task_id,
            file_size=len(data),
            title=title,
            file_format=file_format,
            dir_id=dir_id,
            lang=lang,
            role_split_num=role_split_num,
            translate_switch=translate_switch,
            is_video=1 if is_video else 0,
            file_content_type=content_type,
            **tag_extra,
        )
        # PUT 到 OSS：putLink 已含签名，带 Content-Type 即可
        resp = self._c.session.put(
            link["putLink"], data=data, headers={"Content-Type": content_type},
            timeout=self._c.timeout,
        )
        if resp.status_code >= 300:
            raise APIError(
                f"OSS 直传失败：HTTP {resp.status_code} {resp.text[:200]}",
                code=str(resp.status_code),
            )
        self.sync_put_link(link["getLink"], link["transId"], len(data), duration)
        return link

    def upload_file(
        self, path: str, *, title: str = "", dir: "str | int | None" = None, **kw: Any
    ) -> dict[str, Any]:
        """上传本地文件并触发转写（首页「上传音视频」的完整链路）。

        Args:
            path: 本地文件路径。
            title: 记录名称，留空用文件名（去扩展名）。
            dir: 目标文件夹，可以是文件夹名（如 ``"工作"``）或 dirId。
                留空表示默认文件夹（``dirId=0``）；名字找不到时报错，不会误传根目录。

        Returns:
            ``{"transId", "dirId", "dirName", "fileFormat", "isVideo", "contentType", ...}``，
            ``transId`` 可直接喂给 :meth:`wait` / :meth:`result`。

        Note:
            视频（mp4/mov 等）会自动带 ``fileContentType=video/mp4`` 与
            ``isVideo=1``，服务端才会按视频转写。

        Example:
            >>> r = client.trans.upload_file("周会.mp4", dir="工作")
            >>> tr = client.trans.wait(r["transId"])
        """
        with open(path, "rb") as f:
            data = f.read()
        if not title:
            title = os.path.splitext(os.path.basename(path))[0]
        fmt = os.path.splitext(path)[1].lstrip(".").lower() or "mp3"
        kw.setdefault("file_format", fmt)
        dir_id = self.resolve_dir_id(dir)
        link = self.upload_bytes(data, title=title, dir_id=dir_id, **kw)
        ctype, is_video = media_type_of(fmt)
        return {
            **link,
            "dirId": dir_id,
            "dirName": self._dir_name(dir_id, dir),
            "fileFormat": fmt,
            "contentType": kw.get("content_type") or ctype,
            "isVideo": kw.get("is_video") if kw.get("is_video") is not None else is_video,
        }

    def resolve_dir_id(self, dir: "str | int | None") -> int:
        """把文件夹名、路径或 dirId 归一化成 dirId。

        Args:
            dir: ``None`` / ``""`` → 默认文件夹 ``0``；
                数字或纯数字字符串 → 直接当 dirId；
                其它字符串 → 在目录树里按 **路径 > 末级名** 匹配，
                所以 ``"odoo"`` 和 ``"工作/odoo"`` 都能落到同一个文件夹。

        Raises:
            ValueError: 名字不存在（不会静默退回根目录，避免传错位置）。

        Note:
            目录树每层只按 ``dirName`` 建路径，同名的多个文件夹会命中
            第一个（前序遍历顺序），此时建议直接传 dirId。
        """
        if dir is None or dir == "":
            return 0
        if isinstance(dir, int) or (isinstance(dir, str) and dir.isdigit()):
            return int(dir)

        want = str(dir).replace("\\", "/").strip("/")
        if not want:
            return 0
        nodes = self._dir_nodes()

        # 1) 完整路径精确匹配
        for d in nodes:
            if d.get("path") == want:
                return int(d["dirId"])
        # 2) 路径后缀匹配（"odoo" -> "工作/odoo"）
        suffix_matches = [
            d for d in nodes if d.get("path", "").split("/")[-1] == want
            or d.get("path", "").endswith("/" + want)
        ]
        if suffix_matches:
            suffix_matches.sort(key=lambda d: d.get("path", "").count("/"))
            return int(suffix_matches[0]["dirId"])

        raise ValueError(
            f"找不到文件夹 {dir!r}。可用 ``tingwu dirs`` 查看，或直接传 dirId。"
        )

    def _dir_nodes(self) -> list[dict[str, Any]]:
        """取拍平后的目录树（带 ``path``），失败时返回空列表。"""
        try:
            from .directory import DirectoryResource

            return DirectoryResource(self._c).flatten()
        except Exception:
            return []

    def _dir_name(self, dir_id: int, given: "str | int | None") -> str:
        """返回文件夹显示名（含父级路径），用于回显；查不到就用传入值/默认名。"""
        if dir_id == 0:
            return "默认文件夹"
        try:
            for d in self._dir_nodes():
                if int(d.get("dirId", -1)) == dir_id:
                    return str(d.get("path") or d.get("dirName", ""))
        except Exception:
            pass
        if isinstance(given, str) and not given.isdigit():
            return given
        return str(dir_id)

    def wait(
        self,
        trans_id: str,
        *,
        timeout: float = 3600.0,
        interval: float = 10.0,
        quiet: bool = True,
    ) -> dict[str, Any]:
        """轮询等待转写完成。

        Args:
            trans_id: 转写 ID。
            timeout: 最长等待秒数。
            interval: 轮询间隔秒数。
            quiet: True 不打印进度。

        Returns:
            最后一次 :meth:`status` 的条目。``status`` 为 1 表示成功，
            2 表示失败，超时则为 ``"timeout"``。
        """
        import time

        deadline = time.time() + timeout
        last: dict[str, Any] = {}
        while True:
            for it in self.status([trans_id]) or []:
                if str(it.get("transId")) == str(trans_id):
                    last = it
            code = last.get("status")
            if code in (STATUS_SUCCESS, STATUS_FAILED):
                if not quiet:
                    print(f"transId={trans_id} {STATUS_NAMES.get(code, code)}")
                return last
            if time.time() >= deadline:
                last["status"] = "timeout"
                return last
            if not quiet:
                print(f"transId={trans_id} {STATUS_NAMES.get(code, code)} ...")
            time.sleep(interval)

    def start(self, **params: Any) -> Any:
        """启动转写（参数随场景变化，透传）。"""
        return self._c.request("startTrans", params=params)

    # ------------------------------------------------------------------
    # 其他
    # ------------------------------------------------------------------

    def trigger_role_split(self, **params: Any) -> Any:
        """触发/重新触发角色分离。"""
        return self._c.request("triggerRoleSplit", params=params)

    def parse_net_source(self, url: str, **params: Any) -> Any:
        """解析网盘/网页音视频直链。"""
        return self._c.direct("net_source_parse", body={"url": url, **params})

    def query_net_source(self, **params: Any) -> Any:
        """查询直链解析进度。"""
        return self._c.direct("net_source_query", body=params)

    def put_net_source_url(
        self,
        files: "Sequence[dict[str, Any]]",
        **params: Any,
    ) -> Any:
        """提交播客/网页音视频链接到转写列表（首页「播客链接转写」按钮）。

        Args:
            files: 由 :meth:`parse_net_source` 解析出的条目，每项形如::

                {
                    "fileId": "<taskId>-0",      # 解析结果里的 fileId，必填
                    "dirId": 0,
                    "fileSize": 54632848,        # 解析结果里的 size
                    "tag": {
                        "fileType": "net_source",
                        "showName": "某一期播客",
                        "lang": "cn",
                        "roleSplitNum": 0,
                        "translateSwitch": 0,
                        "transTargetValue": 0,
                        "client": "web",
                        "originalTag": "",        # 视频填 '{"isVideo":1}'
                    },
                }

        Note:
            ``fileId`` 必须来自 :meth:`parse_net_source`——实测随意构造会返回
            ``TRS.TaskIdNotFound``。解析结果字段叫 ``urls``（不是 ``files``）。
        """
        return self._c.request(
            "putNetSourceUrl", params={"files": list(files), **params}
        )

    def query_net_source_upload(self, trans_ids: "Sequence[str]") -> Any:
        """查询播客链接转写的上传/解析进度。

        Args:
            trans_ids: 转写 ID 列表（提交后从转写列表里取）。
        """
        return self._c.request(
            "queryNetSourceUpload", params={"transIds": list(trans_ids)}
        )

    def transcribe_net_source(
        self,
        url: str,
        *,
        dir_id: int = 0,
        lang: str = "cn",
        limit: int = 1,
        poll_interval: float = 4.0,
        poll_timeout: float = 60.0,
        **tag_extra: Any,
    ) -> Any:
        """解析播客链接并提交转写（解析 + 提交两步合一）。

        Args:
            url: 播客 RSS 地址或单集页面地址。
            dir_id: 归属文件夹。
            lang: 语言。
            limit: 取解析结果的前 N 条。
            poll_interval: 解析轮询间隔（秒）。
            poll_timeout: 解析最长等待（秒）。

        Returns:
            :meth:`put_net_source_url` 的响应。
        """
        import time

        parsed = self.parse_net_source(url)
        task_id = parsed.get("taskId") if isinstance(parsed, dict) else None
        if not task_id:
            raise APIError(f"解析未返回 taskId：{parsed!r}")

        deadline = time.time() + poll_timeout
        urls: list[dict[str, Any]] = []
        while time.time() < deadline:
            q = self.query_net_source(taskId=task_id)
            urls = (q or {}).get("urls") or []
            if urls:
                break
            time.sleep(poll_interval)
        if not urls:
            raise APIError(f"解析超时或未拿到条目：taskId={task_id}")

        files = []
        for u in urls[:limit]:
            files.append(
                {
                    "fileId": u.get("fileId"),
                    "dirId": dir_id,
                    "fileSize": u.get("size") or 0,
                    "tag": {
                        "fileType": "net_source",
                        "showName": u.get("showName") or "",
                        "lang": lang,
                        "roleSplitNum": 0,
                        "translateSwitch": 0,
                        "transTargetValue": 0,
                        "client": "web",
                        "originalTag": '{"isVideo":1}' if u.get("isVideo") else "",
                        **tag_extra,
                    },
                }
            )
        return self.put_net_source_url(files)

    def shared_with_me(self, **params: Any) -> Any:
        """别人分享给我的转写列表。"""
        return self._c.direct("public_share_trans_list", body=params)
