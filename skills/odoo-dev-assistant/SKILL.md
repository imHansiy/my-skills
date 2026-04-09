---
name: odoo-dev-assistant
description: Odoo 开发与运维辅助技能。用于处理 Odoo 模块开发、配置排查、数据库操作、账号与权限修复、文档生成等任务。当前已内置重置 Odoo 登录用户 admin 密码、生成模块介绍页文档、识别当前运行数据库与 addons 路径、恢复 Odoo.sh 备份并配置 odoo.conf 等工作流，后续可继续扩展更多 Odoo 场景。
metadata:
  author: imHansiy
  version: "0.1.0"
  tags:
    - odoo
    - erp
    - module
    - database
    - maintenance
---

# Odoo 开发与运维辅助技能

这是一个面向 **Odoo 日常开发、排查和维护** 的总入口技能，不是单一功能 skill。

当前版本已内置四个工作流：**重置 Odoo 登录用户 `admin` 的密码**、**生成/维护 Odoo 模块介绍页文档**、**根据 `odoo.conf` 识别当前运行数据库与 addons 路径**，以及 **恢复 Odoo.sh 备份并配置 `odoo.conf`**。后续凡是与 Odoo 相关的能力，都应优先沉淀到这个 skill 中，而不是不断新建很多零散的 Odoo 子 skill。

## When to Apply

- 用户在做 Odoo 模块开发、运行调试、配置排查、账号修复、数据库维护
- 用户提到 Odoo 的 `odoo.conf`、模块目录、`__manifest__.py`、addons、升级模块、用户权限、数据库记录
- 用户希望把某个 Odoo 操作沉淀为可复用流程

## Skill Positioning

这个 skill 是一个 **Odoo 任务总入口**。

当前已包含：

1. 重置 Odoo 登录用户 `admin` 密码
2. 生成或维护 Odoo 模块文档与 `static/description/index.html`
3. 根据 `odoo.conf` 识别当前运行数据库与 addons 路径
4. 恢复 Odoo.sh 备份并配置 `odoo.conf`

后续建议继续增加：

5. 升级指定模块
6. 初始化/检查自定义模块结构
7. 修复常见 XML / Python / security / access rights 问题
8. 数据修复与脚本化维护

## Global Rules

1. **先区分 Odoo 概念，再动手**。
   对用户提到的“管理员密码”“数据库密码”“admin 密码”这类词，必须先判断是：
   - Odoo 登录用户密码
   - `admin_passwd`
   - PostgreSQL 用户密码

2. **优先读取当前实例配置**。
   任何数据库相关操作，优先读取 `odoo.conf`，确认：
   - `db_name`
   - `db_host`
   - `db_port`
   - `db_user`
   - `db_password`
   - `addons_path`

3. **优先用 Odoo 框架方式操作 Odoo 数据**。
   能用 `odoo-bin shell` + ORM 处理的，不要直接手写底层哈希或盲改业务表。

4. **最小范围修改**。
   只改用户要求的对象，不顺带改别的配置、别的密码、别的模块。

5. **结果汇报必须明确边界**。
   要明确告诉用户：
   - 改了什么
   - 没改什么
   - 当前操作的是哪个数据库 / 哪个模块 / 哪个用户

## Workflow 1: 重置 Odoo 登录用户 admin 密码

这个工作流用于**修改 Odoo 应用内登录用户 `admin` 的密码**，不是 PostgreSQL 账号密码，也不是 `odoo.conf` 里的 `admin_passwd`。

### When to Apply

- 用户说“把 Odoo 登录用户名 admin 的密码改为 xxx”
- 用户说“重置 Odoo admin 登录密码”
- 用户说“修改数据库里 admin 登录密码”，但上下文明确是在说 Odoo 后台登录账号

### Must Distinguish First

必须先确认目标不是下面两种：

1. **Odoo 管理主密码 (`admin_passwd`)**
2. **PostgreSQL 用户密码 (`db_user` / `db_password`)**

### Execution Steps

1. 读取当前 `odoo.conf`，确定活动数据库
2. 明确告诉用户当前将操作哪个数据库
3. 确认 `res_users` 中存在 `login='admin'` 的用户
4. 使用 `odoo-bin shell` + ORM 更新密码
5. 提醒用户通过 Odoo 登录页做最终验证

### Preferred ORM Snippet

```python
user = env['res.users'].search([('login', '=', 'admin')], limit=1)
assert user, 'admin user not found'
user.write({'password': '<NEW_PASSWORD>'})
env.cr.commit()
print(f'password updated for user id={user.id} login={user.login}')
```

### Report Template

