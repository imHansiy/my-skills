# scripts 目录

开箱即用的命令行工具。每个脚本自己处理 SDK 路径、ticket 加载、登录态检查、
UTF-8 输出，直接跑就行，不用先写 Python。

```bash
cd <skill>/scripts
python <脚本>.py [参数]
```

多数脚本支持 `--json`（结构化输出）和 `--sdk PATH`（覆盖 SDK 路径）。

## 共享模块

`_bootstrap.py` —— 公共引导层。自己写新脚本时：

```python
from _bootstrap import client, out, die, add_common, apply_sdk_arg
```

- `client()` 返回**已验证登录态**的 `TingwuClient`（ticket 失效直接退出并提示）
- `out(data, as_json=)` 统一输出
- `die(msg)` 打印错误并退出 1
- `add_common(parser)` 加 `--json` / `--sdk`

## 脚本清单

| 脚本 | 作用 | 读写 |
|---|---|---|
| `set_ticket.py` | **用浏览器复制的 ticket 登录（通用，不需抓包软件）** | 写 |
| `refresh_ticket.py` | 从 anything-analyzer 抓包库恢复（仅该环境） | 写 |
| `whoami.py` | 登录态 + 剩余时长 | 读 |
| `list_dirs.py` | 文件夹与 dirId（供 upload `--dir`） | 读 |
| `list_trans.py` | 转写记录列表 | 读 |
| `search.py` | 按名称搜记录 | 读 |
| `get_result.py` | 取全文 / SRT / VTT / MD，可写文件 | 读 |
| `trash.py` | 回收站 | 读 |
| `upload.py` | **上传音视频，可选等完直接导出** | 写 |
| `wait_trans.py` | 等转写完成，可选随后导出 | 读 |
| `export.py` | 导出 docx / pdf / srt / md | 写 |
| `batch_export.py` | 批量导出（自动避开频控） | 写 |
| `delete_trans.py` | 删除记录（软删，进回收站） | 写 |
| `meeting.py` | 实时记录：创建 / 状态 / 停止 / 改名 | 写 |
| `netsource.py` | 播客链接转写 | 写 |
| `probe_action.py` | 探测未封装的 action 能否用 | 读 |

## 典型组合

**登录失效 —— 用浏览器复制的 ticket 恢复**（通用）：

```bash
python whoami.py                    # 1 检查（退出码非 0 = 失效）
python set_ticket.py "<ticket值>"   # 2 写入并验证
python whoami.py                    # 3 再确认
```

ticket 从 F12 → Application → Cookies → `login_aliyunid_ticket` 的 Value 取；
也可以粘整段 `Cookie:` 头，或用 `@文件` 读。

**仅限装了 anything-analyzer 的环境**：`python refresh_ticket.py` 可全自动。
细节见 [../references/AUTH.md](../references/AUTH.md)。
细节见 [../references/AUTH.md](../references/AUTH.md)。

**上传视频 → 转写 → 拿 SRT**（一条命令）：

```bash
python upload.py 会议.mp4 --dir "工作/odoo" --wait --format srt --out-dir ./out
```

**已有记录批量导出字幕**：

```bash
python search.py 周会            # 先找 ID
python batch_export.py ID1 ID2 ID3 --format srt --out-dir ./out
```

## 注意

- `upload.py --dir` 找不到文件夹会**报错**，不会静默落到根目录
- `delete_trans.py` 只能软删（服务端拒绝永久删除）
- `batch_export.py` 每条之间默认等 8 秒，避开 `EPO.RequestTooFast`
- `meeting.py create` 会建**真实会议**并开始录音，用完必须 `stop`
- `export.py` 报「未返回文件」通常是导出物还没生成，隔半分钟重跑即可
- `refresh_ticket.py` 只读打开抓包库，只打印 ticket 前 8 位
