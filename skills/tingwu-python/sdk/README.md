# tingwu — 通义听悟 Python SDK（非官方）

协议级封装 [tingwu.aliyun.com](https://tingwu.aliyun.com)，**直连 HTTP 接口，不需要浏览器**。

覆盖 168 个接口动作、32 个业务模块，含转写结果解析与 SRT/VTT/Markdown 导出。

```
pip install -e .              # 基础（仅需 requests）
pip install -e ".[login]"     # 协议登录（需 cryptography）
pip install -e ".[browser]"   # 从 CDP 读 ticket（需 websocket-client）
```

---

## 鉴权：只需一个 cookie

**听悟所有业务接口只认 cookie `login_aliyunid_ticket`，没有签名、没有 token 参数。**

实测消融（对 `/api/tingwu/account/info`）：

| 发送的 cookie | 结果 |
|---|---|
| 无 | `CMN.NotLogin` |
| **仅 `login_aliyunid_ticket`** | ✅ **成功** |
| 完整 30+ 个 cookie | ✅ 成功 |
| `pks` / `pk` / `yunpk` / `aui` / `cnaui` / `hssid`（单独或任意组合） | ❌ 全部 `CMN.NotLogin` |

所以那些 2027 年才过期的 cookie **并不能**用来长期免登录，只有 ticket 有效。

**有效期**：实测 **≥ 35.6 小时**仍未失效，而且期间 **ticket 的值从不轮换**——
同一份 ticket 反复可用，而 `isg` / `tfstk` / `atpsida` 这些风控 cookie 却在持续刷新。
说明 ticket 不参与前端续期，这个时长是它自身的寿命。浏览器里它是 session cookie
（`expires=-1`），那个值**不代表**真实寿命。

**所以不要用时间阈值判断是否该刷新**，用 `client.check()` 直接问服务端：

```python
if not client.check():                 # 真实探测；失效返回 False（不抛异常）
    client.ticket = extract_ticket_from_cdp()

client.ensure_login()                  # 严格版：无效则抛 AuthError
me = client.check_or_raise()           # 探测并顺便拿到账号信息
```

CLI 同样可用，退出码可直接给脚本判断：

```bash
tingwu check && echo "在线" || echo "掉线了"
```

**不绑定**：UA / Referer / Origin / 出口 IP 均可变；改动一个字符立即失效。

> ⚠️ `Ticket.is_probably_valid` 是**三态**：只有签发时刻已知时才返回 `True`/`False`，
> 从 cookie/CDP 拿到的 ticket 返回 **`None`（无法判断）**。
> 它不是"有效"的意思，别拿它当门禁——用 `check()`。

### 三种拿 ticket 的方式

```python
from tingwu import TingwuClient, Ticket, extract_ticket_from_cdp, extract_ticket_from_cookie_string

# 1) 手工复制 cookie 串（最省事）
client = TingwuClient.from_cookie("login_aliyunid_ticket=_wkpof_...")

# 2) 从运行中的浏览器读（需 --remote-debugging-port=9222）
client = TingwuClient(ticket=extract_ticket_from_cdp())

# 3) 环境变量
#    export TINGWU_TICKET='login_aliyunid_ticket=_wkpof_...'
from tingwu import client_from_env
client = client_from_env()
```

ticket 是 `HttpOnly`，`document.cookie` 读不到，只能走 CDP 或抓包。

### 协议登录（账密）

```python
from tingwu import PasswordLogin, VerificationRequired

login = PasswordLogin("13800000000", "your-password")
try:
    result = login.submit()
    print(result.ticket.value[:20])
except VerificationRequired as e:
    # 阿里云风控（baxia/IV）大概率要求短信验证
    code = input(f"短信验证码（{e.phone}）：")
    result = login.verify_sms(e.htoken, code)
```

登录流程已完全复现并实测通过：

```
GET  login.htm                      → 提取 rsaModulus / rsaExponent / _csrf
RSA(password, PKCS#1 v1.5)          → password2（512 位 hex，已实测格式被接受）
POST loginLegacy/password/login.do  → 错误密码返回"密码错误"，证明链路正确
   └─ 风控 IV：upload_env → ivsend → verify_ajax → 下发 ticket
```

**注意**：实测该账号/环境**登录会触发短信验证**，所以协议登录是**半自动**的。
若只需调用 API，用上面的方式 1/2 拿 ticket 更省事。`umidToken` 可以留空
（成功请求里它本身就是空的）。

---

## 用法

```python
from tingwu import TingwuClient

c = TingwuClient.from_cookie("login_aliyunid_ticket=_wkpof_...")

# 账号
c.account.info()          # {'userId': <你的 userId>, 'accountId': ..., 'encodedUsername': ...}
c.account.aliyun_info()   # 阿里云侧（含手机号、昵称）

# 文件夹
c.directory.flatten()     # [{'dirId': 319288, 'path': '工作'}, ...]

# 转写列表
c.trans.list(dir_id=0, status=[0])         # 进行中
c.trans.list(status=[1,2,3,4,11])          # 历史
list(c.trans.iter_all(max_items=100))      # 自动翻页

# 转写结果
tr = c.trans.result("zj78qpprw44rqxdp")
print(len(tr))            # 3552 句
print(tr.text[:200])
print(tr.duration)        # 7981.0 秒
print(tr.speakers)        # ['1', '2', ...]
print(tr.show_name)

# 本地导出（从转写结果直接生成文本）
tr.to_srt(with_speaker=True)
tr.to_vtt()
tr.to_markdown()
tr.to_text(with_timestamps=True)
tr.by_speaker()

# 官方导出（服务端生成 docx / pdf / srt / md 并给下载链接）
c.export.create("zj78qpprw44rqxdp", file_type=2)   # -> exportTaskId
c.export.wait(task_id)                             # -> {'exportStatus': 1, 'exportUrls': [...]}
c.export.save("zj78qpprw44rqxdp", "./out", file_type=2)   # 直接落盘

# 上传音视频到指定文件夹
r = c.trans.upload_file("周会.mp4", dir="工作/odoo")   # 文件夹名、路径、dirId 都行
print(r["transId"], r["dirId"], r["isVideo"])
c.trans.wait(r["transId"])                          # 等转写完成（status 1=成功）

# 其他模块
c.share.invite_info()          # 邀请码 + 微信二维码
c.subscription.gain_daily()    # 每日签到
c.notice.list()                # 站内通知
c.trash.list()                 # 回收站
c.lab.all_info("transId")      # AI 速览/问答
```

### 逃生舱：调未封装的接口

168 个 action 里没被封装成方法的，用 `request()` 直调：

```python
c.request("getTransTag", params={"transIds": ["xxx"]})
c.call_path("/trans/getTransResult", body={"action": "getTransResult", "version": "1.0", "transId": "xxx"})
```

### 长任务 / 自动刷新

```python
def refresh():
    return extract_ticket_from_cdp()   # 或重新读文件/环境变量

c = TingwuClient(
    ticket=Ticket.load(),
    on_auth_expired=refresh,   # 遇 CMN.NotLogin 时自动刷新并重放原请求
)

# 长任务开头先确认在线，避免跑到一半才发现掉线
c.ensure_login()
for item in c.trans.iter_all():
    process(item)
```

**为什么不靠时间判断**：ticket 实测能活 35+ 小时，任何固定阈值都只是猜测；
而且从 cookie 复制来的 ticket 根本无法知道签发时刻。所以：

| 想做的事 | 用哪个 |
|---|---|
| 确认现在能不能用 | `client.check()` |
| 确保能跑再开工 | `client.ensure_login()` |
| 探测 + 拿账号信息 | `client.check_or_raise()` |
| 自动续期 | `on_auth_expired=` 回调 |
| ~~按时间猜~~ | ~~`Ticket.is_probably_valid`~~（可能返回 `None`） |

---

## 命令行

```bash
tingwu check                     # 探测登录态（退出码 0=有效 / 1=失效）
tingwu whoami                    # 当前账号
tingwu ls                        # 进行中的任务
tingwu ls --status history       # 历史
tingwu dirs                      # 文件夹树
tingwu get <transId>             # 打印全文
tingwu srt <transId> -o a.srt    # 导出字幕（自动建目录）
tingwu md  <transId> -o a.md
tingwu txt <transId> --speaker
tingwu search 关键词

# 上传 → 指定位置 → 下载文档/SRT
tingwu upload 周会.mp4 --dir 工作/odoo
tingwu upload 周会.mp4 --wait --format srt --out-dir ./out   # 等转写完直接导出
tingwu export <transId> --format srt --out-dir ./out
tingwu export <transId> --format docx          # 也支持 pdf / md
tingwu export <transId> --doc note --format pdf  # 笔记（笔记/PPT/导读只出 pdf）
tingwu quota                     # 签到 + 权益
tingwu invite                    # 邀请码
tingwu ticket --from-cdp         # 导出并缓存 ticket
tingwu raw getTransList --params '{"status":[0]}'   # 调任意 action
```

---

## 协议要点

**请求格式**（实测）：

```
POST https://tingwu.aliyun.com/api/<module>/request?<action>&c=web
Content-Type: application/json
Cookie: login_aliyunid_ticket=<value>

{"action": "<action>", "version": "1.0", ...业务参数}
```

- `?<action>` 在 query 里，body 里也要有同名 `action`，**两者必须一致**
- `&c=web` 可省略
- 无需 `X-B3-*` 等追踪头，也无需 Referer/Origin

**响应格式**：

```json
{"code": "0", "message": "success", "requestId": "...", "data": {...}, "success": true}
```

未登录时 `code = "CMN.NotLogin"`。

**转写结果结构**（`/trans/getTransResult`）：

```
data.tag                 元信息（showName / lang / fileFormat ...）
data.duration            时长，单位【秒】（不是毫秒！）
data.playback            OSS 签名播放地址（会过期）
data.result              JSON 字符串 → {"pg": [...]}
  pg[i].ui               说话人 ID
  pg[i].sc[j].bt / .et   句起止，毫秒
  pg[i].sc[j].si         全局句序号（递增，不是说话人）
  pg[i].sc[j].tc         文本
```

**两个易踩的坑**：

1. `duration` 单位是**秒**（`1670` 对应 `max(et)=1670200` 毫秒）
2. `si` 是句子序号不是说话人，说话人看 `pg[].ui`

**几个接口有两套 endpoint**（不同产品线）：

| action | 用途 | endpoint |
|---|---|---|
| `exportTrans` / `getExportStatus` | 导出到本地下载 | `/export/request`（`c.export`） |
| `fuzzySearchInBiz` | 搜索 | `/tingwu/account/request`（`/account/request` 实测 404） |

`ACTION_MODULE` 里 `exportTrans` 默认归到 `aliyundrive`；
本地下载那套在 `c.export` 内部用 `endpoint=` 显式指定，不需要调用方关心。

### 官方导出参数（实测）

导出是异步两步：先拿 `exportTaskId`，再轮询 `exportStatus`（0 进行中 / 1 完成 / -1 失败）。

| 参数 | 取值 |
|---|---|
| `docType` | 1 原文 · 3 笔记 · 5 PPT · 7 导读 |
| `fileType` | 0 docx · 1 pdf · 2 srt · 3 md |

只有「原文」四种格式都能出；笔记 / PPT / 导读只出 pdf（`fileType` 传别的会拿到
`success=false`）。`fileType` 4/5 返回 `EPO.InvalidRequest`。

连续导出会被 `EPO.RequestTooFast` 频控，`c.export.create` 内部已自动退避重试。
刚转写完立刻导出常拿到 `success=false, failReason=3`（服务端还没生成导出物），
`c.export.download` 内部会等 20s 起、逐步放大重发，最多 4 轮。
下载链接是 OSS 签名地址，文件名在 `response-content-disposition` 里（RFC 5987，双重编码）。

**`getTransResult` 不在 `/request` 形式下**，正确路径是 `/trans/getTransResult`。
本库的 `PATH_OVERRIDES` 已处理。

---

## 已知未覆盖

- **上传/创建转写任务**：`generatePutLink` → OSS PUT → `syncPutLink` 三步已分别可用，
  但没有封装成一步式 `upload()`（涉及 OSS 直传与断点续传策略）。目前会话里也没有
  完整的上传抓包可供核对。
- **实时会议（WebSocket）**：`meeting` 模块的实时转写走 WS，未实现。
- `timeFlow` 语义未证实（签到后仍为 0，而 `maxTimeFlow` 是 1440000），
  `subscription.remaining_seconds()` 的结果请自行验证。
- 部分模块（`lab` 的 AI 问答、`export` 导出、`meeting`）只做了接口映射，
  未逐个实测参数。

---

## 开发

```bash
pip install -e ".[dev]"
pytest tests/test_unit.py -q          # 49 个离线测试
export TINGWU_TICKET='login_aliyunid_ticket=...'
python tests/test_live.py             # 26 个真实接口测试
```

## 免责声明

非官方项目，仅供个人学习与自动化自有账号使用。接口可能随时变更；
请遵守目标站点的服务条款，控制请求频率。