```text
已处理当前 Odoo 数据库：<DB_NAME>

- 目标用户：admin
- 已执行操作：将 Odoo 登录密码改为 <NEW_PASSWORD>
- 未修改：admin_passwd / PostgreSQL 用户密码
- 建议验证：使用 admin / <NEW_PASSWORD> 登录 Odoo 页面
```

## Workflow 2: 生成或维护 Odoo 模块介绍页文档

这个工作流用于把 Odoo 模块中的 Markdown 文档整理为 `static/description/index.html`，或者在缺少文档时根据模块结构自动生成一份可用的介绍内容。

### When to Apply

- 用户说“给这个 Odoo 模块生成介绍页”
- 用户说“把 README 转成 Odoo 模块 description 页面”
- 用户说“帮我维护模块文档”
- 用户需要生成 `static/description/index.html`

### Must Distinguish First

必须先确认当前对象是 **Odoo 模块文档/介绍页**，而不是普通项目 README、美化官网页面或通用 HTML 文档。

### Execution Steps

1. 确认目标目录是否是 Odoo 模块，优先检查是否存在 `__manifest__.py`
2. 确定文档来源：
   - 用户显式指定的 Markdown 文件
   - 自动查找 `docs/README.md`、`docs/index.md`、`dos/README.md` 或根目录 `README.md`
3. 如果没有现成文档，则读取 `__manifest__.py` 与模块结构，生成 `docs/AUTO_SUMMARY.md`
4. 优先使用 `npx markdown-to-html-cli` 转换为 `static/description/index.html`
5. 补足基础样式，确保输出符合 Odoo `description` 页面使用场景
6. 如存在本地图片，确保资源路径可用，必要时迁移到 `static/description` 下

### Preferred Conversion Command

```bash
npx markdown-to-html-cli --source <SOURCE_MD> --output static/description/index.html
```

### Content Rules

- 若自动总结，至少包含：
  - 模块标题
  - 单句摘要（Summary）
  - 核心功能点（Features）
  - 依赖说明（Dependencies）
- 生成结果应具备清晰层级，而不是只输出一整块纯文本
- 页面样式应克制、整洁、适合 Odoo 后台展示，不要做成营销落地页风格

### Report Template

```text
已处理 Odoo 模块文档：<MODULE_PATH>

- 文档源：<SOURCE_MD>
- 输出文件：static/description/index.html
- 已执行操作：转换/生成模块介绍页
- 如无原始文档：已补充自动总结内容
```

## Workflow 3: 根据 `odoo.conf` 识别当前运行数据库与 addons 路径

这个工作流用于在 Odoo 项目中快速确认当前实例实际连接的数据库、PostgreSQL 连接参数，以及当前生效的 `addons_path`，适合排查“现在到底跑的是哪个库、哪个模块路径”的问题。

### When to Apply

- 用户说“读取 `odoo.conf` 现在正在使用的”
- 用户说“看看当前 Odoo 连的是哪个数据库”
- 用户说“确认当前 addons 路径”
- 用户在 Docker / 多数据库 / 多套 addons 环境里排查实例配置

### Must Distinguish First

必须先区分以下几个概念：

1. **当前配置文件声明的数据库**：例如 `db_name`
2. **PostgreSQL 连接参数**：例如 `db_host` / `db_port` / `db_user` / `db_password`
3. **Odoo 模块搜索路径**：例如 `addons_path`

如果项目里有多个配置文件，必须先确认当前要读的是哪一个 `odoo.conf`。

### Execution Steps

1. 读取目标 `odoo.conf`
2. 提取关键配置：
   - `db_name`
   - `db_host`
   - `db_port`
   - `db_user`
   - `db_password`
   - `addons_path`
   - 如有必要也包括 `http_port`、`admin_passwd`
3. 明确区分哪些是：
   - Odoo 数据库名
   - PostgreSQL 连接账户
   - Odoo 模块路径
4. 如配置中存在多组被注释的候选值，只报告当前未注释、实际生效的那一组
5. 回答时直接给出当前实例实际使用的值，不要让用户自己再从原文件里找

### Report Template

```text
当前 Odoo 配置文件：<CONF_PATH>

- 数据库名：<DB_NAME>
- PostgreSQL 地址：<DB_HOST>:<DB_PORT>
- PostgreSQL 用户：<DB_USER>
- PostgreSQL 密码：<DB_PASSWORD>
- addons_path：<ADDONS_PATH>

说明：以上为当前未注释、实际生效的配置；这不等同于 Odoo 登录用户密码。
```

## Workflow 4: 恢复 Odoo.sh 备份并配置 `odoo.conf`

