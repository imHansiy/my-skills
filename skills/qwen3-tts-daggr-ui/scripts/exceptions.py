"""异常类型。

分层原则：把「连不上」和「连上了但业务失败」分开，调用方才能正确决策
（前者可重试，后者重试无用且浪费一次完整推理）。
"""

from __future__ import annotations


class Qwen3TTSError(Exception):
    """本 SDK 所有异常的基类。"""


class TransportError(Qwen3TTSError):
    """WebSocket 建连/收发失败，或下载音频失败。

    属于可重试类别：网络抖动、Space 正在冷启动（容器未就绪）都会走到这里。

    ``result`` 仅在「推理已成功、下载产物失败」时被填上（见 ``run`` 的
    ``save_to``）：此时重试应当是**重新下载**，而不是重跑一次推理。
    """

    #: 触发下载失败的那次 run 结果，可从 ``result.audio`` 取回服务端路径。
    result = None


class GraphError(Qwen3TTSError):
    """无法获取或解析节点图。

    Space 处于 Building / Sleeping 时也会走到这里。
    """


class NodeNotFoundError(Qwen3TTSError):
    """请求的节点名在工作流里不存在。

    必须提前拦截：服务端对未知节点名【静默不响应】，
    不做校验就会一直挂到超时，看起来像"推理很慢"。
    """


class RunFailedError(Qwen3TTSError):
    """节点执行完成但业务失败。

    典型 status 文本：``Text required``、``Error: Unsupported speakers: [...]``。
    """

    def __init__(self, message: str, *, node: str = "", status: str = "") -> None:
        super().__init__(message)
        self.node = node
        self.status = status


class RunTimeoutError(Qwen3TTSError):
    """等待 node_complete 超过 deadline。"""


class InputError(Qwen3TTSError):
    """本地输入不合法（文件不存在、音频为空等）。"""
