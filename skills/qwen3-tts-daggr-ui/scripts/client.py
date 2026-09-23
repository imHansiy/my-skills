"""Qwen3-TTS-Daggr-UI Space 的统一客户端（Skill 执行层）。

HuggingFace Space ``prithivMLmods/Qwen3-TTS-Daggr-UI`` 不是 Gradio：推理走一条
自定义 WebSocket 节点图协议（前端叫 daggr）。本模块把建连、取图、参数校验、
执行、产物下载封装成稳定调用，供 ``scripts/qwen3tts.py`` 的 CLI 使用。

依赖：``websockets>=12``（见 scripts/requirements.txt）。

通信模型（逐条实测，完整细节见 references/protocol.md）：

1. 连 ``wss://<host>/ws/<session_id>``，session_id 形如 ``session_<random>``。
2. 发 ``{"action":"get_graph"}`` → 回 ``type:"graph"``，含 INPUT 参数节点与
   FN 可执行算子节点。
3. 发 ``{"action":"run","node_name":...,"inputs":{"<node_id>__<port>":{"value":...}},
   "run_id":...,"run_ancestors":true}`` → 事件流 node_started → node_complete。
4. 产物是服务端路径 ``/file/tmp/<uuid>.wav``，普通 HTTPS GET 下载（免鉴权）。

实测结论（决定了下面的设计）：

* **未知节点名会被静默忽略**——服务端不回任何消息，只能挂到超时。所以本地必须
  先用节点图校验 node_name。
* 参数校验**不在服务端做**：漏传 text 仍返回 ``status:"Success"`` 并给出可下载的
  wav（算子自带默认值）。少参的唯一后果是"产出的音频不是你想要的"，因此必填项
  只能在本地拦截。
* 音频输入走 **data URL**（``data:audio/wav;base64,...``），与前端
  FileReader.readAsDataURL 同形；服务端自己的 /file/ 路径不接受作输入。
* **推理期间服务端不推任何进度帧**，只在开始和结束各推一条。等待逻辑必须循环到
  真正的 deadline，否则长任务会被误判超时（45s 空窗曾被当成整体超时）。
* 产物路径写错时可能回 200 + SPA HTML，必须先校验正文魔数再落盘。
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union
from urllib.parse import urlsplit

from daggr import (
    DEFAULT_HOST,
    NODE_CUSTOM_VOICE,
    NODE_QWEN3_ASR,
    NODE_VOICE_CLONE,
    NODE_VOICE_DESIGN,
    REQUIRED_PORTS,
    NodeInfo,
    NodePort,
    RecvTimeout,
    RunResult,
    as_bool,
    encode_audio,
    extract_choices,
    is_blank,
    looks_like_audio,
    normalize_space_name,
    session_id,
    to_result,
)
from exceptions import (
    GraphError,
    InputError,
    NodeNotFoundError,
    RunFailedError,
    RunTimeoutError,
    TransportError,
)

EventCallback = Callable[[Dict[str, Any]], None]


class Qwen3TTSClient:
    """Qwen3-TTS Daggr Space 客户端。

    典型用法::

        with Qwen3TTSClient() as c:
            res = c.voice_clone("ref.wav", "参考音频说的话", "要合成的目标文本",
                                save_to="out.wav")
            print(res.ok, res.saved_to)
    """

    def __init__(
        self,
        host: Optional[str] = None,
        *,
        hf_token: Optional[str] = None,
        run_timeout: float = 600.0,
        connect_timeout: float = 30.0,
        connect_retries: int = 2,
        scheme: str = "wss",
    ) -> None:
        """
        Args:
            host: Space 主机名（不含协议）或完整 URL。省略时取环境变量
                ``QWEN3_TTS_HOST``，再回落到 DEFAULT_HOST。
            hf_token: 可选 HF token，省略时取环境变量 ``QWEN3_TTS_HF_TOKEN``。
                本 Space 匿名可用；token 仅按前端行为在消息里透传，
                不落盘、不打印、不出现在任何输出里。
            run_timeout: 单次 ``run`` 等待 ``node_complete`` 的总时限（秒）。
                默认 600s。耗时随文本长度显著增长：短文本 6~40s，
                412 字中文克隆实测 188s，长文本需相应调大。
            connect_timeout: WebSocket 建连超时。
            connect_retries: 仅对「建连 + 取图」阶段重试，绝不会重发 run，
                避免重复触发 GPU 推理。
            scheme: ``wss`` 或 ``ws``。
        """
        host = (host or os.environ.get("QWEN3_TTS_HOST") or DEFAULT_HOST).strip()
        if hf_token is None:
            hf_token = os.environ.get("QWEN3_TTS_HF_TOKEN") or None
        if "://" in host:
            # 允许直接传 URL（scheme 大小写不敏感），拆出 scheme 与 host
            parsed = urlsplit(host)
            scheme = "ws" if parsed.scheme.lower() in ("http", "ws") else "wss"
            host = parsed.netloc or parsed.path
        host = host.rstrip("/")
        if not host:
            raise InputError("host 不能为空")
        self.host = host
        self.scheme = scheme
        self.hf_token = hf_token
        self.run_timeout = run_timeout
        self.connect_timeout = connect_timeout
        self.connect_retries = max(0, int(connect_retries))
        self._graph: Optional[Dict[str, Any]] = None

    # ------------------------------------------------------------------
    # 上下文管理
    # ------------------------------------------------------------------
    def __enter__(self) -> "Qwen3TTSClient":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        """释放缓存的节点图。连接是短连接，随 run 结束即关闭。"""
        self._graph = None

    @property
    def base_url(self) -> str:
        """HTTP(S) 基地址，用于下载产物音频（不含尾斜杠，便于安全拼接路径）。"""
        host = self.host.rstrip("/")
        return f"https://{host}" if self.scheme == "wss" else f"http://{host}"

    # ------------------------------------------------------------------
    # WebSocket 基础收发
    # ------------------------------------------------------------------
    def _connect(self, session: Optional[str] = None):
        """建立一条 WebSocket。延迟导入 websockets，便于无依赖时给出清晰报错。"""
        try:
            from websockets.sync.client import connect
        except ImportError as exc:  # pragma: no cover - 环境缺依赖时
            raise TransportError(
                "缺少 websockets 依赖，请执行：pip install 'websockets>=12'"
            ) from exc

        sid = session or session_id()
        url = f"{self.scheme}://{self.host}/ws/{sid}"
        try:
            ws = connect(url, open_timeout=self.connect_timeout, max_size=None)
        except Exception as exc:  # websockets 的异常类型较杂，统一归类
            raise TransportError(f"连接 {url} 失败：{type(exc).__name__}: {exc}") from exc
        return ws

    @staticmethod
    def _recv(ws, timeout: float) -> Dict[str, Any]:
        """收一条 JSON 消息。

        超时抛出 :class:`RecvTimeout`（内部类型）：等待推理时「一个 recv 窗口
        没消息」不等于「整体超时」，调用方要据此决定是继续等还是放弃；只有
        取图这种一次性等待才需要换算成 :class:`RunTimeoutError`。
        """
        try:
            raw = ws.recv(timeout=timeout)
        except TimeoutError as exc:
            raise RecvTimeout("等待服务端消息超时") from exc
        except Exception as exc:
            raise TransportError(f"接收消息失败：{type(exc).__name__}: {exc}") from exc
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            raise TransportError(f"服务端返回的不是合法 JSON：{str(raw)[:200]}") from exc

    def _send(self, ws, payload: Mapping[str, Any]) -> None:
        try:
            ws.send(json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            raise TransportError(f"发送消息失败：{type(exc).__name__}: {exc}") from exc

    # ------------------------------------------------------------------
    # 节点图
    # ------------------------------------------------------------------
    def graph(self, *, refresh: bool = False) -> Dict[str, Any]:
        """取工作流节点图（默认缓存）。

        Space 处于 Building/Sleeping 时这里会失败，是最常见的首因，
        因此把 ``connect_retries`` 的重试放在这一段。
        """
        if self._graph is not None and not refresh:
            return self._graph

        last: Optional[Exception] = None
        for attempt in range(self.connect_retries + 1):
            try:
                self._graph = self._fetch_graph()
                return self._graph
            except (TransportError, GraphError) as exc:
                last = exc
                if attempt < self.connect_retries:
                    time.sleep(1.5 * (attempt + 1))
        raise GraphError(
            f"获取节点图失败（已尝试 {self.connect_retries + 1} 次）：{last}"
        ) from last

    def _fetch_graph(self) -> Dict[str, Any]:
        ws = self._connect()
        try:
            self._send(ws, {"action": "get_graph", "hf_token": self.hf_token})
            try:
                msg = self._recv(ws, self.connect_timeout)
            except RecvTimeout as exc:
                # 取图是一次性等待，这里空等就是真的拿不到图（Space 未就绪）。
                raise RunTimeoutError(
                    f"获取节点图超时（{self.connect_timeout}s）；Space 可能正在冷启动"
                ) from exc
        finally:
            try:
                ws.close()
            except Exception:
                pass

        if msg.get("type") != "graph":
            raise GraphError(
                f"期望 graph 消息，收到：{json.dumps(msg, ensure_ascii=False)[:300]}"
            )
        data = msg.get("data") or {}
        if not isinstance(data, dict) or "nodes" not in data:
            raise GraphError("graph 消息缺少 nodes 字段")
        return data

    def nodes(self, *, refresh: bool = False) -> List[NodeInfo]:
        """列出全部节点（含 INPUT 参数节点）。

        节点图里两类节点的字段形状不同，必须分别解析：

        * ``INPUT`` 节点（如 ``Voice_Clone__ref_audio``）把元数据放在
          ``input_components[0]``：有 ``component``（audio/textbox/dropdown/
          checkbox）、``props.label``、``props.choices``。
        * ``FN`` 算子节点（如 ``Voice_Clone``）的 ``input_components`` 是**空的**，
          端口只以 ``inputs: [{"name": "ref_audio"}]`` 这种纯名字出现，``outputs``
          则是名字字符串数组。

        因此 FN 端口的类型信息只能靠 ``edges`` 回填：边记录了
        ``Voice_Clone__ref_audio:value → Voice_Clone:ref_audio`` 的映射。
        不回填的后果不是"少个标签"，而是音频端口拿不到 ``component="audio"``，
        本地文件路径不会被编码成 data URL，直接发给服务端会报
        ``Could not process reference audio``。
        """
        data = self.graph(refresh=refresh)
        raw_nodes = data.get("nodes") or []

        # INPUT 全名 → 该端口的类型元数据（FN 端口从这里借信息）
        input_meta: Dict[str, Dict[str, Any]] = {}
        for raw in raw_nodes:
            if raw.get("type") != "INPUT":
                continue
            comps = raw.get("input_components") or []
            if not comps:
                continue
            comp = comps[0]
            props = comp.get("props") or {}
            input_meta[raw.get("id") or raw.get("name", "")] = {
                "component": comp.get("component") or comp.get("type") or "",
                "label": props.get("label"),
                "value": comp.get("value"),
                "choices": extract_choices(comp),
            }

        # (FN 节点 id, FN 端口名) → 上游 INPUT 全名
        incoming: Dict[tuple, str] = {}
        for edge in data.get("edges") or []:
            src = edge.get("from_node")
            dst_node = edge.get("to_node")
            dst_port = edge.get("to_port")
            if src and dst_node and dst_port:
                incoming[(dst_node, dst_port)] = src

        out: List[NodeInfo] = []
        for raw in raw_nodes:
            node_id = raw.get("id") or raw.get("name", "")
            comps = raw.get("input_components") or []

            if comps:
                # INPUT 节点：元数据自带
                ports = [
                    NodePort(
                        port_name=c.get("port_name", ""),
                        component=c.get("component") or c.get("type") or "",
                        label=(c.get("props") or {}).get("label"),
                        value=c.get("value"),
                        choices=extract_choices(c),
                        node_id=node_id,
                    )
                    for c in comps
                ]
            else:
                # FN 节点：端口只有名字，类型与可选值靠边回填
                ports = []
                for spec in raw.get("inputs") or []:
                    port_name = spec if isinstance(spec, str) else spec.get("name", "")
                    meta = input_meta.get(incoming.get((node_id, port_name), "")) or {}
                    ports.append(
                        NodePort(
                            port_name=port_name,
                            component=meta.get("component", ""),
                            label=meta.get("label"),
                            value=meta.get("value"),
                            choices=meta.get("choices"),
                            node_id=node_id,
                        )
                    )

            out_comps = raw.get("output_components") or []
            if out_comps:
                outs = [
                    NodePort(
                        port_name=c.get("port_name", ""),
                        component=c.get("component") or c.get("type") or "",
                        label=(c.get("props") or {}).get("label"),
                        value=c.get("value"),
                        node_id=node_id,
                    )
                    for c in out_comps
                ]
            else:
                outs = [
                    NodePort(port_name=str(p), node_id=node_id)
                    for p in raw.get("outputs") or []
                ]

            out.append(
                NodeInfo(
                    name=raw.get("name", ""),
                    node_id=node_id,
                    type=raw.get("type", ""),
                    is_input_node=bool(raw.get("is_input_node")),
                    inputs=ports,
                    outputs=outs,
                )
            )
        return out

    def runnable_nodes(self, *, refresh: bool = False) -> List[NodeInfo]:
        """只返回可执行的算子节点。"""
        return [n for n in self.nodes(refresh=refresh) if n.runnable]

    def node(self, name: str, *, refresh: bool = False) -> NodeInfo:
        """按名字取节点，名字需精确匹配（区分大小写）。"""
        for n in self.nodes(refresh=refresh):
            if n.name == name:
                return n
        available = ", ".join(n.name for n in self.runnable_nodes(refresh=refresh))
        raise NodeNotFoundError(f"节点不存在：{name!r}。可用算子：{available}")

    def describe(self, name: str, *, refresh: bool = False) -> Dict[str, Any]:
        """给出某个算子的完整参数说明，供人或 AI 决定怎么调用。"""
        node = self.node(name, refresh=refresh)
        return {
            "node": node.name,
            "node_id": node.node_id,
            "type": node.type,
            "runnable": node.runnable,
            "inputs": [
                {
                    "port": p.port_name,
                    "key": p.qualified,
                    "component": p.component,
                    "label": p.label,
                    "default": p.value,
                    "choices": p.choices,
                    "required": p.value is None,
                }
                for p in node.inputs
            ],
            "outputs": [{"port": p.port_name, "component": p.component} for p in node.outputs],
        }

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def run(
        self,
        node_name: str,
        inputs: Mapping[str, Any],
        *,
        on_event: Optional[EventCallback] = None,
        timeout: Optional[float] = None,
        run_id: Optional[str] = None,
        save_to: Optional[Union[str, Path]] = None,
        strict: bool = True,
        require: Optional[Sequence[str]] = None,
    ) -> RunResult:
        """执行一个算子并等待结果。

        Args:
            node_name: 算子名，须存在于节点图（不存在会立刻报错，
                因为服务端对未知节点名不响应）。
            inputs: 输入。键可写完整形式 ``Custom_Voice__text``，
                也可写短名 ``text``（会自动补全为 ``<node_id>__<port>``）。
                音频端口的值可传本地文件路径（自动编码为 data URL）。
            on_event: 收到每条服务端消息时回调，可用于打印进度。
            timeout: 覆盖默认 ``run_timeout``。
            run_id: 自定义运行 ID，用于取消。
            save_to: 若给出，成功后自动下载产物音频到该路径。
            strict: 为 True 时业务失败抛 ``RunFailedError``；为 False 时
                返回 ``RunResult`` 由调用方自行检查 ``ok``。
            require: 必填端口名。默认取 ``REQUIRED_PORTS`` 里该算子的
                条目；传 ``[]`` 可关闭校验。

        Returns:
            RunResult
        """
        node = self.node(node_name)
        if not node.runnable:
            raise NodeNotFoundError(
                f"{node_name!r} 是参数节点（type={node.type}），不能直接执行；"
                f"请执行算子：{', '.join(n.name for n in self.runnable_nodes())}"
            )
        required = REQUIRED_PORTS.get(node.name, ()) if require is None else require
        resolved = self._resolve_inputs(node, inputs, require=required)

        rid = run_id or f"run_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
        deadline = time.monotonic() + (timeout if timeout is not None else self.run_timeout)

        ws = self._connect()
        try:
            self._send(
                ws,
                {
                    "action": "run",
                    "node_name": node.name,
                    "inputs": resolved,
                    "item_list_values": {},
                    "selected_results": {},
                    "run_id": rid,
                    "sheet_id": None,
                    "hf_token": self.hf_token,
                    "run_ancestors": True,
                },
            )
            result = self._await_result(ws, node, rid, deadline, on_event)
        finally:
            try:
                ws.close()
            except Exception:
                pass

        if save_to and result.audio:
            try:
                result.saved_to = str(self.download(result.audio, save_to))
            except TransportError as exc:
                # 推理已经跑完（GPU 已消耗），只是取件失败：把结果挂到异常上，
                # 调用方可以按 exc.result.audio 直接重下，不必重跑一次推理。
                exc.result = result
                raise
        if strict and not result.ok:
            raise RunFailedError(
                f"{node.name} 执行失败：{result.status}",
                node=node.name,
                status=result.status,
            )
        return result

    def _await_result(
        self,
        ws,
        node: NodeInfo,
        run_id: str,
        deadline: float,
        on_event: Optional[EventCallback],
    ) -> RunResult:
        """循环收消息，直到拿到本节点的 node_complete 或 error。"""
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RunTimeoutError(
                    f"等待 {node.name} 完成超时（run_id={run_id}）。"
                    "常见原因：Space 正在冷启动/排队，或输入音频过长。"
                )
            try:
                msg = self._recv(ws, min(remaining, 45.0))
            except RecvTimeout:
                # 单个窗口空等不等于超时：服务端只在开始/结束时推消息，
                # 长文本合成期间可能几十秒没有任何帧。回到循环顶部重新算
                # remaining，直到真正耗尽 run_timeout 才报超时。
                continue
            if on_event:
                try:
                    on_event(msg)
                except Exception:
                    # 回调失败不应影响主流程
                    pass

            mtype = msg.get("type")
            if mtype == "node_complete":
                # 只有本节点的完成事件才代表本次 run 结束
                if msg.get("completed_node") == node.name:
                    return to_result(msg, node)
            elif mtype == "error":
                failed = msg.get("node") or msg.get("completed_node")
                if failed in (None, node.name):
                    raise RunFailedError(
                        f"{node.name} 执行出错：{msg.get('error')}", node=node.name
                    )
            elif mtype == "cancelled":
                raise RunFailedError(f"{node.name} 已被取消", node=node.name)
            elif mtype == "graph":
                # 服务端可能主动推送图更新（如 HF token 变更），忽略即可
                continue

    def cancel(self, node_name: str, run_id: str) -> None:
        """请求取消一个进行中的运行。"""
        ws = self._connect()
        try:
            self._send(ws, {"action": "cancel", "node_name": node_name, "run_id": run_id})
            time.sleep(0.2)
        finally:
            try:
                ws.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 输入解析
    # ------------------------------------------------------------------
    def _resolve_inputs(
        self,
        node: NodeInfo,
        inputs: Mapping[str, Any],
        *,
        require: Sequence[str] = (),
    ) -> Dict[str, Any]:
        """把用户给的输入对齐成服务端要的 ``{<node_id>__<port>: {"value": ...}}``。

        服务端**不校验键名**：写错端口名不报错，该参数只是取默认值，表现为
        "参数没生效"。所以本地严格校验，宁可早失败。

        Args:
            require: 必须显式给出的端口名。服务端对漏传的必填项同样不报错
                （实测漏传 ``text`` 仍回 ``Success`` 并产出音频），因此
                "哪些参数不能少"只能由调用方声明，在这里统一拦截。
        """
        ports = {p.port_name: p for p in node.inputs}
        out: Dict[str, Any] = {}
        unknown: List[str] = []

        for key, value in (inputs or {}).items():
            port_name = self._match_port(key, node, ports)
            if port_name is None:
                unknown.append(key)
                continue
            port = ports[port_name]
            out[port.qualified] = {"value": self._coerce(port, value)}

        if unknown:
            raise InputError(
                f"{node.name} 不认识这些输入：{', '.join(map(repr, unknown))}。"
                f"可用端口：{', '.join(sorted(ports)) or '(无)'}"
            )

        missing = [
            name
            for name in require
            if name in ports
            and is_blank((out.get(ports[name].qualified) or {}).get("value"))
        ]
        if missing:
            raise InputError(
                f"{node.name} 缺少必填参数：{', '.join(missing)}。"
                f"完整端口：{', '.join(sorted(ports)) or '(无)'}"
            )
        return out

    @staticmethod
    def _match_port(key: str, node: NodeInfo, ports: Mapping[str, NodePort]) -> Optional[str]:
        """把用户写的键名解析成端口名。

        接受两种写法：完整键 ``Voice_Clone__ref_audio`` 与短名 ``ref_audio``。

        带前缀时前缀必须**正好**是本节点 id。若写成别的节点前缀（如把
        ``Voice_Design__text`` 传给 Voice Clone），返回 None 让上层报错——
        放任它按短名匹配会变成"参数静默生效到错误的地方"。
        """
        if "__" in key:
            prefix, _, port = key.partition("__")
            if prefix != node.node_id:
                return None
            return port if port in ports else None
        return key if key in ports else None

    def _coerce(self, port: NodePort, value: Any) -> Any:
        """按端口控件类型规整取值，尽量在本地把能发现的错误拦下来。

        各类型的处理理由：

        * ``audio``：本地文件路径 → data URL（前端 ``FileReader.readAsDataURL``
          的形状）；``data:`` 与 ``http(s):`` 原样透传。
        * ``checkbox``：CLI / JSON 传进来的是 ``"true"`` / ``"1"`` 这类字符串，
          直接发会被服务端当成真值，必须转成 bool。
        * ``dropdown``：可选值是闭合集合，提前比对能立刻指出拼写错误，
          而不是等一次完整 GPU 推理后才发现音色没生效。
        """
        if port.component == "audio":
            if isinstance(value, (str, Path)):
                text = str(value)
                if text.startswith("data:"):
                    return text
                if text.startswith("/file/"):
                    # 实测服务端不接受自己的产物路径作输入，会回
                    # "Could not process reference audio"。
                    raise InputError(
                        f"音频端口 {port.port_name} 不接受服务端路径 {text!r}，"
                        "请先下载为本地文件再传入"
                    )
                if text.startswith(("http://", "https://")):
                    return text
                p = Path(text)
                if p.is_file():
                    return encode_audio(p)
        elif port.component == "checkbox":
            return as_bool(value)
        elif port.component == "dropdown" and port.choices and isinstance(value, str):
            if value not in port.choices:
                raise InputError(
                    f"{port.port_name}={value!r} 不在可选值内：{', '.join(port.choices)}"
                )
        return value

    # ------------------------------------------------------------------
    # 产物下载
    # ------------------------------------------------------------------
    def download(self, server_path: str, dest: Union[str, Path]) -> Path:
        """把 ``/file/tmp/xxx.wav`` 这类服务端路径下载到本地。"""
        import urllib.error
        import urllib.request

        if not server_path:
            raise InputError("server_path 为空")
        if urlsplit(server_path).scheme.lower() in ("http", "https"):
            url = server_path
        else:
            # 调用方可能传 "file/tmp/a.wav"（无前导斜杠，常用于绕开 Git Bash 的
            # 路径改写），直接相加会拼成 "https://hostfile/tmp/a.wav"，必须补斜杠。
            url = self.base_url + "/" + server_path.lstrip("/")
        out = Path(dest)
        try:
            if out.parent and not out.parent.exists():
                out.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise TransportError(f"无法创建目录 {out.parent}：{exc}") from exc
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                body = resp.read()
        except urllib.error.HTTPError as exc:
            raise TransportError(f"下载失败 HTTP {exc.code}：{url}") from exc
        except Exception as exc:
            raise TransportError(f"下载失败：{type(exc).__name__}: {exc}") from exc
        if not body:
            raise TransportError(f"下载到的内容为空：{url}")
        # 产物路径写错时服务端可能回 200 + 前端页面而非 404，只判断"内容非空"
        # 会把 HTML/JSON 当音频写盘并回报成功。这里要求正文以音频魔数开头；
        # Content-Type 仅用于报错信息——实测同一份 wav 会返回 audio/x-wav
        # 或 application/octet-stream，不能作为准入条件。
        if not looks_like_audio(body):
            raise TransportError(
                f"下载到的不是音频（Content-Type={ctype or '未知'}）：{url}；"
                "请确认路径取自 node_complete 的音频输出"
            )
        try:
            out.write_bytes(body)
        except OSError as exc:
            raise TransportError(f"写入 {out} 失败：{exc}") from exc
        return out

    # ------------------------------------------------------------------
    # 便捷方法：四个算子各一个
    # ------------------------------------------------------------------
    def voice_clone(
        self,
        ref_audio: Union[str, Path],
        ref_text: str,
        target_text: str,
        *,
        language: str = "Auto",
        use_xvector_only: bool = False,
        model_size: str = "1.7B",
        save_to: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> RunResult:
        """声音克隆：用参考音频 + 参考文本，合成目标文本。

        ``use_xvector_only=True`` 时只取说话人向量，不要求参考文本精确，
        参考音频短（3~10 秒）即可；为 False 时走完整 ICL 流程，效果更贴近原音。
        """
        return self.run(
            NODE_VOICE_CLONE,
            {
                "ref_audio": str(ref_audio),
                "ref_text": ref_text,
                "target_text": target_text,
                "language": language,
                "use_xvector_only": use_xvector_only,
                "model_size": model_size,
            },
            save_to=save_to,
            **kwargs,
        )

    def voice_design(
        self,
        text: str,
        voice_description: str,
        *,
        language: str = "Auto",
        save_to: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> RunResult:
        """音色设计：用自然语言描述音色与情绪，直接合成（无需参考音频）。"""
        return self.run(
            NODE_VOICE_DESIGN,
            {"text": text, "voice_description": voice_description, "language": language},
            save_to=save_to,
            **kwargs,
        )

    def custom_voice(
        self,
        text: str,
        *,
        speaker: str = "Ryan",
        language: str = "English",
        instruct: str = "Neutral",
        model_size: str = "1.7B",
        save_to: Optional[Union[str, Path]] = None,
        **kwargs: Any,
    ) -> RunResult:
        """预置音色合成：从 9 个内置说话人里选一个。"""
        return self.run(
            NODE_CUSTOM_VOICE,
            {
                "text": text,
                "language": language,
                "speaker": speaker,
                "instruct": instruct,
                "model_size": model_size,
            },
            save_to=save_to,
            **kwargs,
        )

    def transcribe(
        self,
        audio: Union[str, Path],
        *,
        language: str = "Auto",
        **kwargs: Any,
    ) -> RunResult:
        """Qwen3 ASR：转写音频，输出语种与文本。"""
        return self.run(
            NODE_QWEN3_ASR,
            {"audio_upload": str(audio), "lang_disp": language},
            **kwargs,
        )

    # ------------------------------------------------------------------
    # 运行环境自检
    # ------------------------------------------------------------------
    def space_status(self, *, repo: Optional[str] = None) -> Dict[str, Any]:
        """查询 Space 运行状态。

        ``run`` 卡住时先看这里：``stage`` 不是 ``RUNNING`` 说明容器还没起来，
        此时任何请求都会失败或极慢。

        Args:
            repo: HF 仓库 ID（``owner/name``）。默认从 ``host`` 反查。

        为什么要反查：WebSocket 用的是子域名
        ``prithivmlmods-qwen3-tts-daggr-ui.hf.space``，而 HF 状态接口要的是
        仓库 ID ``prithivMLmods/Qwen3-TTS-Daggr-UI``。两者大小写与分隔符都不同，
        无法直接还原，只能拉取候选列表后按规范化名字比对。
        """
        import urllib.parse
        import urllib.request

        api = f"https://huggingface.co/api/spaces/{repo}" if repo else None
        if api is None:
            # 用完整子域名当搜索词。HF 的 search 是模糊匹配，
            # 只需给出足够长的特征串就能命中（实测带 owner 也能命中）。
            slug = self.host.split(".")[0]
            query = urllib.parse.urlencode({"search": slug, "limit": 20})
            search_api = f"https://huggingface.co/api/spaces?{query}"
            try:
                with urllib.request.urlopen(search_api, timeout=30) as resp:
                    candidates = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                return {
                    "reachable": False,
                    "error": f"{type(exc).__name__}: {exc}",
                    "api": search_api,
                }
            for item in candidates or []:
                if normalize_space_name(item.get("id", "")) == slug:
                    repo = item.get("id")
                    break
            if repo is None:
                return {
                    "reachable": False,
                    "error": f"未在 HF 上找到与 {slug!r} 对应的 Space，请用 repo 参数指定",
                    "api": search_api,
                }
            api = f"https://huggingface.co/api/spaces/{repo}"
        try:
            with urllib.request.urlopen(api, timeout=30) as resp:
                info = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return {"reachable": False, "error": f"{type(exc).__name__}: {exc}", "api": api}
        runtime = info.get("runtime") or {}
        return {
            "reachable": True,
            "space_id": info.get("id"),
            "stage": runtime.get("stage"),
            "hardware": (runtime.get("hardware") or {}).get("current"),
            "raw": runtime,
        }