这个工作流用于把 Odoo.sh 或 Odoo 导出的备份恢复到本地开发环境，并把 `odoo.conf` 配置到可启动、可连接、可加载附件的状态。目标不是只把数据库“导进去”，而是让本地 Odoo 实例可以正确打开恢复后的数据库。

### When to Apply

- 用户说“帮我把 Odoo.sh 导出的备份恢复到本地”
- 用户说“导入这个 `.zip` / `.dump` / `dump.sql` 到本地 Odoo”
- 用户说“恢复数据库后顺便把 `odoo.conf` 配好”
- 用户把备份包交给 AI，希望 AI 自动恢复数据库、复制 filestore、更新配置

### Must Distinguish First

必须先识别当前是哪一种恢复输入：

1. **标准 Odoo 备份压缩包**：例如 `.zip`，优先走 `odoo-bin db load`
2. **已解压备份目录**：例如包含 `dump.sql`、`.dump`、`filestore/`
3. **只给了数据库 dump，没有 filestore**
4. **只给了 filestore，没有数据库 dump**

还必须先确认以下信息：

- 目标数据库名是什么
- 本地 Odoo 版本与备份来源是否同大版本
- 本地是否具备所需 enterprise / custom addons
- `odoo.conf` 应该使用哪个文件作为当前配置

### Execution Steps

1. 识别备份格式，并决定恢复路径：
   - 如果是标准 Odoo `.zip` 备份，优先使用 `odoo-bin db load <db> <backup.zip> --force`
   - 如果已解压为 `dump.sql` / `.dump` + `filestore/`，走手动恢复路径
   - 如果在 Windows 本地环境下，`odoo-bin db load` 直接接收本地文件路径失败（例如被当成 URL 处理），不要反复猜参数，直接回退到手动恢复路径
2. 在恢复前确认：
   - PostgreSQL 连接参数可用：`db_host`、`db_port`、`db_user`、`db_password`
   - 目标数据库名已确定，且是否允许覆盖现有数据库
   - 本地有足够磁盘空间
   - 自定义模块路径和企业版代码已包含在 `addons_path` 中或可被补齐
   - 是否需要按统一规则把恢复后的数据库命名为“项目名 + 当前年月日时间”
3. 如果走 `db load`：
   - 使用 Odoo 官方 CLI 恢复备份
   - 如为本地调试环境，优先考虑 `--neutralize`
4. 如果走手动恢复：
   - `dump.sql` 使用 `createdb + psql`
   - `.dump` 使用 `createdb + pg_restore`
   - 再把 `filestore/` 放到 `data_dir/filestore/<db_name>/`
5. 更新或确认 `odoo.conf` 至少包含：
   - `db_name`
   - `db_host`
   - `db_port`
   - `db_user`
   - `db_password`
   - `addons_path`
   - `data_dir`
   - 如有多数据库或本地环境混用，再补 `dbfilter`
6. 启动 Odoo 并验证：
   - 数据库能被识别
   - Odoo 能启动
   - 自定义模块不会因缺失路径而报错
   - 附件、图片、二进制资源能正常读取，说明 filestore 对齐成功
7. 明确向用户报告：
   - 当前恢复使用了哪条路径
   - 哪些配置已改
   - 哪些风险仍存在，例如版本不一致、模块缺失、filestore 缺失

### Windows Fallback Rule

在 Windows 本地环境里，如果 `odoo-bin db load` 对本地 zip 路径报类似“把路径当作 URL 处理”的错误，不要继续在路径格式上盲试多轮。此时应直接切到手动恢复流程：

1. 从 zip 中解出 `dump.sql` 或 `.dump`
2. 创建目标数据库
3. 使用 `psql` 或 `pg_restore` 导入
4. 如有真实 filestore，再复制到 `data_dir/filestore/<db_name>/`

这个回退规则优先保证恢复成功，而不是执着于必须走 `db load`。

### `nofs` Backup Rule

如果备份文件名、目录结构或压缩包内容显示它是 `nofs` 备份，或者 `filestore/` 目录存在但没有实际文件，则必须把它视为 **数据库恢复成功但附件资源不完整** 的场景。

此时必须明确告诉用户：

- 数据库本身可以恢复并启动
- 但附件、图片、文档、二进制资源可能缺失
- 这不是 SQL 恢复失败，而是备份本身不含真实 filestore

### Default Naming Rule

如果用户希望恢复后的数据库名更易管理，默认优先采用：

```text
<project_name>_<YYYYMMDDHHMMSS>
```

例如：

