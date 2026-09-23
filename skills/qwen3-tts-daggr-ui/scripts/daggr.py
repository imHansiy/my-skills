"""协议常量、数据模型与纯函数辅助（供 client.py / graph.py 共用）。

HuggingFace Space ``prithivMLmods/Qwen3-TTS-Daggr-UI`` 不是 Gradio：推理走一条
自定义 WebSocket 节点图协议（前端叫 daggr）。协议细节见 references/protocol.md。

认证：该 Space 匿名可用，**不需要 token / cookie / session**。可选 HF token 只从
环境变量 ``QWEN3_TTS_HF_TOKEN`` 读取并按前端行为在消息里透传，绝不落盘或打印。
"""

from __future__ import annotations

import base64
import mimetypes
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

from exceptions import InputError, RunFailedError

# 默认目标 Space。可用 host 参数或 QWEN3_TTS_HOST 环境变量覆盖。
DEFAULT_HOST = "prithivmlmods-qwen3-tts-daggr-ui.hf.space"

# 四个可执行算子。INPUT 节点只是参数载体，不能直接 run。
NODE_VOICE_DESIGN = "Voice Design"
NODE_CUSTOM_VOICE = "Custom Voice"
NODE_VOICE_CLONE = "Voice Clone"
NODE_QWEN3_ASR = "Qwen3 ASR"

RUNNABLE_NODES = (NODE_VOICE_DESIGN, NODE_CUSTOM_VOICE, NODE_VOICE_CLONE, NODE_QWEN3_ASR)

# 产物端口名 → 语义。用于把 RunResult.audio 自动指向正确的输出端口。
AUDIO_PORTS = ("cloned_audio", "generated_audio", "tts_audio", "audio")

# 各算子的必填端口。
#
# 这份表的存在原因：服务端对漏传参数**不报错**。实测只传 language 就 run
# Custom Voice，服务端照样回 ``status:"Success"`` 并给一个可下载的 wav——
# 因为算子函数自带默认值。少传参数的唯一后果是"产出的音频不是你想要的"，
# 没有任何信号提示，所以只能在这里声明并在本地拦截。
REQUIRED_PORTS: Dict[str, tuple] = {
    NODE_CUSTOM_VOICE: ("text",),
    NODE_VOICE_DESIGN: ("text", "voice_description"),
    # ref_text 只在 ICL 模式（use_xvector_only=False）下参与推理；
    # x-vector 模式仅取说话人向量，逐字稿可以不精确甚至留空。
    NODE_VOICE_CLONE: ("ref_audio", "target_text"),
    NODE_QWEN3_ASR: ("audio_upload",),
}


class RecvTimeout(Exception):
    """内部信号：单个 recv 窗口内没有收到消息。

    与 ``RunTimeoutError`` 的区别在于，它不代表 ``run_timeout`` 已经耗尽——
    等待推理时空窗是正常的（服务端只在开始和结束时推消息），必须继续循环直到
    真正的 deadline，否则长任务会被 45s 的固定窗口误杀成"超时"。
    """


# 常见的音频扩展名 → MIME。用于把本地文件包成 data URL。
_AUDIO_MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".webm": "audio/webm",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


