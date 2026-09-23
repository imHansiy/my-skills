"""命令行入口。

设计目标是让 Agent / 脚本可以直接调用，因此：

* 所有子命令默认输出**单行 JSON**（``--pretty`` 才换成人读格式），
  避免解析自然语言输出。
* 出错时退出码非 0，错误信息写 stderr，stdout 只有数据。
* ``schema`` 子命令把算子的参数契约直接吐出来，调用方无需先跑一次就能
  知道该传什么、哪些必填、枚举值有哪些。

常用::

    python scripts/qwen3tts.py doctor
    python scripts/qwen3tts.py nodes
    python scripts/qwen3tts.py schema "Voice Clone"
    python scripts/qwen3tts.py clone ref.wav -t "目标文本" -o out.wav
    python scripts/qwen3tts.py say -t "你好" --speaker Serena -o out.wav
    python scripts/qwen3tts.py design -t "你好" -d "warm female voice" -o out.wav
    python scripts/qwen3tts.py asr audio.wav
    python scripts/qwen3tts.py status
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from client import (
    DEFAULT_HOST,
    NODE_CUSTOM_VOICE,
    NODE_QWEN3_ASR,
    NODE_VOICE_CLONE,
    NODE_VOICE_DESIGN,
    REQUIRED_PORTS,
    Qwen3TTSClient,
    RunResult,
)
from exceptions import Qwen3TTSError


def _configure_stdio() -> None:
    """Windows 控制台默认可能是 GBK，中文进度/报错会抛 UnicodeEncodeError。

    失败也不影响主流程（重定向管道上 reconfigure 可能不可用）。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


def _error_type(exc: BaseException) -> str:
    """把异常类映射成稳定的字符串，便于调用方分支处理（见 references/errors.md）。"""
    return {
        "InputError": "invalid_input",
        "TransportError": "transport_error",
        "GraphError": "graph_error",
        "NodeNotFoundError": "unknown_node",
        "RunTimeoutError": "timeout",
        "RunFailedError": "run_failed",
    }.get(type(exc).__name__, type(exc).__name__)


def _emit(data: Any, pretty: bool) -> None:
    """输出结果。默认紧凑 JSON，便于程序解析。"""
    if pretty:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False))


def _emit_error(exc: BaseException, pretty: bool = False) -> None:
    """把异常压成稳定的 JSON 错误结构：{"ok": false, "error": {...}}。"""
    _emit(
        {"ok": False, "error": {"type": _error_type(exc), "message": str(exc)}},
        pretty,
    )


def _result_payload(res: RunResult) -> Dict[str, Any]:
    """把 RunResult 压成稳定的输出结构。

    ``status`` 单独给出：业务失败也走成功事件（见 references/errors.md），
    调用方必须靠 ``ok`` 判断，而不是靠有没有抛异常。
    """
    return {
        "ok": res.ok,
        "node": res.node,
        "status": res.status,
        "audio": res.audio,
        "text": res.text,
        "saved_to": res.saved_to,
        "execution_time_ms": res.execution_time_ms,
        "run_id": res.run_id,
        "outputs": res.outputs,
    }


def _build_client(args: argparse.Namespace) -> Qwen3TTSClient:
    """按命令行参数构造客户端。

    HF token 只从环境变量读，绝不接收命令行参数（参数会进 shell history
    与进程列表），也不写进任何输出。
    """
    return Qwen3TTSClient(
        host=getattr(args, "host", None) or os.environ.get("QWEN3_TTS_HOST") or DEFAULT_HOST,
        run_timeout=getattr(args, "timeout", None) or 600.0,
        connect_timeout=getattr(args, "connect_timeout", None) or 30.0,
    )


def _progress(msg: Dict[str, Any]) -> None:
    """把事件流打到 stderr，不污染 stdout 的 JSON。"""
    mtype = msg.get("type")
    if mtype == "node_started":
        print(f"[进度] 开始执行 {msg.get('node') or ''}", file=sys.stderr)
    elif mtype == "node_complete":
        ms = msg.get("execution_time_ms")
        suffix = f"，耗时 {float(ms) / 1000:.1f}s" if ms else ""
        print(f"[进度] 完成 {msg.get('completed_node') or ''}{suffix}", file=sys.stderr)


def _add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument("--host", help="覆盖 Space 主机名（或设 QWEN3_TTS_HOST）")
    sp.add_argument("--timeout", type=float, help="等待超时秒数（默认 600）")
    sp.add_argument("--connect-timeout", type=float, help="建连超时秒数（默认 30）")
    sp.add_argument("--pretty", action="store_true", help="人类可读输出（默认紧凑 JSON）")
    sp.add_argument("-q", "--quiet", action="store_true", help="不打印进度到 stderr")


