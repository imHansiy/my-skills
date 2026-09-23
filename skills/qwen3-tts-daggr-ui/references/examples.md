# 请求与响应示例（已脱敏）

全部示例不含任何 token / cookie / 账号：该 Space 匿名可用，`hf_token` 恒为 `null`。
`<SESSION_ID>`、`<RUN_ID>`、`<UUID>` 为占位符。

## 1. 取节点图

发送：

```json
{"action": "get_graph", "hf_token": null}
```

收到（节选，只保留结构关键部分）：

```json
{
  "type": "graph",
  "data": {
    "nodes": [
      {
        "id": "Voice_Clone__ref_audio",
        "name": "Voice_Clone__ref_audio",
        "type": "INPUT",
        "is_input_node": true,
        "input_components": [
          {
            "port_name": "value",
            "component": "audio",
            "props": {"label": "Reference Audio (Voice Clone)"},
            "value": null
          }
        ]
      },
      {
        "id": "Voice_Clone",
        "name": "Voice Clone",
        "type": "FN",
        "input_components": [],
        "inputs": [{"name": "ref_audio"}, {"name": "ref_text"}],
        "outputs": ["cloned_audio", "status"]
      }
    ],
    "edges": [
      {"from_node": "Voice_Clone__ref_audio", "to_node": "Voice_Clone", "to_port": "ref_audio"}
    ]
  }
}
```

注意 `Voice_Clone` 的 `input_components` 是空数组——端口类型只能靠 `edges` 回填。

## 2. 执行 Voice Clone（x-vector 模式）

发送（音频已编码为 data URL，此处截断）：

```json
{
  "action": "run",
  "node_name": "Voice Clone",
  "inputs": {
    "Voice_Clone__ref_audio": {"value": "data:audio/wav;base64,UklGRiQ..."},
    "Voice_Clone__ref_text": {"value": ""},
    "Voice_Clone__target_text": {"value": "这是用参考音频克隆出来的声音。"},
    "Voice_Clone__language": {"value": "Chinese"},
    "Voice_Clone__use_xvector_only": {"value": true},
    "Voice_Clone__model_size": {"value": "1.7B"}
  },
  "item_list_values": {},
  "selected_results": {},
  "run_id": "<RUN_ID>",
  "sheet_id": null,
  "hf_token": null,
  "run_ancestors": true
}
```

事件流：

```json
{"type": "node_started", "node": "Voice Clone", "run_id": "<RUN_ID>"}
```

（此处可能有几十秒到几分钟完全无消息——正常，不是断连）

```json
{
  "type": "node_complete",
  "completed_node": "Voice Clone",
  "run_id": "<RUN_ID>",
  "execution_time_ms": 13689.4,
  "nodes": [
    {
      "name": "Voice Clone",
      "output_components": [
        {"port_name": "cloned_audio", "value": "/file/tmp/<UUID>.wav"},
        {"port_name": "status", "value": "Success"}
      ]
    }
  ]
}
```

CLI 侧对应输出：

```
$ python scripts/qwen3tts.py clone ref.wav -t "这是声音克隆的验证结果。" \
    --xvector true --language Chinese -o v_clone.wav
{"ok": true, "node": "Voice Clone", "status": "Success",
 "audio": "/file/tmp/<UUID>.wav", "text": null, "saved_to": "v_clone.wav",
 "execution_time_ms": 9297.8, "run_id": "<RUN_ID>",
 "outputs": {"cloned_audio": "/file/tmp/<UUID>.wav", "status": "Success"}}
```

## 3. 执行 Voice Design（音色设计）

不需要参考音频，`voice_description` 用自然语言描述音色与情绪：

```json
{
  "action": "run",
  "node_name": "Voice Design",
  "inputs": {
    "Voice_Design__text": {"value": "音色设计验证成功，这是全新生成的声音。"},
    "Voice_Design__language": {"value": "Chinese"},
    "Voice_Design__voice_description": {"value": "warm young female voice, gentle and clear, medium pitch"}
  },
  "item_list_values": {},
  "selected_results": {},
  "run_id": "<RUN_ID>",
  "sheet_id": null,
  "hf_token": null,
  "run_ancestors": true
}
```

产物端口是 `generated_audio`（不是 `cloned_audio`/`tts_audio`）：

```
$ python scripts/qwen3tts.py design -t "音色设计验证成功，这是全新生成的声音。" \
    -d "warm young female voice, gentle and clear, medium pitch" \
    --language Chinese -o v_design.wav
{"ok": true, "node": "Voice Design", "status": "Success",
 "audio": "/file/tmp/<UUID>.wav", "text": null, "saved_to": "v_design.wav",
 "execution_time_ms": 11688.6, "run_id": "<RUN_ID>",
 "outputs": {"generated_audio": "/file/tmp/<UUID>.wav", "status": "Success"}}
```

`schema "Voice Design"` 实测的端口默认值（说明这两个端口服务端自带兜底值，
漏传不会报错但结果不是你要的，所以客户端本地强制必填）：

| port | default |
|---|---|
| `text` | `It's in the top drawer... wait, it's empty? No way!` |
| `voice_description` | `Speak in an incredulous tone, but with a hint of panic.` |

## 4. 业务失败（同样是 node_complete）

```json
{"port_name": "status", "value": "Error: Unsupported speakers: ['Nobody']"}
```

没有 `error` 事件，退出码也不由协议给出——调用方必须自己判 `status`。

## 5. 取消

```json
{"action": "cancel", "node_name": "Voice Clone", "run_id": "<RUN_ID>"}
```

## 6. 下载产物

```
GET https://prithivmlmods-qwen3-tts-daggr-ui.hf.space/file/tmp/<UUID>.wav
```

200，正文以 `RIFF` 开头，`Content-Type` 可能是 `audio/x-wav` 或
`application/octet-stream`。产物规格：24000 Hz / 单声道 / 16-bit PCM。

## 7. CLI 侧的成功输出（供对照）

```
$ python scripts/qwen3tts.py say -t "hello" --speaker Serena -o out.wav
{"ok": true, "node": "Custom Voice", "status": "Success",
 "audio": "/file/tmp/<UUID>.wav", "text": null, "saved_to": "out.wav",
 "execution_time_ms": 7836.8, "run_id": "<RUN_ID>",
 "outputs": {"tts_audio": "/file/tmp/<UUID>.wav", "status": "Success"}}
```

ASR 成功输出（产物是文本）：

```
$ python scripts/qwen3tts.py asr in.wav
{"ok": true, "node": "Qwen3 ASR", "status": "Success", "audio": null,
 "text": "脚本验证。", "saved_to": null, "execution_time_ms": 7309.2,
 "run_id": "<RUN_ID>",
 "outputs": {"detected_lang": "Chinese", "transcription": "脚本验证。",
             "status": "Success"}}
```

失败：

```
$ python scripts/qwen3tts.py say -t "hi" --speaker Nobody
{"ok": false, "error": {"type": "invalid_input",
 "message": "speaker='Nobody' 不在可选值内：Aiden, Dylan, Eric, ..."}}
```

## 8. doctor 输出

```
$ python scripts/qwen3tts.py doctor
{"ok": true, "checks": {
  "websockets": {"ok": true, "version": "17.0.1"},
  "space": {"ok": true, "stage": "RUNNING", "hardware": "t4-medium", "error": null},
  "graph": {"ok": true, "operators": ["Voice Design", "Custom Voice",
                                      "Voice Clone", "Qwen3 ASR"]}},
 "host": "prithivmlmods-qwen3-tts-daggr-ui.hf.space"}
```