```text
shanghaimeowai_winston1_20260409103933
```

恢复完成后，如用户要求按此规则命名：

1. 先完成数据库恢复
2. 再用 filestore-aware 的数据库重命名方式处理
3. 同步更新 `odoo.conf` 中的 `db_name`

不要只改 PostgreSQL 数据库名而忽略 Odoo 配置和潜在 filestore 目录。

### Preferred Restore Paths

#### A. 标准 Odoo 备份压缩包

```bash
python odoo-bin db load <DB_NAME> <BACKUP_ZIP> --force
```

如本地调试环境需要安全中性化，可考虑：

```bash
python odoo-bin db load <DB_NAME> <BACKUP_ZIP> --force --neutralize
```

#### B. 手动恢复 `dump.sql`

```bash
createdb -U <DB_USER> <DB_NAME>
psql -U <DB_USER> -d <DB_NAME> -f dump.sql
```

#### C. 手动恢复 `.dump`

```bash
createdb -U <DB_USER> <DB_NAME>
pg_restore --no-owner -U <DB_USER> -d <DB_NAME> backup.dump
```

#### D. 恢复 filestore

把 `filestore/` 放到：

```text
<data_dir>/filestore/<DB_NAME>/
```

如果 `data_dir` 未显式配置，必须先确认当前 Odoo 实例实际使用的默认目录，再复制过去。

### Config Rules

- `data_dir` 是强制检查项，不是可选项；它决定 Odoo 到哪里找 filestore
- `addons_path` 必须覆盖恢复后的数据库所依赖的自定义模块和企业版模块
- `dbfilter` 在多数据库环境里非常重要，可避免用户打开错误数据库
- `admin_passwd` 与恢复数据库本身无关，不要混为一谈

### Validation Checklist

- 目标数据库已成功创建或覆盖
- `odoo.conf` 指向正确数据库
- Odoo 启动后能看到目标库
- 登录后附件、图片、文档可正常打开
- 没有因为缺少 addons 路径导致模块加载失败
- 若未中性化，已明确提醒用户可能触发邮件、定时任务、Webhook、支付或外部连接器
- 在可能的情况下，至少做一次 `odoo-bin shell --no-http --stop-after-init` 或等价 registry 加载验证，确认数据库不是“只导入成功但 Odoo 打不开”
- 如果是 `nofs` 包，应把“附件缺失预期”标注为已知风险，而不是把它计入数据库恢复失败

### Report Template

```text
已处理 Odoo 备份恢复：<BACKUP_PATH>

- 恢复目标数据库：<DB_NAME>
- 恢复方式：db load / psql / pg_restore
- filestore 状态：已恢复 / 缺失 / 待确认
- 已更新配置：db_name, db_host, db_port, db_user, db_password, addons_path, data_dir[, dbfilter]
- 当前风险：<RISKS>
- 建议验证：启动 Odoo，打开目标数据库并检查附件与模块加载情况
```

## Must Not Do

- 不要把 `admin_passwd` 误当成 Odoo 登录用户 `admin` 的密码
- 不要把 `db_user` / `db_password` 误当成 Odoo 登录用户密码
- 不要直接手写 `res_users.password` 哈希，除非 Odoo ORM 方式不可用
- 不要在用户没确认时顺带修改多个密码体系
- 不要擅自删除、禁用或重建 Odoo 用户
- 不要把普通仓库 README 当作 Odoo 模块介绍页直接硬套，除非已确认目标是模块文档
- 不要生成与 Odoo 模块场景不匹配的过度营销化页面
- 不要把被注释掉的候选配置当成当前生效配置
- 不要在 filestore 未对齐时就宣布“恢复成功”
- 不要忽略 Odoo 版本、enterprise/custom addons 与备份数据库之间的匹配问题
- 不要在未确认的情况下覆盖现有本地数据库
- 不要只恢复 SQL 却默认附件和图片会自动可用
- 不要在 Windows 下因为 `db load` 读本地路径失败就误判“备份损坏”
- 不要恢复完数据库却忘记同步 `odoo.conf` 的 `db_name` 和 `data_dir`

## How to Extend This Skill Later

后续新增 Odoo 能力时，直接在本文件里继续追加新的 workflow 分节，例如：

- `## Workflow 5: 升级指定模块`
- `## Workflow 6: 生成模块初始化骨架`
- `## Workflow 7: 排查 access rights 与 security rule`
- `## Workflow 8: 根据 odoo.conf 与 docker 环境定位数据库实例`

保持统一结构：

1. When to Apply
2. Must Distinguish First
3. Execution Steps
4. Report Template
5. Must Not Do