# --------------------------------------------------------------------------
# 查询类子命令
# --------------------------------------------------------------------------
def cmd_nodes(args: argparse.Namespace) -> int:
    c = _build_client(args)
    nodes = [
        {
            "name": n.name,
            "node_id": n.node_id,
            "runnable": n.runnable,
            "required": list(REQUIRED_PORTS.get(n.name, ())),
            "inputs": [
                {"port": p.port_name, "component": p.component, "choices": p.choices}
                for p in n.inputs
            ],
            "outputs": n.output_keys(),
        }
        for n in c.nodes()
    ]
    _emit({"host": c.host, "nodes": nodes}, args.pretty)
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    """输出算子的参数契约（端口 / 控件类型 / 枚举 / 必填）。"""
    c = _build_client(args)
    info = c.describe(args.node)
    info["required"] = list(REQUIRED_PORTS.get(info["node"], ()))
    _emit(info, args.pretty)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """查询 Space 运行状态。非 RUNNING 时退出码 1。"""
    c = _build_client(args)
    st = c.space_status(repo=getattr(args, "repo", None))
    if not st.get("reachable"):
        print(f"Space 不可达：{st.get('error')}", file=sys.stderr)
        _emit(st, args.pretty)
        return 1
    _emit(st, args.pretty)
    return 0 if st.get("stage") == "RUNNING" else 1


# --------------------------------------------------------------------------
# 推理子命令
# --------------------------------------------------------------------------
def _run_and_emit(
    args: argparse.Namespace,
    node: str,
    inputs: Dict[str, Any],
    require: Optional[List[str]] = None,
) -> int:
    """统一的执行 + 输出。业务失败返回 1，但结果仍然打到 stdout。

    strict=False：业务失败不抛异常，而是带回 ``ok:false`` 的结果，
    避免调用方只能从异常文本里捞 status。
    """
    c = _build_client(args)
    res = c.run(
        node,
        inputs,
        on_event=None if args.quiet else _progress,
        save_to=getattr(args, "output", None),
        strict=False,
        require=list(REQUIRED_PORTS.get(node, ())) if require is None else require,
    )
    _emit(_result_payload(res), args.pretty)
    return 0 if res.ok else 1


def cmd_clone(args: argparse.Namespace) -> int:
    """声音克隆：参考音频 + 目标文本。"""
    inputs: Dict[str, Any] = {
        "ref_audio": args.ref_audio,
        "target_text": args.text,
        "language": args.language,
        "model_size": args.model_size,
    }
    # ref_text 只在 ICL 模式参与推理；不传时服务端用自己的默认值，
    # 因此只在用户显式给出时才带上。
    if args.ref_text is not None:
        inputs["ref_text"] = args.ref_text
    if args.xvector is not None:
        inputs["use_xvector_only"] = args.xvector
    return _run_and_emit(args, NODE_VOICE_CLONE, inputs)


def cmd_say(args: argparse.Namespace) -> int:
    """预置音色合成。"""
    inputs: Dict[str, Any] = {
        "text": args.text,
        "language": args.language,
        "speaker": args.speaker,
        "instruct": args.instruct,
        "model_size": args.model_size,
    }
    return _run_and_emit(args, NODE_CUSTOM_VOICE, inputs)


def cmd_design(args: argparse.Namespace) -> int:
    """音色设计：用自然语言描述一个新音色，不需要参考音频。"""
    inputs: Dict[str, Any] = {
        "text": args.text,
        "voice_description": args.description,
        "language": args.language,
    }
    return _run_and_emit(args, NODE_VOICE_DESIGN, inputs)


def cmd_asr(args: argparse.Namespace) -> int:
    """音频转写。产物是文本而非音频，不需要 -o。"""
    inputs: Dict[str, Any] = {"audio_upload": args.audio, "lang_disp": args.language}
    return _run_and_emit(args, NODE_QWEN3_ASR, inputs)


def cmd_run(args: argparse.Namespace) -> int:
    """通用执行：直接给 JSON 输入，覆盖便捷子命令之外的组合。"""
    if args.inputs:
        raw = args.inputs
    elif args.inputs_file:
        with open(args.inputs_file, "r", encoding="utf-8") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except ValueError as exc:
        print(f"输入不是合法 JSON：{exc}", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("输入必须是 JSON 对象（端口名 → 取值）", file=sys.stderr)
        return 2
    # 通用入口不做必填校验：调用方已显式列出端口；要严格校验请用具体子命令。
    return _run_and_emit(args, args.node, payload, require=[])


def cmd_doctor(args: argparse.Namespace) -> int:
    """环境自检：一次调用确认依赖、Space 状态与节点图是否可用。

    Space 休眠或重建时，后续命令会以各种"看起来像参数错"的形式失败，
    所以任何任务开始前先跑一次，比逐个命令试错便宜得多。
    """
    report: Dict[str, Any] = {"ok": True, "checks": {}}

    try:
        import websockets  # noqa: F401

        report["checks"]["websockets"] = {
            "ok": True,
            "version": getattr(websockets, "__version__", "?"),
        }
    except Exception as exc:
        report["ok"] = False
        report["checks"]["websockets"] = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
        }

    c = _build_client(args)
    report["host"] = c.host

    st = c.space_status()
    report["checks"]["space"] = {
        "ok": bool(st.get("reachable")) and st.get("stage") == "RUNNING",
        "stage": st.get("stage"),
        "hardware": st.get("hardware"),
        "error": st.get("error"),
    }
    if not report["checks"]["space"]["ok"]:
        report["ok"] = False

    try:
        nodes = c.runnable_nodes()
        report["checks"]["graph"] = {"ok": True, "operators": [n.name for n in nodes]}
    except Exception as exc:
        report["ok"] = False
        report["checks"]["graph"] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    _emit(report, args.pretty)
    return 0 if report["ok"] else 1


