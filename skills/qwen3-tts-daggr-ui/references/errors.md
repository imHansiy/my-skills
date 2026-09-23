# 已观察到的错误与处理

## 最危险的一类：`status` 是唯一成功信号

成功与业务失败共用同一个 `node_complete` 形状。**业务失败不走 WebSocket 的
`error` 事件**，`node_complete` 照样正常到达，异常只在 `status` 文本里。

| 场景 | `status` 文本 |
|---|---|
| 成功 | `Success` |
| 缺文本 | `Text required` |
| 说话人写错 | `Error: Unsupported speakers: ['xxx']` |
| 参考音频读不了 | `Could not process reference audio. Please upload a valid WAV/MP3.` |

判定必须靠 `ok = status.strip().lower() == "success"`。
**只看"有没有抛异常"会漏掉全部业务失败**——这是本项目最容易出现的产品级缺陷。

## 错误分类（CLI 输出的 `error.type`）

| type | 触发 | 处理 |
|---|---|---|
| `invalid_input` | 文件不存在、必填缺失、枚举值不在可选列表、音频端口收到 `/file/` 路径 | 改参数，**不要重试** |
| `unknown_node` | 节点名不在图里，或该节点是 INPUT 参数节点 | 用 `nodes` / `schema` 取正确名字 |
| `graph_error` | 取不到节点图或图结构不符 | 通常 Space 未就绪，**等待后重试** |
| `transport_error` | 连不上、消息非法、下载到的不是音频 | 网络类可重试；下载类先确认路径 |
| `timeout` | `run_timeout` 内没等到本节点完成 | 见下文"假超时" |
| `run_failed` | `status` 非 Success，或收到 `error` / `cancelled` | 读 `status` 文案修输入 |
| `interrupted` | Ctrl-C | — |

退出码：`0` 成功，`1` 业务/网络失败，`2` 参数或 JSON 不合法，`130` Ctrl-C。

## 假超时：单个 recv 空窗 ≠ 超时

服务端在推理期间**不推任何进度帧**，只在开始和结束各推一条。客户端曾用 45 秒的
recv 窗口轮询，导致任何超过约 45 秒的任务都被误杀成"超时"——实测 412 字中文克隆
在 `run_timeout=900` 下仍于 49 秒失败，看起来像服务端有问题，其实是等待逻辑。

现在的实现：单个窗口空等只是内部信号，回到循环重算剩余时间，直到真正的
deadline 耗尽才报 `timeout`。只有取图这种一次性等待才把空窗换算成超时
（报 Space 可能正在冷启动）。

**遇到 `timeout`**：先确认是不是真的慢。用 ~35s 固定开销 + ~0.37s/中文字估算，
超出就把 `--timeout` 调大，而不是反复重试。

## 下载类错误：200 不代表拿到音频

| 路径 | 响应 |
|---|---|
| `/file/tmp/<valid>.wav` | 200，音频 |
| `/file/tmp/nope.wav` | 404 |
| `/file/nope.wav` | 403 |
| `/nope`、`/`、`/favicon.ico` | **200 + SPA HTML** |

所以下载**必须校验正文魔数**（`RIFF` / `fLaC` / `OggS` / `ID3` / mp3 帧同步
`0xFF…` / `ftyp`），用白名单而非黑名单——黑名单漏得掉 JSON 错误体、带 BOM 的页面。
校验失败时报错且**不落盘**（不能留一个打不开的 .wav 还回报成功）。

`Content-Type` **不可作为准入条件**：同一份 wav 实测会返回 `audio/x-wav` 或
`application/octet-stream`；它只用于报错文案。

## 参数错误是静默的

- 漏传必填：不报错，返回 `Success` + 一个用了默认值的音频 → 只能本地拦截。
- 端口名写错：不报错，该参数取默认值 → 表现为"参数没生效"。
- 未知 `node_name`：服务端**完全不回消息**，客户端挂到超时，看起来像"推理很慢"。
- `use_xvector_only` 收到字符串 `"false"`：Python 里是真值 → 静默**打开**开关。

这些都不会产生任何错误信号，所以客户端把能本地校验的（必填、枚举、键名、
checkbox 收敛）全部放在发送之前。

## Git Bash 路径改写（Windows 特有，但报错像网络故障）

MSYS 会把参数里的 `/file/tmp/a.wav` 改写成
`D:/Apps/Scoop/apps/git/2.54.0/file/tmp/a.wav`，最终报
`getaddrinfo failed`——看起来像网络不通，其实是参数被改了。

三种可行写法（客户端都会归一化）：

```bash
MSYS_NO_PATHCONV=1 python scripts/qwen3tts.py download /file/tmp/a.wav -o a.wav
python scripts/qwen3tts.py download "https://<host>/file/tmp/a.wav" -o a.wav
python scripts/qwen3tts.py download file/tmp/a.wav -o a.wav
```

## 结果"成功但不对"的兜底校验

一次真正成功的合成应满足：退出码 0、`ok: true`、`status == "Success"`、文件能被
`wave` 解析、且 RMS 不是接近 0（静音也是一种失败）。
