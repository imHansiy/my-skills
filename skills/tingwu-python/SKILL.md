---
name: tingwu-python
description: 通义听悟 (tingwu.aliyun.com) 非官方 Python SDK 与 CLI —— 上传本地音视频转写、等待结果、官方导出 docx/pdf/srt/md、文件夹管理、实时记录、播客链接转写。当用户要处理通义听悟的转写记录、把视频/音频转成字幕或文档、批量导出 SRT、或调用听悟内部 API 时使用。
license: MIT
compatibility: >-
  Requires Python 3.9+. The SDK ships with this skill under sdk/;
  scripts locate it automatically (override with env TINGWU_SDK),
  or run `pip install -e ./sdk` to install it into the environment.
  Needs a valid login ticket cached at ~/.tingwu/ticket.json
  (env TINGWU_TICKET or --ticket also accepted). Network access required.
metadata:
  author: imHansiy
  version: "0.1.0"
  verified: "upload -> wait -> export srt/md closed-loop; lab/discover/collect 接口实测"
---

# 通义听悟 SDK / CLI

操作 `tingwu.aliyun.com` 的协议级 Python SDK。

**优先用 `scripts/` 下现成的脚本**，不要从头拼 Python。每个脚本自带
SDK 路径、ticket 加载、登录态检查、UTF-8 输出，直接跑即可。
完整清单见 [scripts/README.md](scripts/README.md)。

```bash
cd <skill>/scripts
python whoami.py              # 退出码 0 = 有效
```

**ticket 不会自动加载** —— 自己写 Python 时必须显式传：

```python
from tingwu import TingwuClient, Ticket
c = TingwuClient(ticket=Ticket.load().value)   # 不能写 TingwuClient()
```

用 `_bootstrap.client()` 则已处理好，不用管。

### 登录失效（CMN.NotLogin / whoami 退出码非 0）

ticket 会过期，且**重新登录后轮换**（旧的立即失效），只能重新取一个。

**通用做法** —— 从浏览器 DevTools 复制，不需要任何抓包软件：

1. 打开 tingwu.aliyun.com 登录后按 F12
2. Application → Cookies → `https://tingwu.aliyun.com`
   → 复制 `login_aliyunid_ticket` 的 Value
   （或从 Network 面板复制整段 `Cookie:` 头）
3. 写入并验证：

```bash
python set_ticket.py "<ticket值>"     # 也接受整段 Cookie，或 @文件路径
python whoami.py                       # 确认
```

脚本先 `check()` 验证再写入，无效 ticket 不会污染缓存。

**仅限本环境**：装了 anything-analyzer 时可全自动
`python refresh_ticket.py`（从抓包库提取，只读）。没有该软件就别用它。
细节见 [references/AUTH.md](references/AUTH.md)。
## 主力闭环：上传 → 转写 → 导出

一条命令做完：

```bash
cd <skill>/scripts
python upload.py 视频.mp4 --dir "工作/odoo" --wait --format srt --out-dir ./out
```

- `--dir` 接受**文件夹名、路径或 dirId**（`工作/odoo` → 319289；缺省 0 = 默认文件夹）。
  名字找不到会**报错**，不会静默落到根目录。不知道有哪些文件夹就先跑
  `python list_dirs.py`。
- 音视频类型**自动推断**（mp4/mov/mkv/avi… = 视频；mp3/wav/m4a/flac… = 音频）。
  类型错了视频会被当音频处理。
- `--wait` 轮询到转写完成，然后按 `--format` 导出。
- `--format` docx / pdf / srt / md；`--doc` original 原文 / note 笔记 / ppt / scan 导读。

对**已存在**的记录导出（`export.py`），批量用 `batch_export.py`：

```bash
python export.py <transId> --format srt --out-dir ./out
python batch_export.py ID1 ID2 ID3 --format srt --out-dir ./out
```

`batch_export.py` 每条之间默认等 8 秒，避开 `EPO.RequestTooFast`；
个别失败不中断，最后汇总。

不上传、只读结果用 `get_result.py`（本地生成字幕，不走导出服务，不用等）：

```bash
python get_result.py <transId> --format srt -o out.srt
python get_result.py <transId> --info          # 句数/时长/说话人
```

## 常用脚本

