# tingwu-python

通义听悟（<https://tingwu.aliyun.com>）的非官方 Python SDK + CLI + 现成脚本，
覆盖「上传音视频 → 转写 → 导出」的完整闭环。

- **SDK**（`sdk/`）：协议级 Python 包 `tingwu`，165 个 action 的路由表、
  资源化封装（`c.trans` / `c.lab` / `c.discover` / `c.collect` …）、CLI。
- **脚本**（`scripts/`）：16 个开箱即用的命令行工具，自带 SDK 定位、ticket
  加载、登录态检查、UTF-8 输出。

## 目录结构

```text
tingwu-python/
├─ SKILL.md              # 技能入口（AI 读这个）
├─ references/           # API / AUTH / CLI 细节文档
├─ scripts/              # 16 个可执行脚本
└─ sdk/                  # Python 包源码（tingwu/）+ 测试 + 示例
```

## 快速开始

```bash
# 1) 装 SDK（二选一）
pip install -e ./sdk          # 装进环境
export TINGWU_SDK=/path/to/sdk  # 或只指过去，脚本自动找

# 2) 放 ticket：浏览器 F12 复制 Cookie 后
python scripts/set_ticket.py "<ticket 值或整条 Cookie 头>"
python scripts/whoami.py      # 退出码 0 = 登录有效

# 3) 上传并导出
python scripts/upload.py 录音.mp3 --dir 工作/odoo --wait --format docx
```

获取 ticket 的三种方式见 `references/AUTH.md`（推荐浏览器 F12，无需抓包工具）。

## 常用脚本

| 脚本 | 作用 |
|---|---|
| `whoami.py` | 检查登录态 / 剩余时长 |
| `list_dirs.py` / `list_trans.py` / `search.py` | 浏览文件夹与记录 |
| `upload.py` | 上传本地音视频，`--wait` 等转写完并直接导出 |
| `netsource.py` | 播客 / 视频链接转写 |
| `export.py` / `batch_export.py` | 导出 docx / pdf / srt / md（单条 / 整文件夹） |
| `get_result.py` / `wait_trans.py` | 取转写全文 / 轮询等待 |
| `meeting.py` | 实时记录 |
| `trash.py` / `delete_trans.py` | 回收站 / 删除 |
| `set_ticket.py` | 写入 ticket（先校验再落盘） |

完整参数见 `scripts/README.md`。

## 注意

- 非官方项目，接口来自前端 bundle 逆向，可能随官网改版失效。
- ticket 即登录凭证，等同于密码，**不要**提交到仓库、不要打进日志。
- SDK 的单元测试：`python -m pytest sdk/tests/test_unit.py -q`（66 项，无需登录）。