def cmd_download(args: argparse.Namespace) -> int:
    """下载服务端产物音频。

    推理成功但下载失败时应当重下而不是重跑：一次 run 就是一次完整 GPU 推理。
    """
    c = _build_client(args)
    path = c.download(args.path, args.output)
    _emit({"ok": True, "saved_to": str(path), "bytes": path.stat().st_size}, args.pretty)
    return 0


# --------------------------------------------------------------------------
# 参数解析
# --------------------------------------------------------------------------
_LANG = "Auto"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="qwen3tts.py",
        description="Qwen3-TTS Daggr Space 协议客户端（声音克隆 / 语音合成 / 音色设计 / 转写）",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("doctor", help="环境自检：依赖 + Space 状态 + 节点图（先跑这个）")
    _add_common(sp)
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("nodes", help="列出可用算子及其端口")
    _add_common(sp)
    sp.set_defaults(func=cmd_nodes)

    sp = sub.add_parser("schema", help="查看某个算子的参数契约（调用前建议先看）")
    sp.add_argument("node", help=f"算子名，如 {NODE_VOICE_CLONE!r}")
    _add_common(sp)
    sp.set_defaults(func=cmd_schema)

    sp = sub.add_parser("status", help="查询 Space 运行状态")
    sp.add_argument("--repo", help="HF 仓库 ID（默认自动反查）")
    _add_common(sp)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("clone", help="声音克隆：用参考音频合成目标文本")
    sp.add_argument("ref_audio", help="参考音频（本地文件路径；3~10 秒最佳）")
    sp.add_argument("-t", "--text", required=True, help="要合成的目标文本")
    sp.add_argument(
        "--ref-text",
        help="参考音频里说的内容。完整 ICL 模式下越准越像；x-vector 模式可不给",
    )
    sp.add_argument(
        "--xvector",
        choices=["true", "false"],
        help="true=只取说话人向量（快）；false=完整 ICL（更像，约慢一倍）",
    )
    sp.add_argument("--language", default=_LANG, help="语种（默认 Auto）")
    sp.add_argument("--model-size", default="1.7B", choices=["0.6B", "1.7B"])
    sp.add_argument("-o", "--output", help="产物保存路径（如 out.wav）")
    _add_common(sp)
    sp.set_defaults(func=cmd_clone)

    sp = sub.add_parser("say", help="预置音色合成")
    sp.add_argument("-t", "--text", required=True)
    sp.add_argument("--speaker", default="Ryan", help="内置说话人（默认 Ryan）")
    sp.add_argument("--instruct", default="Neutral", help="风格指令（默认 Neutral）")
    sp.add_argument("--language", default="English")
    sp.add_argument("--model-size", default="1.7B", choices=["0.6B", "1.7B"])
    sp.add_argument("-o", "--output")
    _add_common(sp)
    sp.set_defaults(func=cmd_say)

    sp = sub.add_parser("design", help="音色设计：用文字描述音色（无需参考音频）")
    sp.add_argument("-t", "--text", required=True)
    sp.add_argument("-d", "--description", required=True, help="音色描述（英文效果更稳）")
    sp.add_argument("--language", default=_LANG)
    sp.add_argument("-o", "--output")
    _add_common(sp)
    sp.set_defaults(func=cmd_design)

    sp = sub.add_parser("asr", help="音频转写")
    sp.add_argument("audio", help="本地音频文件")
    sp.add_argument("--language", default=_LANG)
    _add_common(sp)
    sp.set_defaults(func=cmd_asr)

    sp = sub.add_parser("run", help="通用执行：直接给 JSON 端口输入")
    sp.add_argument("node", help="算子名")
    sp.add_argument("--inputs", help="JSON 对象字符串")
    sp.add_argument("--inputs-file", help="从文件读 JSON（默认读 stdin）")
    sp.add_argument("-o", "--output")
    _add_common(sp)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("download", help="下载服务端产物音频")
    sp.add_argument("path", help="/file/tmp/xxx.wav 或完整 URL")
    sp.add_argument("-o", "--output", required=True)
    _add_common(sp)
    sp.set_defaults(func=cmd_download)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except Qwen3TTSError as exc:
        _emit_error(exc, getattr(args, "pretty", False))
        return 1
    except KeyboardInterrupt:
        print('{"ok": false, "error": {"type": "interrupted", "message": "Ctrl-C"}}')
        return 130
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
