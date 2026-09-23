# Python API 参考

```python
from tingwu import TingwuClient, Ticket
c = TingwuClient(ticket=Ticket.load().value)   # ticket 必须显式传
```

## 资源一览

| 属性 | 用途 |
|---|---|
| `c.trans` | 转写记录：列、查、上传、等待、删除 |
| `c.export` | 官方导出：docx / pdf / srt / md |
| `c.directory` | 文件夹：树、增删改移 |
| `c.meeting` | 实时记录：创建、配置、起停、改名 |
| `c.account` | 账号信息、登录态 |
| `c.share` | 分享、邀请码 |
| `c.collect` | 收藏 |
| `c.discover` | 发现页：分类 / 播客 / 推荐 |
| `c.subscription` | 签到、剩余时长 |
| `c.lab` | AI 速览 / 问答 |
| `c.trash` | 回收站 |
| `c.notice` | 站内通知 |

## c.trans

| 方法 | 说明 |
|---|---|
| `list(page, page_size, raw)` | 记录列表 |
| `iter_all()` | 自动翻页 |
| `status(trans_id)` | 转写状态 |
| `result(trans_id)` | `Transcript` 对象（含 `to_srt` / `to_vtt` / `to_text` / `to_markdown`） |
| `result_raw(trans_id)` | 原始 dict |
| `detail(trans_id)` | 详情 |
| `upload_file(path, *, title, dir, **kw)` | 上传本地文件；`dir` 接受名 / 路径 / dirId |
| `upload_bytes(data, *, title, dir, content_type, is_video)` | 上传字节；类型可省略自动推断 |
| `resolve_dir_id(dir)` | 文件夹名 → dirId；找不到抛 `ValueError` |
| `wait(trans_id, *, timeout=3600, interval=10)` | 轮询到 status 1/2 |
| `delete(trans_id)` | 软删（`permanent=False`，服务端只接受这个） |
| `delete_from_share(trans_id)` | 从分享中删 |
| `parse_net_source(url)` / `query_net_source` | 播客链接解析 |
| `put_net_source_url` / `query_net_source_upload` | 播客转写 |
| `shared_with_me()` | 分享给我的 |

### Transcript 对象

```python
tr = c.trans.result(tid)
len(tr)              # 句数
tr.duration          # 秒
tr.speakers          # 说话人 ID 列表
tr.show_name
tr.playback_url      # OSS 签名播放地址（会过期）
tr.to_srt() / tr.to_vtt() / tr.to_text() / tr.to_markdown()
tr.by_speaker()      # 按说话人分组
```

## c.export

```python
from tingwu import FILE_DOCX, FILE_PDF, FILE_SRT, FILE_MD
from tingwu import DOC_ORIGINAL, DOC_NOTE, DOC_PPT, DOC_SMART_SCAN

task = c.export.create(tid, file_type=FILE_SRT, doc_type=DOC_ORIGINAL)
c.export.status(task)        # {"exportStatus": 0|1|-1, "exportUrls": [...]}
c.export.wait(task)          # 轮询到完成
c.export.download(tid, file_type=FILE_SRT)   # → [{transId, success, url, filename, content}]
c.export.save(tid, "./out", file_type=FILE_SRT)  # → [写入路径]
```

### 参数矩阵（实测）

**docType**：1 原文（`_原文.*`）· 3 笔记（`_笔记.pdf`）· 5 PPT（`_PPT.pdf`）· 7 导读（`_导读.pdf`）
0 是非法值（`EPO.InvalidRequest`）；2/6/9/10 返回 `success:false`。

**fileType**：0 docx · 1 pdf · 2 srt · 3 md；4/5 非法（`EPO.InvalidRequest`）。

> **只有「原文」四种格式都能出**；笔记 / PPT / 导读只出 pdf。

### 常量

```python
EXPORT_PENDING = 0
EXPORT_DONE = 1
EXPORT_FAILED = -1
EXPORT_RETRIES = 5            # EPO.RequestTooFast 退避次数
EXPORT_RETRY_WAIT = 6.0
EXPORT_NOT_READY = 3          # failReason=3：导出物还没准备好
EXPORT_NOT_READY_RETRIES = 4
EXPORT_NOT_READY_WAIT = 20.0
```

`filename_of(url)` 从 `response-content-disposition`（RFC 5987，双重编码）解文件名。

## c.meeting

```python
c.meeting.create(dir_id=0, show_name="")   # → meetingId / transId / meetingJoinUrl
c.meeting.info(meeting_id)
c.meeting.config(meeting_id, translate_result_enabled=False)
c.meeting.start(meeting_id) / .stop(meeting_id, role_split=ROLE_SPLIT_DIALOG) / .clear()
c.meeting.rename(trans_id, "新标题")       # → syncTransTag {showName}
c.meeting.doc_edit(trans_id)               # → getTransDocEdit
c.meeting.doc_save(trans_id, content)      # → saveTransDocEdit
```