| 脚本 | 用途 |
|---|---|
| `list_dirs.py` | 文件夹与 dirId |
| `list_trans.py [--status history\|all]` | 转写记录列表 |
| `search.py 关键词` | 按名称搜 |
| `get_result.py ID [--format srt\|vtt\|md\|text]` | 读结果，可 `-o` 写文件 |
| `trash.py` | 回收站 |
| `export.py ID --format srt` | 官方导出 |
| `batch_export.py ID... --format srt` | 批量导出 |
| `delete_trans.py ID...` | 删除（软删） |
| `meeting.py create\|status\|stop\|rename` | 实时记录 |
| `netsource.py URL` | 播客链接转写 |
| `probe_action.py ACTION '{json}'` | 探测未封装的 action |

都要先 `cd <skill>/scripts`。
全部支持 `--json`。细节见 [scripts/README.md](scripts/README.md)。

SDK 还自带一个 `python -m tingwu <子命令>` CLI（`ls` / `dirs` / `get` / `srt` /
`raw` / `doc` / `meeting` 等），参数见 [references/CLI.md](references/CLI.md)。

## 关键坑（都踩过）

1. **导出要用 `/api/export/request`，不是 `/aliyundrive/request`。**
   后者是"导出到阿里云盘"。`c.export` 内部已用 `endpoint=` 显式指定，直接用即可。

2. **导出是异步两步**：`exportTrans` → `exportTaskId` → 轮询 `getExportStatus`
   （0 进行中 / 1 完成 / -1 失败）→ 拿 OSS 签名 URL 下载。

3. **刚转写完立刻导出常失败**（`success=false, failReason=3`，服务端还没生成导出物）。
   `c.export.download` 已内置重试（20s 起逐步放大，最多 4 轮）。看到 `导出失败：服务端未返回文件`
   时**先等一会儿重跑** `tingwu export`，不是代码 bug。

4. **连续导出会被 `EPO.RequestTooFast` 频控**，`c.export.create` 内部自动退避。

5. **只有「原文」四种格式都能出**；笔记 / PPT / 导读只出 pdf。`fileType` 4/5 是非法值。

6. **删除只能用软删**：`delTrans` 的 `deletePermanently=True` 会被拒（`TRS.InvalidRequest`）。
   `c.trans.delete()` 默认 `permanent=False`，正确。

7. **`getTransResult` 的路径是 `/trans/getTransResult`**（不在 `/request` 形式下），
   `PATH_OVERRIDES` 已处理。

8. **Windows 终端是 GBK**，中文输出乱码 ≠ 数据损坏。脚本里加
   `sys.stdout.reconfigure(encoding="utf-8")`。

9. **跑测试不要设 `PYTHONIOENCODING=utf-8`**（`TestEncoding` 会因环境变量失败）：
   ```bash
   PYTHONUTF8=0 python -m pytest tests/test_unit.py -q    # 66 passed
   ```

10. **不要猜接口**。新增 action 先用 `c.request(action, params=..., raw=True)` 探测，
    只有返回 `code:"0"` / `success:true` 才封装。已验证 165 个 action。

11. **成功响应不等于成功**。历史上 `importFile` 返回 `code:"0"` 却不创建记录。
    写操作后回列表确认。

## 数据约定

- `duration` 单位是**秒**（不是毫秒）
- `pg[].ui` = 说话人；`sc[].si` = 全局句序号（**不是**说话人）
- 导出文件名在 URL 的 `response-content-disposition` 里（RFC 5987，双重编码），
  `export.filename_of(url)` 已处理

## 已移除 / 不支持

- **阿里云盘导入（`importFile`）已删除** —— 接口静默失败（响应 200 但不入库），不可用。
  需要云盘文件时让用户自己下载到本地再 `upload`。
- 实时音频流：`createMeeting` 返回 WebSocket 地址，本库只做 HTTP，不支持推流。

## 参考文件

- [references/API.md](references/API.md) —— Python API 全量方法 + 导出参数矩阵
- [references/CLI.md](references/CLI.md) —— 每个子命令的完整参数
- [references/AUTH.md](references/AUTH.md) —— ticket 获取与失效处理
- [scripts/probe_action.py](scripts/probe_action.py) —— 探测未封装的 action
