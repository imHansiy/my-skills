# 登录与 ticket

听悟的所有接口靠 cookie `login_aliyunid_ticket` 鉴权。SDK 不实现登录流程，
只负责使用一个**已有的** ticket。

## 通用做法：从浏览器复制（任何环境都能用）

不需要任何抓包软件，只需浏览器 F12。

### 1. 取 ticket

打开 <https://tingwu.aliyun.com> 并登录后，任选一种：

- **Application 面板**：F12 → Application（应用）→ 左侧 Cookies →
  `https://tingwu.aliyun.com` → 找 `login_aliyunid_ticket` → 复制 **Value** 一列
- **Network 面板**：F12 → Network（网络）→ 点任一请求 → Headers →
  Request Headers 里找 `Cookie:` → 复制整段（脚本会自己抠）
- **Console 面板**：F12 → Console → 执行 `document.cookie` → 从输出里找
  `login_aliyunid_ticket=` 后面那段
  > 该 cookie 有时是 HttpOnly，`document.cookie` 取不到；换前两种

### 2. 写入并验证

```bash
cd <skill>/scripts

python set_ticket.py "<ticket值>"        # 或粘整段 Cookie
python whoami.py                          # 退出码 0 = 有效
```

也支持从文件读（避免命令行里出现凭证）：

```bash
python set_ticket.py @cookie.txt
python set_ticket.py "<值>" --dry-run     # 只验证不写入
```

脚本会先 `check()` 验证再写入，**无效 ticket 不会污染缓存**。

## anything-analyzer 环境专用（可选）

如果装了 anything-analyzer（抓包库里有听悟的 cookie 快照），可以全自动：

```bash
python refresh_ticket.py              # 提取 → 验证 → 写入
python refresh_ticket.py --dry-run    # 只报告
python refresh_ticket.py --db <路径>  # 指定别的抓包库
```

它只读打开 `C:\Users\Admin\AppData\Roaming\anything-analyzer\data\anything-register.db`
的 `storage_snapshots` 表，取 `domain='tingwu.aliyun.com'` 的 cookie，
按时间倒序去重后逐个验证，取第一个真能用的。

**没有这个软件就别用它**，会提示你改用 `set_ticket.py`。

## 缓存位置

`C:\Users\Admin\.tingwu\ticket.json`，格式由 `Ticket.save()` 决定：

```json
{"value": "...", "issued_at": null, "obtained_at": 1790068105.07,
 "source": "manual-cookie", "extra_cookies": {}}
```

> 不要手写这个文件。格式错了 `Ticket.load()` 返回 `None`，
> 表现为 `'NoneType' object has no attribute 'value'`。
> 用 `set_ticket.py` / `refresh_ticket.py` / `Ticket.save()` 写入。

其它覆盖方式：

- Python：`TingwuClient(ticket=...)`，或 `Ticket.load(path)`
- CLI：`--ticket <值>` / `--ticket-file <路径>`

## 必须显式传 ticket

```python
c = TingwuClient(ticket=Ticket.load().value)   # 正确
c = TingwuClient()                             # 错误：不会自动加载缓存
```

## 判断是否还有效

**只信 `client.check()`，不要看 cookie 元数据里的过期时间**：

```bash
python whoami.py            # 或 python -m tingwu check
```

失效时接口返回 `CMN.NotLogin`。ticket 会过期，且**重新登录后轮换**
（旧的立即失效），所以过期了只能重新取一个。

## 其它途径（优先级低）

- **浏览器 CDP**：`extract_ticket_from_cdp()`，需浏览器以
  `--remote-debugging-port=9222` 启动 + `pip install -e .[browser]`。
  麻烦，一般没必要。
- **协议登录**（`PasswordLogin`）：需 `pip install -e .[login]`，RSA 加密密码，
  且会触发短信验证（`VerificationRequired`）。除非要全自动无人值守，否则别走。

## 安全

- ticket 等价于登录凭证，**不要打印完整值**、不要写进日志或交付物
- 两个脚本都只打印前 8 位
- 手机号等 PII 一律掩码（如 `180****0544`）
- 抓包库一律只读打开，禁止写入