常量：`MEETING_TYPE="101"`；`ROLE_SPLIT_NONE=-1` / `SINGLE=1` / `DIALOG=2` / `MULTI=3`；
`LANG_CN="cn"` / `LANG_EN="en"`；`ORIGIN_LANG_CN=1` / `ORIGIN_LANG_EN=2`。

正文是**钉钉文档 JSON 节点树**；`MeetingResource.build_doc_content(text)` 把纯文本包成节点树。

> 开始录音会创建**真实会议**，用完必须 `stop` + 软删记录。

## c.directory

`list()` `tree()` `flatten()` `find_by_name()` `create()` `rename()` `delete()` `move()` `has_processing()`

## 其它

- `c.subscription.gain_daily()` 签到；`remaining_hours()` 剩余时长
- `c.trash.list(keyword=)` / `restore()` / `empty()`
- `c.account.info()` / `is_login()` / `fuzzy_search()`

## c.lab（实测）

```python
c.lab.all_info(tid)                      # 速览 / 关键词，默认 content=["labInfo"]
c.lab.all_info(tid, content=["labRecommendQuestionsInfo"])
c.lab.recommend_questions(tid)           # 等价上面那行
c.lab.ask(tid, "问题") / .ask_status() / .ask_result() / .ask_history(tid) / .clear_history(tid)
```

- `getAllLabInfo` **必须带 `content`**（`list[str]`），不带返回 `CMN.ServerError`。
- 独立 action `labRecommendQuestionsInfo` 实测返回 `code=-1`（已废弃），
  不要直接调；`recommend_questions()` 内部走 `all_info(content=[...])`。
- `ask_status()` 无任务时返回 `-1`，不是报错。

## c.discover（实测）

```python
c.discover.categories()                  # 13 个分类
c.discover.category_rss(cat_id)          # 某分类下的播客源
c.discover.subscribed()                  # 我订阅的
c.discover.public_content(need_num=12)   # 发现页推荐（前端用 12）
c.discover.search("科技")                 # 搜播客 → 列表
c.discover.search_items("科技")           # 搜单集 → 列表
c.discover.content_by_trans(tid)         # 按转写 ID 反查 RSS 内容
```

- **`search` / `search_items` 的关键词参数是 `matchText`，不是 `keyword`**；
  路径也是独立的 `/explore/rss/search`、`/explore/content/search`
  （走 `request?action` 形式会 `CMN.ServerError`）。
- 两者结果在 `data.highlights`（**不是** `list`），标题带
  `<span class="s1">` 高亮标签，展示前要去标签；`total` 在 `data.total`。
- `content_by_trans` 参数是 `transIdList`（**数组**），传 `transId`
  会 `CMN.ServerError`；非 RSS 来源的转写 `data` 为空列表（非报错）。
- `public_content()` 每项含 `contentId` + `rssItemInfo.rssDTO.xmlLink`，
  可直接喂给 `c.trans.transcribe_net_source()`。

## c.collect（实测）

```python
c.collect.list()                         # 收藏列表
c.collect.add(content_id)                # 收藏，默认 type_=2
c.collect.remove(content_id)             # 取消，默认 type_=2
c.collect.iter_all()                     # 自动翻页
```

- **`type` 必须传 2**：0/1 → `CMN.ServerError`，3 → `COL.InvalidRequest`。
- `add` 参数是 `{type, idList:[...]}`；`remove` 是 `{cancelList:[{id,type}]}`，
  两者形状不同。
- `getCollectList` 的 `total` 在**响应顶层**，不在 `data` 里（`data` 是列表）。
- 收藏列表的 `filter` 用 `source`/`keyword`/`lang`/`mediaType`，
  **没有** `status`/`dirId`，传 `status` 会 `COL.InvalidRequest`。

## 底层调用

```python
c.request(action, params={...}, endpoint=None, raw=False)   # 走 action→模块路由
c.direct(action, body={...})                                # 走独立路径
```

`raw=True` 返回完整 body（含 `code` / `success`）—— **写操作一律用 `raw=True`**，
否则拿不到真实错误码。

未知 action 会报 `未知 action: 'xxx'。已知 165 个`，需更新 `tingwu.endpoints.ACTION_MODULE`。

## 错误码

| 码 | 含义 |
|---|---|
| `CMN.NotLogin` | ticket 失效 |
| `EPO.RequestTooFast` | 导出频控，等几秒重试 |
| `EPO.InvalidRequest` | docType / fileType 非法 |
| `TRS.InvalidRequest` | 参数不合法（如 `deletePermanently=True`） |
| `TRS.InvalidTrans` | transId 不存在 |
| `COL.InvalidRequest` | 收藏参数非法（`type` 非 2、filter 带 `status`） |
| `COL.NotShared` | 收藏目标未公开 |
| `CMN.ServerError` | 参数形状/路径不对（如 `getAllLabInfo` 缺 `content`、`getContentWithTransId` 传 `transId`、搜索走 `request` 路径） |
