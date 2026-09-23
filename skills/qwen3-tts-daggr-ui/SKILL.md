---
name: qwen3-tts-daggr-ui
description: >-
  Voice cloning, TTS, voice design and ASR on the HuggingFace Space
  prithivMLmods/Qwen3-TTS-Daggr-UI. Use when the user wants to clone a voice
  from a reference audio file, synthesize speech (Chinese/English/…), design a
  new timbre from a text description, or transcribe audio — 声音克隆、语音合成、
  音色设计、音频转写. This Space is NOT Gradio: it speaks a custom WebSocket
  node-graph protocol, so do not reach for gradio_client or /gradio_api/*.
  Run scripts/qwen3tts.py for every operation instead of hand-writing requests.
tags: ["自习"]
---

# Qwen3-TTS-Daggr-UI

HuggingFace Space `prithivMLmods/Qwen3-TTS-Daggr-UI` 上的四个 Qwen3-TTS 算子：
声音克隆、语音合成、音色设计、音频转写。**匿名可用**，无需 token / cookie / 登录。

它不是 Gradio：推理走一条自定义 WebSocket 节点图协议，`gradio_client` 与
`/gradio_api/*` 在这里完全无效。协议细节已封装进 `scripts/`——**正常情况下不要
按协议手搓请求**。

## When to Use

- 用户要**克隆声音**（用一段参考音频说新文本）/ 声音克隆 / 复刻音色。
- 用户要**语音合成**（TTS / text to speech），可指定内置说话人。
- 用户要**音色设计**（用自然语言描述一个新音色，不需要参考音频）。
- 用户要**转写音频**（ASR / 这段语音说了什么）。

Don't use：标准 Gradio Space（`gradio_client` 用不了）；需要身份认证的站点；
**音频必须保密**的场景——上传内容会进入公开共享 Space 与共享 T4 实例，产物是
公开可猜的下载链接。

## 能做什么 / 调哪个 script

所有操作都走 `scripts/qwen3tts.py`（依赖见 `scripts/requirements.txt`）。

| 任务 | 命令 |
|---|---|
| 环境自检（**先跑这个**） | `python scripts/qwen3tts.py doctor` |
| 列出算子与端口 | `python scripts/qwen3tts.py nodes` |
| 查算子参数契约（必填/枚举） | `python scripts/qwen3tts.py schema "Voice Clone"` |
| Space 运行状态 | `python scripts/qwen3tts.py status` |
| 声音克隆 | `python scripts/qwen3tts.py clone <参考音频> -t "<文本>" -o out.wav --xvector true` |
| 预置音色合成 | `python scripts/qwen3tts.py say -t "<文本>" --speaker Serena -o out.wav` |
| 音色设计 | `python scripts/qwen3tts.py design -t "<文本>" -d "<音色描述>" -o out.wav` |
| 音频转写 | `python scripts/qwen3tts.py asr <音频文件>` |
| 下载产物 | `python scripts/qwen3tts.py download <路径或URL> -o a.wav` |
| 任意组合 | `python scripts/qwen3tts.py run "<算子名>" --inputs '{"text":"..."}'` |

四个算子名（区分大小写）：`Voice Clone` / `Custom Voice` / `Voice Design` /
`Qwen3 ASR`。不确定端口和枚举值时先跑 `schema <算子名>`，不要凭记忆写。

**音色设计**不需要参考音频，只要"要说的文本 + 一段音色描述"（`-d`）。描述用
英文效果更稳，可写音色、情绪、语速、年龄等，例如
`warm young female voice, gentle and clear`。产物端口是 `generated_audio`。

**声音克隆**则要"参考音频 + 目标文本"：`--xvector true` 只取说话人向量（快，
`--ref-text` 可省）；`--xvector false` 走完整 ICL（更像，约慢一倍，需给准逐字稿）。

> 上面四条推理命令执行时都会**长时间无任何输出**（推理期间服务端不推进度），
> 属正常现象，不要中断。预期耗时见下文「要等多久」。

## 使用前的必要条件

1. `pip install -r scripts/requirements.txt`（只有 `websockets>=12`）。
2. Space 在 RUNNING。`doctor` 会一并确认；`stage` 不是 `RUNNING` 时所有请求都会
   失败或极慢，只能等容器起来。
3. 输入音频是本地文件（脚本负责编码上传），或 `data:` / `http(s):` URL。

## 要等多久（**别因为慢就判定失败或取消**）

推理在共享 T4 实例上跑，且**期间服务端不推任何进度帧**——命令行会长时间静默，
这是正常的，不是卡死也不是断连。请务必耐心等到命令自己返回：

| 任务 | 实测耗时 |
|---|---|
| Qwen3 ASR（转写） | 7~10 s |
| Custom Voice（短句合成） | 6~12 s |
| Voice Design（音色设计） | 8~18 s |
| Voice Clone x-vector（短句） | 9~43 s |
| Voice Clone 完整 ICL（短句） | 10~32 s（约 x-vector 的 2 倍） |
| **Voice Clone x-vector，412 字中文** | **188 s**（产出 73.5 s 音频） |

粗算：**约 35s 固定开销 + 约 0.37s/中文字**。默认 `--timeout 600` 大约撑 1500 字；
文本更长就在命令里显式调大，例如 `--timeout 1800`。

**不要做的事**：不要中途 Ctrl-C、不要因为几十秒没输出就判定超时、不要重试
（一次 run = 一次完整 GPU 推理，重试就是双倍耗时和双倍占用，且拿不到更好的结果）。
真正超时只有一种：命令自己返回 `error.type == "timeout"`；那时先按上面的公式估算
是否确实需要更久，再调大 `--timeout` 重跑。

## 最重要的操作规则

1. **先 `doctor`**。它一次确认依赖 + Space 状态 + 节点图，比逐个命令试错便宜。
2. **必须判 `ok`**。业务失败不会抛异常、也不走协议 `error` 事件，而是照常到达
   `node_complete`，结论只在 `status` 文本里。只看"有没有报错"会漏掉全部业务失败。
3. **绝不重试 run**。一次 run = 一次完整 GPU 推理。只有"建连 + 取图"才重试。
   推理成功但下载失败时，重下而不是重跑。
4. **长文本调大 `--timeout`**（默认 600s）。耗时约 ~35s 固定开销 + ~0.37s/中文字，
   600s 约撑 1500 字。遇到 `timeout` 先估是不是真的慢，别盲目重试。
5. **Windows / Git Bash 下载产物时加 `MSYS_NO_PATHCONV=1`**，否则 `/file/...`
   会被改写成 Windows 路径，报 `getaddrinfo failed`（看着像网络故障）。
6. **结果要校验**：退出码 0 + `ok:true` + `status=="Success"` 才算成功；产物音频
   应能被 `wave` 解析且不是静音。

## 输出契约

stdout 恒为 JSON：`--pretty` 才缩进，默认单行便于解析。进度走 stderr。
退出码：`0` 成功，`1` 业务/网络失败，`2` 参数或 JSON 不合法，`130` Ctrl-C。

失败形如 `{"ok": false, "error": {"type": "...", "message": "..."}}`，
`type` 取值见 `references/errors.md`。

## 什么时候读 references

references 用于**排查脚本问题、扩展新操作、理解特殊字段、处理异常、协议变更时
维护 Skill**，不是日常执行前的必读项。

| 文件 | 读它的时机 |
|---|---|
| `references/authentication.md` | 确认认证方式、请求头、token 放置规则、隐私边界 |
| `references/protocol.md` | 排查脚本异常、协议变更时维护 Skill、要加新操作 |
| `references/data-models.md` | 查端口、必填、枚举值、RunResult 字段含义 |
| `references/workflows.md` | 理解一个任务内部怎么组合调用、重试与副作用边界 |
| `references/errors.md` | 命令报错，要判断能不能重试、改什么参数 |
| `references/examples.md` | 想看真实的报文/响应形状做对照 |

## 已验证 / 未验证

**已验证**（本次 CLI 实跑）：`doctor` / `nodes` / `schema` / `status`；四个算子
端到端跑通（ASR 转写、预置音色合成、x-vector 声音克隆、音色设计）；产物下载三种
路径写法（完整 URL、`MSYS_NO_PATHCONV=1` 带前导斜杠、去前导斜杠）；下载失败时
404 与「200+HTML」都能被魔数拦截且不落盘；未知节点名报 `unknown_node`；枚举值
错误报 `invalid_input`；JSON 不合法退出码 2；匿名访问无需凭证。

**未验证**：`model_size=0.6B` 端到端（枚举接受，实测用的 1.7B 默认）；
31 种 `lang_disp` 里的绝大多数语种；`instruct` 的具体语义；`hf_token` 持久化
（`set_sheet`）；并发/突发行为与排队上限。

## 风险与安全

- 所有推理都会把输入音频/文本上传到**公开共享** Space 推理，产物是公开可猜的
  UUID 链接。**不要**处理必须保密的音频；用户给了敏感音频先说明这一点。
- 该 Space **不需要**凭证。不要去抓 Cookie、不要构造登录、不要伪造 Authorization。
- 可选 HF token 只从环境变量 `QWEN3_TTS_HF_TOKEN` 读取，禁止写进 Skill、脚本、
  命令行参数或日志；脚本不打印它，也不放进任何 JSON 输出。
- 脚本只做命令要求的那一次 run，不自动重试、不自动换参数、不做任何额外写操作。
  本 Space 没有删除 / 发布 / 支付类接口，四个算子都是「输入 → 产物」的纯计算。

## Pitfalls

每一条都来自真实失败，脚本已内置处理，但遇到异常时要按这些思路归因：

1. **`status` 是唯一成功信号**：业务失败不走协议 `error` 事件，照样到达
   `node_complete`，结论只在 `status` 文本（`Text required`、
   `Error: Unsupported speakers: [...]`、`Could not process reference audio...`）。
2. **参数错误是静默的**：漏传必填回 `Success` + 一个用默认值的音频；端口名写错
   表现为"参数没生效"；未知节点名服务端完全不回消息（客户端已本地拦截）。
3. **单个 recv 空窗 ≠ 超时**：推理期间服务端不推任何进度帧，只有开始和结束各一条。
   命令行长时间静默是常态——**看到几分钟没输出不要取消，更不要当成失败**，
   静默不等于卡死（详见上文「要等多久」）。
4. **200 不代表拿到音频**：`/` 这类路径回 200 + SPA HTML。客户端用魔数白名单校验，
   校验失败即报错且不落盘。`Content-Type` 不可信（同份 wav 会回 `audio/x-wav`
   或 `application/octet-stream`）。
5. **音频输入不接受服务端自己的 `/file/tmp/…` 路径**，要复用产物先下载到本地。
6. **`use_xvector_only` 收到字符串 `"false"` 在 Python 里是真值**，会静默打开开关；
   客户端已显式收敛成 bool。
7. **耗时随文本长度显著增长**：短文本 7~12s，412 字中文克隆实测 188s，不要因为
   慢就重试。

## Verification

```bash
python scripts/qwen3tts.py doctor                       # 依赖 + RUNNING + 四算子在线
python scripts/qwen3tts.py asr <一个本地wav>             # 最便宜的端到端验证
python scripts/qwen3tts.py say -t "health check" --speaker Serena -o hc.wav
```

一次真正成功要同时满足：退出码 0、`ok:true`、`status=="Success"`、产物能被
`wave` 解析且不是静音。排查与错误分类见 `references/errors.md`。


