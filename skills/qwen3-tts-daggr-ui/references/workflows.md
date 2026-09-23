# 面向用户任务的调用流程

日常执行请用 `scripts/qwen3tts.py` 的对应子命令；本文解释每个流程内部做了什么、
以及为什么必须这么组合，用于排查与扩展。

## 通用前置：一次 `doctor`

```
python scripts/qwen3tts.py doctor
```

内部依次确认：依赖 `websockets` 已装 → Space `stage == RUNNING` → 节点图可取且
含四个算子。任一项失败就退出码 1。**在任何任务开始前跑一次**，比逐个命令试错
便宜得多——Space 休眠或重启时，后面所有命令都会以各种"看起来像参数错"的形式
失败。

## 流程 1：声音克隆（用参考音频说新文本）

```
python scripts/qwen3tts.py clone <参考音频> -t "<目标文本>" -o out.wav --xvector true
```

内部：
1. 取节点图 → 校验 `Voice Clone` 存在（未知节点服务端静默不响应，不校验会挂到超时）。
2. 本地强制必填：`ref_audio`、`target_text`。
3. `ref_audio` 是 audio 端口 → 本地文件编码成 data URL。
4. 发 run → 循环等到 `node_complete`（期间服务端不推任何进度帧，空窗正常）。
5. 读 `status`；`Success` 才继续（业务失败也走 node_complete）。
6. 有 `-o` 时用产物路径下载，先校验正文魔数再落盘。

**模式选择**：
- `--xvector true`：只取说话人向量。参考音频 3~10 秒即可，`ref_text` 可留空，
  更快。
- `--xvector false`（默认）：完整 ICL。需要 `ref_text` 尽量接近参考音频的逐字稿，
  韵律更贴近原音，约慢一倍（同负载实测 13.7s vs 24.3s）。

## 流程 2：预置音色合成

```
python scripts/qwen3tts.py say -t "<文本>" --speaker Serena -o out.wav
```

内部同流程 1，只是算子换成 `Custom Voice`，必填只有 `text`，`speaker` 是闭合枚举
（9 个），客户端提前比对拼写。`--instruct` 是风格指令（默认 `Neutral`）。

## 流程 3：音色设计（无参考音频）

```
python scripts/qwen3tts.py design -t "<文本>" -d "<音色描述>" -o out.wav
```

必填 `text` + `voice_description`。描述用英文效果更稳。

## 流程 4：音频转写

```
python scripts/qwen3tts.py asr <音频文件>
```

算子 `Qwen3 ASR`，必填 `audio_upload`。产物是文本不是音频：读 `text` 字段
（`transcription`），`outputs.detected_lang` 给出检测到的语种。不传 `-o`。

## 流程 5：下载产物（重取、或另存到别处）

```
MSYS_NO_PATHCONV=1 python scripts/qwen3tts.py download /file/tmp/<uuid>.wav -o a.wav
```

产物路径可直接用完整 URL，也可去前导斜杠，客户端三种都能归一化。
Git Bash 会把 `/file/...` 改写成 Windows 路径，用 `MSYS_NO_PATHCONV=1` 规避。

## 流程 6：未被便捷子命令覆盖的组合

```
python scripts/qwen3tts.py run "<算子名>" --inputs '{"text":"...","speaker":"Vivian"}' -o out.wav
```

键可写端口短名或完整 `<node_id>__<port>`。通用入口**不做必填校验**（调用方已
显式列出端口），要严格校验就用具体子命令。

## 多步骤与重试原则

- **绝不重试 run**：一次 run 就是一次完整 GPU 推理，重试等于双倍耗时和双倍占用。
  只有"建连 + 取图"阶段才重试（`connect_retries`，默认 2 次，指数退避）。
- **推理成功但下载失败时，重下而不是重跑**：客户端把 `RunResult` 挂在
  `TransportError.result` 上，可按 `exc.result.audio` 直接重下。
- **长文本要调大 `--timeout`**：默认 600s。耗时约等于 ~35s 固定开销 +
  ~0.37s/中文字，600s 大约撑 1500 字；更长要显式调大。
- **取消**：知道 `run_id` 时可 `client.cancel(node_name, run_id)`；CLI 未暴露
  该命令，用 Python API。
- **不要偷偷做额外动作**：脚本只做命令要求的那一次 run，不自动重试、不自动
  换参数、不自动发布/持久化。

## 副作用声明

- 所有推理操作都会把输入音频/文本上传到**公开共享**的 Space，并在共享 T4 实例
  上推理。产物是公开可猜的 UUID 下载链接。
- 本 Space 不存在删除 / 发布 / 支付 / 修改他人数据的接口，四个算子都是
  "输入 → 产物"的纯计算。
- 唯一有"持久"意味的是前端的 `set_sheet`（绑定 HF token 后保存结果），
  客户端不调用它，也不提供对应命令。

## 耗时参考（T4-medium，含排队）

| 任务 | 实测耗时 |
|---|---|
| Custom Voice（短句） | 6~9 s |
| Voice Clone x-vector（短句） | 9~43 s |
| Voice Clone 完整 ICL（短句） | 10~32 s（约为 x-vector 的 2 倍） |
| Voice Design | 15~18 s |
| Qwen3 ASR | 7~10 s |
| Voice Clone x-vector，412 字中文 | 188 s → 73.5 s 音频 |
