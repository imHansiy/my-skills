# CLI 参考

```bash
cd "D:\Dev\Anything Analyzer\tingwu-python"
python -m tingwu <command> [options]
```

全局选项：`--ticket TICKET`（覆盖环境变量）、`--ticket-file PATH`（默认 `C:\Users\Admin\.tingwu\ticket.json`）

## 命令清单

`check` `whoami` `ls` `dirs` `get` `srt` `vtt` `md` `txt` `search` `quota` `invite`
`ticket` `collect` `trash` `discover` `upload` `export` `netsource` `meeting` `doc` `raw`

## 主力命令

### upload

```bash
python -m tingwu upload PATH \
    [--title 标题] [--dir 文件夹名或dirId] [--dir-id ID] [--lang cn] \
    [--wait] [--format {docx,md,pdf,srt}] [--doc {note,original,ppt,scan}] \
    [--out-dir DIR] [--timeout 3600] [--interval 10] [--json]
```

- `--dir` 接受**名 / 路径 / dirId**；名字找不到**报错**（不会静默落到根目录）
- 媒体类型按扩展名自动推断，并写入 `originalTag.isVideo`
- `--wait` 转写完成后按 `--format` 导出（默认 md）

```bash
python -m tingwu upload 周会.mp4 --dir "工作/odoo" --wait --format srt
```

### export

```bash
python -m tingwu export TRANS_ID \
    [--format {docx,md,pdf,srt} | --srt] [--doc {note,original,ppt,scan}] \
    [--out-dir DIR] [--timeout 300] [--no-speaker] [--no-timestamp] [--json]
```

导出已有记录。`failReason=3` = 服务端还没准备好，**等一会儿重跑**即可。

## 其余命令

| 命令 | 主要参数 |
|---|---|
| `check` | 无。退出码 0/1 |
| `whoami` | 无 |
| `ls` | 分页 / `--json` |
| `dirs` | 无。输出 `dirId  路径` |
| `get TRANS_ID` | 打印全文 |
| `srt` / `vtt` / `md` / `txt` | `TRANS_ID`，本地生成字幕（不走官方导出服务） |
| `search 关键词` | 按名称搜 |
| `quota` | 签到 + 权益 |
| `invite` | 邀请码与二维码 |
| `ticket` | 导出 / 缓存 ticket |
| `collect` | 收藏列表 |
| `trash` | 回收站 |
| `discover` | 分类 / 播客 / 推荐 |
| `netsource URL` | 播客链接转写 |
| `raw ACTION [JSON]` | 调任意 action |

### meeting

```bash
python -m tingwu meeting create   [--dir ID] [--title 名]
python -m tingwu meeting status   MEETING_ID
python -m tingwu meeting config   MEETING_ID [--translate] [--origin-lang N]
python -m tingwu meeting stop     MEETING_ID [--role-split {-1,1,2,3}]
python -m tingwu meeting rename   TRANS_ID 新标题
python -m tingwu meeting tag      TRANS_ID [--translate-switch 0|1] [--origin-lang N]
```

`--role-split`：`-1` 暂不体验 / `1` 单人演讲 / `2` 两人对话 / `3` 多人讨论。

> `create` 会产生**真实会议**，用完必须 `stop` 并软删记录。

### doc

```bash
python -m tingwu doc get TRANS_ID          # 读取正文（钉钉文档 JSON 树）
python -m tingwu doc set TRANS_ID [--file PATH | --text "内容"]
```

## 退出码

`check` 用退出码表示登录态是否有效（0 有效 / 1 失效）。其它命令失败时非 0。