def looks_like_audio(body: bytes) -> bool:
    """按起始魔数判断下载到的字节是不是音频。

    用白名单而不是黑名单：黑名单（排除 ``text/*`` 或 ``<html`` 开头）
    漏得掉 JSON 错误体、带 BOM 的页面、前导空白的 HTML，
    这些仍会被静默写成打不开的 ``.wav`` 并回报成功。
    """
    head = body[:12]
    if head[:4] in (b"RIFF", b"fLaC", b"OggS", b"\x1aE\xdf\xa3"):
        return True
    if head[:3] == b"ID3":
        return True
    if head[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa"):
        return True
    # mp4 / m4a：'ftyp' 固定出现在第 5~8 字节
    return head[4:8] == b"ftyp"


def session_id() -> str:
    """生成会话 ID，形状对齐前端：``session_`` + 随机串。"""
    return "session_" + uuid.uuid4().hex[:12]


def encode_audio(path: Union[str, Path]) -> str:
    """把本地音频文件编码成 data URL（前端上传音频用的就是这个形状）。"""
    p = Path(path)
    if not p.is_file():
        raise InputError(f"音频文件不存在：{p}")
    data = p.read_bytes()
    if not data:
        raise InputError(f"音频文件为空：{p}")
    mime = _AUDIO_MIME.get(p.suffix.lower())
    if mime is None:
        # 后缀不认识时用 mimetypes 猜；但音频端口传的是音频，若猜出
        # application/octet-stream 这类非音频类型，退到 audio/wav 更可能被服务端接受。
        guessed = mimetypes.guess_type(p.name)[0]
        mime = guessed if guessed and guessed.startswith("audio/") else "audio/wav"
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


@dataclass
class NodePort:
    """一个输入端口（或输出端口）。

    ``component`` 是该端口的控件类型（``textbox``/``dropdown``/``audio``/
    ``checkbox``），决定取值怎么规整（见 ``Qwen3TTSClient._coerce``）。
    FN 节点的输出端口在节点图里只给了名字，拿不到控件类型，因此留空。
    """

    port_name: str
    component: str = ""
    label: Optional[str] = None
    value: Any = None
    choices: Optional[List[str]] = None
    # 所属节点的 id，决定 run.inputs 里的键名前缀
    node_id: str = ""

    @property
    def qualified(self) -> str:
        """该端口在 ``run.inputs`` 里使用的完整键名：``<node_id>__<port>``。"""
        return f"{self.node_id}__{self.port_name}"


@dataclass
class NodeInfo:
    """工作流里的一个节点。"""

    name: str
    node_id: str
    type: str
    is_input_node: bool
    inputs: List[NodePort] = field(default_factory=list)
    outputs: List[NodePort] = field(default_factory=list)

    @property
    def runnable(self) -> bool:
        return self.type == "FN"

    def input_keys(self) -> List[str]:
        return [p.port_name for p in self.inputs]

    def output_keys(self) -> List[str]:
        return [p.port_name for p in self.outputs]

    def input_port(self, port_name: str) -> Optional[NodePort]:
        for p in self.inputs:
            if p.port_name == port_name:
                return p
        return None


@dataclass
class RunResult:
    """一次 ``run`` 的最终结果。"""

    node: str
    status: str
    outputs: Dict[str, Any]
    execution_time_ms: Optional[float] = None
    run_id: str = ""
    saved_to: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """``status`` 端口为 Success 即视为成功。

        服务端用同一张表回成功和业务失败，失败文案形如
        ``Text required`` / ``Error: Unsupported speakers: [...]``。
        """
        return str(self.status).strip().lower() == "success"

    @property
    def audio(self) -> Optional[str]:
        """产物音频的服务端路径（``/file/tmp/xxx.wav``）。"""
        for port in AUDIO_PORTS:
            v = self.outputs.get(port)
            if isinstance(v, str) and v.startswith("/file/"):
                return v
        return None

    @property
    def text(self) -> Optional[str]:
        """文本类产物（ASR 转写结果等）。"""
        for port in ("transcription", "detected_lang"):
            v = self.outputs.get(port)
            if v:
                return str(v)
        return None


def extract_choices(component: Mapping[str, Any]) -> Optional[List[str]]:
    """从 dropdown 的 props.choices 里抽出可选值。

    服务端给的是 ``[["Auto","Auto"], ...]`` 形式（label/value 对），
    这里统一取 value。
    """
    raw = (component.get("props") or {}).get("choices")
    if not raw:
        return None
    out: List[str] = []
    for item in raw:
        if isinstance(item, (list, tuple)) and item:
            out.append(str(item[0]))
        else:
            out.append(str(item))
    return out


def to_result(msg: Mapping[str, Any], node: NodeInfo) -> RunResult:
    """把 node_complete 消息里本节点的输出抽成 RunResult。"""
    outputs: Dict[str, Any] = {}
    status = ""
    for raw in msg.get("nodes") or []:
        if raw.get("name") != node.name:
            continue
        for comp in raw.get("output_components") or []:
            port = comp.get("port_name", "")
            outputs[port] = comp.get("value")
        status = str(outputs.get("status") or "")
    if not outputs:
        raise RunFailedError(f"{node.name} 的完成事件里没有找到输出端口", node=node.name)
    return RunResult(
        node=node.name,
        status=status,
        outputs=outputs,
        execution_time_ms=msg.get("execution_time_ms"),
        run_id=str(msg.get("run_id") or ""),
        raw=dict(msg),
    )


def normalize_space_name(name: str) -> str:
    """把 HF 仓库 ID 规范化成子域名的形状，用于反查。

    ``prithivMLmods/Qwen3-TTS-Daggr-UI`` → ``prithivmlmods-qwen3-tts-daggr-ui``。
    """
    return name.replace("/", "-").lower()


def is_blank(value: Any) -> bool:
    """判断取值是否等同"没给"。

    用于必填校验：``None`` / 空串 / 全空白都算没给，``False`` 和 ``0`` 算给了
    （``use_xvector_only=False`` 是一个有意义的取值，不能被当成缺参）。
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def as_bool(value: Any) -> bool:
    """把 CLI / JSON 传进来的各种写法收敛成 bool。

    checkbox 端口如果收到字符串 ``"false"``，Python 里是真值，
    原样发出会让服务端把开关打开，属于静默的行为偏差。
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "y", "on"):
            return True
        if text in ("false", "0", "no", "n", "off", ""):
            return False
    return bool(value)
