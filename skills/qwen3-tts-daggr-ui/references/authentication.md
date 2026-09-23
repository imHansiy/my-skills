# 认证与访问

## 结论：匿名可用，没有认证环节

该 Space（`prithivMLmods/Qwen3-TTS-Daggr-UI`，host
`prithivmlmods-qwen3-tts-daggr-ui.hf.space`）**不需要任何凭证**。已实测确认：

| 环节 | 是否需要凭证 |
|---|---|
| WebSocket 建连 `wss://<host>/ws/<session_id>` | 否，无 Origin/Authorization 校验 |
| `get_graph` / `run` / `cancel` 三条 action | 否，消息里的 `hf_token` 字段恒为 `null` 也正常响应 |
| 产物下载 `GET https://<host>/file/tmp/<uuid>.wav` | 否，普通 HTTPS GET，无 Cookie 无 Referer 校验 |
| Space 状态查询 `huggingface.co/api/spaces/...` | 否 |

因此本 Skill 里**没有** Cookie / Session / CSRF / 登录态 / 刷新规则可言。
不要为此去抓 Cookie、不要试图"登录"、也不要构造 Authorization 头。

## 可选 HF token

- 前端 JS bundle 里存在 `hf_token` 字段与 `set_sheet` 调用，说明页面支持"绑定
  token 以持久化结果"，但**这不是访问前置条件**。
- 客户端把它做成可选项：
  - 来源：环境变量 `QWEN3_TTS_HF_TOKEN`（其次构造参数 `hf_token=`）。
  - 用途：仅按前端行为在 `get_graph` / `run` 消息里原样透传。
- **安全规则**：不要把 token 写进 SKILL.md、脚本、命令行参数或日志。命令行参数
  会进 shell history 与进程列表。走环境变量；脚本不打印它，也不把它放进任何
  JSON 输出（`_emit` 只输出 host / status / 产物路径，不含 token）。

## 认证失效判断

既然没有认证，也就不存在"认证失效"。请求失败时按这个顺序归因：

1. `doctor` 先看 Space `stage`——不是 `RUNNING`（常见 `BUILDING` / `SLEEPING`）
   时，任何请求都会失败或极慢，这是唯一需要"等待重认证"的情形（等容器起来）。
2. `graph_error`：拿不到节点图，同上，通常是 Space 未就绪或被限流。
3. `transport_error`：网络不可达、下载到的不是音频。
4. `unknown_node` / `invalid_input` / `run_failed`：业务或参数问题，与凭证无关。

## 请求头

- WebSocket：无自定义头，`websockets` 库默认即可。
- 产物下载：用 `urllib.request.urlopen` 默认头即可，实测无需 `User-Agent` 伪装。

## 环境变量

| 变量 | 作用 |
|---|---|
| `QWEN3_TTS_HOST` | 覆盖 Space 主机名（换镜像/自建时用） |
| `QWEN3_TTS_HF_TOKEN` | 可选 HF token，只为结果持久化，**非必需** |

## 隐私提示

音频会被上传到这个**公开共享**的 Space，并在共享 T4 实例上推理。不要用于必须
保密的音频。产物路径是公开可猜的 UUID 下载链接，任何拿到链接的人都能下载。
