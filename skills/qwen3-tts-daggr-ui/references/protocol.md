# 协议与端点（daggr WebSocket 节点图协议）

底层事实。日常任务请用 `scripts/qwen3tts.py`，**不要**按本文手搓请求；
本文用于排查脚本问题、扩展新操作、协议变更时维护 Skill。

## 关键判断：这不是 Gradio

`/gradio_api/info` 返回 200，但 body 是 `<!DOCTYPE html>` 首页（含 `<div id="app">`）。
`/gradio_api/*`、`/queue/join` 都只是 SPA 路由 fallback，**不是 JSON API**。
`gradio_client` 在这里完全不可用——不要浪费时间尝试。

前端是自研 SPA（内部叫 daggr），真正推理走 WebSocket。

## 端点总览

| 类型 | 端点 | 用途 | 认证 |
|---|---|---|---|
| WSS | `wss://<host>/ws/<session_id>` | 唯一的控制通道：取图 / 执行 / 取消 | 无 |
| GET | `https://<host>/file/tmp/<uuid>.wav` | 下载产物音频 | 无 |
| GET | `https://huggingface.co/api/spaces/<owner>/<name>` | 查 Space 运行状态 | 无 |

没有 REST 推理接口、没有分页、没有批量接口。

### 路径响应实测（决定下载必须校验魔数）

| 请求路径 | 响应 |
|---|---|
| `/file/tmp/<valid>.wav` | 200，音频正文 |
| `/file/tmp/nope.wav` | **404** |
| `/file/nope.wav` | **403** |
| `/nope`、`/`、`/favicon.ico` | **200 + SPA HTML** |

即"状态码 200"完全不代表拿到音频，必须校验正文魔数。

## 会话 ID

`session_id` 形状对齐前端：`session_` + `uuid4().hex[:12]`。服务端用它隔离每个
会话的图状态；每次 run 用新 session 即可，无需复用。

## 消息：`get_graph`

发送：

```json
{"action": "get_graph", "hf_token": null}
```

返回 `{"type": "graph", "data": {"nodes": [...], "edges": [...]}}`。

### 两类节点形状不同（解析时最容易错的地方）

- **INPUT 节点**（id 形如 `Voice_Clone__ref_audio`）：参数载体，**不可执行**。
  元数据在 `input_components[0]`：`component`（`audio`/`textbox`/`dropdown`/
  `checkbox`）、`props.label`、`props.choices`。
- **FN 节点**（id 形如 `Voice_Clone`）：真正的可执行算子，名字带空格
  （`Voice Clone`）。它的 `input_components` 是**空数组**，端口只以
  `inputs: [{"name": "ref_audio"}]` 这种纯名字出现，`outputs` 是名字字符串数组。

**FN 端口的类型信息只能靠 `edges` 回填**：边记录了
`Voice_Clone__ref_audio:value → Voice_Clone:ref_audio` 的映射。不回填的后果不是
"少个标签"，而是音频端口拿不到 `component="audio"`，本地文件路径不会被编码成
data URL，服务端会回 `Could not process reference audio`。

`choices` 的形状是 `[["Auto","Auto"], ...]`（label/value 对），取 value。

## 消息：`run`

```json
{
  "action": "run",
  "node_name": "Voice Clone",
  "inputs": {"Voice_Clone__ref_audio": {"value": "data:audio/wav;base64,<...>"},
             "Voice_Clone__target_text": {"value": "要合成的文本"}},
  "item_list_values": {},
  "selected_results": {},
  "run_id": "run_<millis>_<rand6>",
  "sheet_id": null,
  "hf_token": null,
  "run_ancestors": true
}
```

`inputs` 键的规则：`<FN节点id>__<端口名>`。写短名也可以（客户端会补全），
但**带前缀时前缀必须正好是本节点 id**——写成别的节点前缀会被静默丢弃。

### 事件流

`node_started` →（长时间无消息）→ `node_complete`。
`node_complete` 里 `completed_node` 字段标明是哪个节点完成；本节点的输出在
`nodes[].output_components` 里（`port_name` / `value`）。

**业务失败不会走 WebSocket 的 `error` 事件**（该事件只在服务端内部异常时出现），
`node_complete` 照样正常到达，结论全在 `status` 文本里。`error` 事件的
`node` 字段可能缺失，缺失时按"本次 run 出错"处理。

## 消息：`cancel`

```json
{"action": "cancel", "node_name": "Voice Clone", "run_id": "<run_id>"}
```

## 音频上传

音频端口的值必须是下列之一（与前端 `FileReader.readAsDataURL` 同形）：

- `data:<mime>;base64,<...>` — 本地文件由客户端编码，MIME 按扩展名映射
  （`.wav→audio/wav`、`.mp3→audio/mpeg`…），猜不出时回落 `audio/wav`。
- 已经是 `data:` 或 `http(s):` 的 URL — 原样透传。
- ❌ 服务端自己的 `/file/tmp/…` 路径**不接受**作输入，实测回
  `Could not process reference audio`。要复用产物就先下载到本地。

产物音频规格：24000 Hz / 单声道 / 16-bit PCM WAV。

## Space 状态端点

`GET https://huggingface.co/api/spaces/<owner>/<name>` → `runtime.stage`、
`runtime.hardware.current`。

子域名 `prithivmlmods-qwen3-tts-daggr-ui` 无法直接还原成仓库 ID
`prithivMLmods/Qwen3-TTS-Daggr-UI`（大小写与分隔符都不同），客户端用
`/api/spaces?search=<slug>` 拉候选后按规范化名字比对反查。
