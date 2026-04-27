---
name: odoorpc-agent-skill
description: >-
  Use proactively for Odoo work. Connect AI coding agents to Odoo through
  Python OdooRPC profiles, inspect live records, troubleshoot models, fields,
  access rights, modules, companies, connectors, imports, synchronization
  issues, odoo.conf, addons paths, backup restore, filestore checks, and
  guarded create/update/delete workflows.
license: MIT
compatibility: Requires Python 3.10+, network access to the target Odoo server, and either uv or a Python environment with odoorpc and PyYAML installed. Designed for Agent Skills-compatible tools including Claude Code, OpenCode, Codex, Manus, and similar coding agents.
metadata:
  version: "1.3.0"
  author: "customized-for-siy-han"
---

# OdooRPC Agent Skill

This skill gives an AI coding agent a safe, reusable workflow for connecting to Odoo with Python and OdooRPC.

It is intentionally **not tied to Claude Code**. Any agent that can read `SKILL.md` and run local scripts can use it: Claude Code, OpenCode, Codex, Manus, Cursor-like agents, local terminal agents, or other Agent Skills-compatible clients.

The skill is meant to be used **actively**. If the user asks about Odoo records, Odoo fields, Odoo business documents, Odoo connector data, Odoo settings, Odoo errors, Odoo version differences, or Odoo database state, do not treat this as a generic explanation task only. First consider whether a configured Odoo profile can answer the question with real data.

## Proactive invocation policy

Use this skill whenever the request is about Odoo and one of these is true:

- The user wants to **look up real Odoo data**, such as customers, vendors, contacts, products, variants, quotations, sale orders, purchase orders, invoices, bills, payments, stock, pickings, deliveries, receipts, tasks, projects, users, companies, or modules.
- The user asks **why something in Odoo looks wrong**, such as a company hierarchy, wrong partner address, missing product, wrong inventory number, missing order, connector import issue, failed synchronization, access-right issue, or model/field error.
- The user provides Odoo connection information and expects the agent to **save it and connect later**.
- The user asks for **Odoo model names, field names, record IDs, domains, counts, or examples based on their database**.
- The user asks the agent to **create, update, archive, deactivate, or delete** Odoo records.
- The user asks for **Odoo version-aware behavior** or says the system is Odoo 16, 17, 18, 19, Odoo Online, Odoo.sh, or a custom deployment.
- The user is working on a connector, migration, data sync, import/export, automation, or integration that depends on Odoo records.
- The user is doing **local Odoo development or operations**, including `odoo.conf` diagnosis, database selection, addons path detection, module documentation, module manifest work, Odoo.sh backup restore, filestore recovery, or admin/account repair.

Do **not** wait for the user to explicitly say “use OdooRPC”. If an Odoo profile exists and the user asks a database-specific Odoo question, use read-only commands to inspect the live system before answering, unless the user explicitly says not to connect.

## Common trigger words and entities

Treat these as strong signals to use or consider this skill:

- English: `Odoo`, `Odoo.sh`, `Odoo Online`, `partner`, `customer`, `vendor`, `contact`, `lead`, `opportunity`, `quotation`, `sale order`, `purchase order`, `invoice`, `bill`, `payment`, `journal entry`, `product`, `variant`, `stock`, `inventory`, `picking`, `delivery`, `receipt`, `warehouse`, `route`, `lot`, `serial`, `project`, `task`, `user`, `company`, `access rights`, `record rule`, `module`, `connector`, `import`, `sync`, `XML-RPC`, `JSON-RPC`, `odoorpc`.
- Chinese: `客户`, `联系人`, `供应商`, `报价单`, `销售订单`, `采购订单`, `发票`, `账单`, `付款`, `会计凭证`, `产品`, `规格`, `变体`, `库存`, `调拨`, `出库`, `入库`, `仓库`, `批次`, `序列号`, `项目`, `任务`, `用户`, `公司`, `多公司`, `权限`, `记录规则`, `模块`, `连接器`, `导入`, `同步`, `接口`, `字段`, `模型`, `数据库`, `模块介绍页`, `恢复备份`, `附件`, `文件存储`, `管理员密码`, `登录密码`.

## Default behavior by task type

| User intent | Agent behavior |
|---|---|
| “查一下 / 看一下 / 为什么显示这样” | Use read-only commands if a profile exists. Inspect model, fields, and sample records before explaining. |
| “这个字段叫什么 / 这个模型有什么字段” | Use `fields` against the relevant model. Do not guess if the database is reachable. |
| “有多少 / 哪些记录 / 列出” | Use `count` or `search-read` with a small `--limit`. |
| “帮我建一个记录” | Prepare a dry-run `create`; execute only with explicit user instruction and `--confirm CREATE`. |
| “帮我改成 / 修一下数据” | Search/read exact targets, show IDs and before snapshot, then dry-run update. Execute only with explicit instruction and `--confirm UPDATE`. |
| “删掉 / 清理掉” | Prefer archive/deactivate when possible. Delete only after exact IDs, before snapshot, explicit instruction, `--execute`, and `--confirm DELETE`. |
| “连接这个 Odoo” | Save or update a named profile in `~/.config/odoorpc/config.yaml`, then test login and detect version. |
| “以后都用这个库 / 这个客户系统” | Set the profile as default only if the user implies it should become the default. |
| “看一下 odoo.conf / 当前库 / addons 路径” | Inspect the active config file, distinguish active values from commented examples, and report database/addons/data_dir clearly. |
| “重置 admin 登录密码” | First distinguish Odoo login password from `admin_passwd` and PostgreSQL password; prefer `odoo-bin shell` + ORM. |
| “生成模块介绍页 / README 转 description” | Confirm the target is an Odoo module, inspect `__manifest__.py`, and create or update `static/description/index.html`. |
| “恢复 Odoo.sh 备份” | Identify backup type, confirm target database and filestore/data_dir, prefer safe restore paths, and warn about non-neutralized backups. |

## Core rule

Use the bundled scripts first. Do not write ad-hoc OdooRPC code unless the scripts are insufficient.

Preferred command style from the skill directory:

```bash
uv run scripts/odoo_config.py --help
uv run scripts/odoo_query.py --help
uv run scripts/odoo_mutate.py --help
```

Fallback when `uv` is unavailable:

```bash
python3 -m pip install --user "odoorpc>=0.10,<1" "PyYAML>=6,<7"
python3 scripts/odoo_config.py --help
python3 scripts/odoo_query.py --help
python3 scripts/odoo_mutate.py --help
```

## Configuration location

Connection profiles are stored under the user directory:

```text
~/.config/odoorpc/config.yaml
```

For compatibility with common typos, the scripts also detect `~/.config/odoorpc/config.ymal`; however, agents should create and update `config.yaml` as the canonical file.

The config file supports multiple Odoo connections:

```yaml
default_profile: local
profiles:
  local:
    host: 127.0.0.1
    port: 8069
    protocol: jsonrpc
    database: odoo
    username: admin
    password: admin
    timeout: 30
    odoo_version: "19.0"
  production:
    host: odoo.example.com
    port: 443
    protocol: jsonrpc+ssl
    database: prod_db
    username: admin@example.com
    password: "paste-api-key-or-password-here"
    timeout: 30
    odoo_version: "19.0"
```

Supported protocols usually include `jsonrpc`, `jsonrpc+ssl`, `xmlrpc`, and `xmlrpc+ssl`.

`odoo_version` is optional but strongly recommended. Store the major/minor Odoo version as a string such as `"16.0"`, `"17.0"`, `"18.0"`, or `"19.0"`. Agents should use it to choose version-aware model fields, workflows, and documentation assumptions. If the user provides the Odoo version with their connection details, save it in the profile. If the user does not know the version, connect once and run `scripts/odoo_config.py detect-version --profile <name> --save`.

## Saving user-provided connection config

When the user provides Odoo connection details and asks the agent to connect, save them automatically into a named profile unless the user explicitly says not to save.

Use `scripts/odoo_config.py set-profile`; never manually echo secrets into shell history when avoidable. Prefer `--password-stdin` for passwords/API keys:

```bash
printf '%s' 'SECRET_VALUE' | uv run scripts/odoo_config.py set-profile \
  --profile customer-dev \
  --host odoo.example.com \
  --port 443 \
  --protocol jsonrpc+ssl \
  --database customer_db \
  --username admin@example.com \
  --password-stdin \
  --odoo-version 19.0 \
  --set-default
```

If the user provides multiple Odoo systems, ask or infer a clear profile name such as `local`, `dev`, `staging`, `production`, `customer-a-prod`, or `nordic-match-prod`. If the user does not provide a name, create a short descriptive one from the host and purpose.

If the user did not provide the Odoo version, detect and save it after the profile is created:

```bash
uv run scripts/odoo_config.py detect-version --profile customer-dev --save
```

The config script sets restrictive permissions where supported:

- `~/.config/odoorpc`: `0700`
- `~/.config/odoorpc/config.yaml`: `0600`

## Available scripts

- `scripts/odoo_config.py` — create/list/show/remove local Odoo connection profiles and detect/save Odoo server versions.
- `scripts/odoo_query.py` — read-only Odoo operations: test login, inspect fields, search/read, count, and method calls marked as read-only.
- `scripts/odoo_mutate.py` — guarded create/update/delete operations with dry-run defaults, snapshots, confirmation phrases, deny rules, and JSON output.
- `scripts/odoo_common.py` — shared helper library used by the above scripts.

All scripts output JSON on stdout and diagnostics on stderr. Prefer `--limit` to keep output small.

## Read-only workflow

Use this workflow for inspection, troubleshooting, and reporting.

### 1. List configured profiles

```bash
uv run scripts/odoo_config.py list
```

### 2. Test login and show configured/detected Odoo version

```bash
uv run scripts/odoo_query.py test --profile local
```

To persist the detected server version into the profile config:

```bash
uv run scripts/odoo_config.py detect-version --profile local --save
```

### 3. Inspect a model

```bash
uv run scripts/odoo_query.py fields --profile local --model res.partner --fields name,email,phone,is_company
```

### 4. Search and read records

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model res.partner \
  --domain-json '[["is_company", "=", true]]' \
  --fields name,email,phone \
  --limit 10
```

Use JSON domains only. Do not use Python `eval` for domains.

## Practical Odoo playbooks

### Partner/customer/vendor lookup

Use `res.partner`. Start with `name`, `display_name`, `email`, `phone`, `mobile`, `is_company`, `parent_id`, `company_id`, `country_id`, `vat`, `customer_rank`, and `supplier_rank`.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model res.partner \
  --domain-json '[["name", "ilike", "ACME"]]' \
  --fields name,display_name,email,phone,is_company,parent_id,company_id,country_id,customer_rank,supplier_rank \
  --limit 10
```

### Sale quotation/order lookup

Use `sale.order`. Start with `name`, `partner_id`, `state`, `date_order`, `amount_total`, `currency_id`, `company_id`, `user_id`, and `invoice_status`.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model sale.order \
  --domain-json '[["name", "ilike", "S"]]' \
  --fields name,partner_id,state,date_order,amount_total,currency_id,company_id,user_id,invoice_status \
  --limit 10
```

### Product and variant lookup

Use `product.template` for product-level information and `product.product` for variants. Start with `name`, `default_code`, `barcode`, `active`, `sale_ok`, `purchase_ok`, `type`, `categ_id`, `list_price`, `standard_price`, and `qty_available` when available.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model product.product \
  --domain-json '[["default_code", "ilike", "SKU"]]' \
  --fields name,display_name,default_code,barcode,active,sale_ok,purchase_ok,type,categ_id,list_price,standard_price,qty_available \
  --limit 10
```

### Inventory/stock lookup

Use `stock.quant` for on-hand quantities, `stock.picking` for transfers, and `stock.move` for stock moves. Stock mutation is high risk; default to read-only diagnostics.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model stock.picking \
  --domain-json '[["name", "ilike", "WH"]]' \
  --fields name,partner_id,picking_type_id,location_id,location_dest_id,state,scheduled_date,origin,company_id \
  --limit 10
```

### Invoice/bill lookup

Use `account.move`. Accounting documents are protected. Read them freely when authorized, but do not post, cancel, reset, delete, or change them unless the user gives precise instructions and accepts business/legal risk.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model account.move \
  --domain-json '[["name", "ilike", "INV"]]' \
  --fields name,partner_id,move_type,state,payment_state,invoice_date,amount_total,currency_id,company_id \
  --limit 10
```

### Company hierarchy and multi-company questions

Use `res.company` and `res.partner`. For a company record, inspect `name`, `parent_id`, `partner_id`, `country_id`, and related partner address fields. Do not mutate `company_id`, `company_ids`, `parent_id`, or company address fields without explicit approval.

```bash
uv run scripts/odoo_query.py search-read \
  --profile local \
  --model res.company \
  --domain-json '[["name", "ilike", "Schaeffler"]]' \
  --fields name,parent_id,partner_id,country_id,company_registry,vat \
  --limit 10
```

### Access-right and security diagnostics

Use `res.users`, `ir.model.access`, and `ir.rule` in read-only mode. Never change groups or record rules unless the user explicitly asks for an admin/security change and the impact is reviewed.

## Create workflow

Creating records is state-changing and must be deliberate.

Default behavior is dry-run:

```bash
uv run scripts/odoo_mutate.py create \
  --profile local \
  --model res.partner \
  --values-json '{"name":"Demo Customer","email":"demo@example.com"}'
```

Actual creation requires `--execute` and a confirmation phrase:

```bash
uv run scripts/odoo_mutate.py create \
  --profile local \
  --model res.partner \
  --values-json '{"name":"Demo Customer","email":"demo@example.com"}' \
  --execute \
  --confirm CREATE
```

## Strict update rules

Updating existing records is high risk. Follow all rules below.

1. Never update records based only on a fuzzy name. First search/read and show the user the target IDs and key fields.
2. Always read a before-snapshot of the exact IDs and fields being changed.
3. Default to dry-run. Show the proposed diff before executing.
4. Actual update requires all of these:
   - User explicitly requested the update.
   - Exact model and IDs are known.
   - `--execute` is passed.
   - `--confirm UPDATE` is passed.
5. Do not update more than 20 records in one command unless the user explicitly requests a bulk operation and the agent has explained the blast radius.
6. Avoid updates that trigger mail/tracking unless required. Use `--quiet-mail` when appropriate.
7. Never update protected models/fields unless the user gives a very explicit administrator-level instruction and accepts the risk.
8. When the user asks for a broad fix, first translate it into exact model, exact domain, exact record IDs, exact fields, and exact new values.
9. Prefer normal Odoo business workflows over direct field edits when a business document has workflow state, but only execute workflow methods after explicit authorization.

Dry-run update:

```bash
uv run scripts/odoo_mutate.py update \
  --profile local \
  --model res.partner \
  --ids 12,13 \
  --values-json '{"category_id":[[6,0,[3]]]}'
```

Execute update:

```bash
uv run scripts/odoo_mutate.py update \
  --profile local \
  --model res.partner \
  --ids 12,13 \
  --values-json '{"category_id":[[6,0,[3]]]}' \
  --execute \
  --confirm UPDATE \
  --quiet-mail
```

## Strict delete rules

Deletion is the most dangerous operation.

1. Never delete by default.
2. Prefer archiving/deactivation when the model supports `active`.
3. Never delete invoices, accounting entries, stock moves/pickings, posted documents, users, companies, or configuration records unless the user gives a precise, written instruction and you have verified the legal/business impact.
4. Always read a before-snapshot of the exact IDs.
5. Actual delete requires all of these:
   - Exact model and IDs are known.
   - User explicitly asked to delete, not “clean up” or “remove from view”.
   - `--execute` is passed.
   - `--confirm DELETE` is passed.
   - Number of records is within the script limit.
6. If uncertain, stop and ask for confirmation instead of deleting.
7. For duplicate records, first propose merge/archive/deactivate where appropriate instead of unlink.

Dry-run delete:

```bash
uv run scripts/odoo_mutate.py delete \
  --profile local \
  --model res.partner \
  --ids 99
```

Execute delete:

```bash
uv run scripts/odoo_mutate.py delete \
  --profile local \
  --model res.partner \
  --ids 99 \
  --execute \
  --confirm DELETE
```

## Protected models and fields

## Local Odoo development and operations playbooks

Use these playbooks when the task is about a local/self-hosted Odoo deployment, module source tree, database restore, or server configuration rather than only live RPC record lookup.

### Global local-ops rules

- **Distinguish Odoo concepts before acting.** For “admin password”, decide whether the user means the Odoo login user password, `admin_passwd`, or PostgreSQL `db_user`/`db_password`.
- **Read the active instance configuration first.** For database-affecting work, inspect `odoo.conf` and identify `db_name`, `db_host`, `db_port`, `db_user`, `db_password`, `addons_path`, and `data_dir` where available.
- **Prefer Odoo framework operations.** Use `odoo-bin shell` + ORM for Odoo data changes when possible; avoid hand-writing password hashes or blindly editing business tables.
- **Keep changes minimal.** Only modify the requested database, user, module, or config entry; do not opportunistically change unrelated passwords, modules, or settings.
- **Report clear boundaries.** Say what changed, what did not change, and which database/module/user/config file was targeted.

### Reset Odoo login user `admin` password

Apply when the user asks to reset the Odoo backend login user `admin`, not the database user and not the Odoo database manager master password.

Required checks:

- Confirm the target is the Odoo application login user `admin`.
- Confirm the active database from `odoo.conf` or the running command/container.
- Verify a `res.users` record with `login='admin'` exists.
- Use `odoo-bin shell` + ORM; only fall back to direct SQL when the framework path is impossible and the user understands the risk.

Preferred ORM snippet:

```python
user = env['res.users'].search([('login', '=', 'admin')], limit=1)
assert user, 'admin user not found'
user.write({'password': '<NEW_PASSWORD>'})
env.cr.commit()
print(f'password updated for user id={user.id} login={user.login}')
```

Report using this shape:

```text
已处理当前 Odoo 数据库：<DB_NAME>

- 目标用户：admin
- 已执行操作：将 Odoo 登录密码改为 <REDACTED_OR_USER_PROVIDED_VALUE>
- 未修改：admin_passwd / PostgreSQL 用户密码
- 建议验证：使用 admin 登录 Odoo 页面
```

### Generate or maintain module description page

Apply when the user asks to generate an Odoo module introduction page, convert a module README into an app description page, maintain module documentation, or create `static/description/index.html`.

Execution rules:

- Confirm the target is an Odoo module by checking `__manifest__.py` or `__openerp__.py`.
- Prefer existing `README.md`, `README.rst`, `docs/`, manifest metadata, screenshots, and module source structure as inputs.
- Write the final app-store-style page to `static/description/index.html` and create the directory if needed.
- Keep the content specific to the module; do not turn a generic repository README into unrelated marketing copy.
- If converting Markdown, use the repository’s existing converter/tooling if present; otherwise use a minimal HTML structure compatible with Odoo module descriptions.

Report using this shape:

```text
已生成/更新 Odoo 模块介绍页：<MODULE_PATH>/static/description/index.html

- 来源文档：<README_OR_GENERATED_FROM_MODULE_STRUCTURE>
- 已覆盖内容：功能介绍、安装/配置、使用方式、注意事项
- 未处理：<KNOWN_GAPS_OR_NONE>
```

### Identify active database and addons paths from `odoo.conf`

Apply when the user asks which database is running, which config is active, where addons are loaded from, or why Odoo is using the wrong database/module path.

Execution rules:

- Locate the actual config used by the running service/container/command; do not assume a nearby sample file is active.
- Parse only active, uncommented values; do not treat commented examples as configuration.
- Report `db_name`, `db_host`, `db_port`, `db_user`, `addons_path`, `data_dir`, `dbfilter`, and relevant service/container command-line overrides.
- If multiple configs exist, explain the evidence for which one is active.
- Redact `db_password`, API keys, and other secrets.

Report using this shape:

```text
已识别当前 Odoo 配置：<ODOO_CONF_PATH>

- 数据库：<DB_NAME_OR_FILTER>
- 数据库连接：<HOST>:<PORT> / user=<DB_USER>
- addons_path：<PATHS>
- data_dir：<DATA_DIR_OR_DEFAULT_NEEDS_CONFIRMATION>
- 注意事项：<MULTI_DB_OR_DBFILTER_OR_OVERRIDES>
```

### Restore Odoo.sh backup and configure `odoo.conf`

Apply when the user asks to restore an Odoo.sh backup locally or on a server, configure `odoo.conf` after restore, recover a `dump.sql`/`.dump`/zip backup, or align filestore and addons paths.

Required checks:

- Identify the backup type: standard Odoo zip, `dump.sql`, PostgreSQL custom `.dump`, or a `nofs` backup without real filestore content.
- Confirm the target database name before overwriting or creating anything.
- Confirm `data_dir`; filestore must live under `<data_dir>/filestore/<DB_NAME>/`.
- Confirm `addons_path` includes all custom and enterprise modules required by the restored database.
- Warn that non-neutralized restores may trigger emails, scheduled actions, webhooks, payments, or external connectors.

Preferred restore paths:

```bash
python odoo-bin db load <DB_NAME> <BACKUP_ZIP> --force
python odoo-bin db load <DB_NAME> <BACKUP_ZIP> --force --neutralize
createdb -U <DB_USER> <DB_NAME>
psql -U <DB_USER> -d <DB_NAME> -f dump.sql
pg_restore --no-owner -U <DB_USER> -d <DB_NAME> backup.dump
```

Windows fallback:

- If `db load` cannot read a local path on Windows, do not conclude the backup is corrupt.
- Fall back by extracting `dump.sql` or `.dump`, creating the database, restoring with `psql`/`pg_restore`, then copying real filestore content if present.

`nofs` backup rule:

- Treat filename/content signs of `nofs` or an empty `filestore/` as a successful database-only backup with missing attachments.
- Clearly tell the user that images, attachments, documents, and binary assets may be unavailable even if SQL restore succeeds.

Default database naming rule:

```text
<project_name>_<YYYYMMDDHHMMSS>
```

If renaming after restore, use a filestore-aware process and update `odoo.conf` `db_name`; do not rename PostgreSQL only and leave filestore/config stale.

Validation checklist:

- Target database was created or overwritten intentionally.
- `odoo.conf` points to the restored database and correct `data_dir`.
- Odoo can load the registry, ideally via `odoo-bin shell --no-http --stop-after-init` or an equivalent startup check.
- Attachments/images/documents work when filestore is present.
- Missing filestore is documented as a known limitation for `nofs` backups.
- Missing addons/version mismatches are reported explicitly.

Report using this shape:

```text
已处理 Odoo 备份恢复：<BACKUP_PATH>

- 恢复目标数据库：<DB_NAME>
- 恢复方式：db load / psql / pg_restore
- filestore 状态：已恢复 / 缺失 / 待确认
- 已更新配置：db_name, db_host, db_port, db_user, db_password, addons_path, data_dir[, dbfilter]
- 当前风险：<RISKS>
- 建议验证：启动 Odoo，打开目标数据库并检查附件与模块加载情况
```

### Local-ops must not do

- Do not confuse `admin_passwd` with the Odoo login user `admin` password.
- Do not confuse PostgreSQL `db_user`/`db_password` with Odoo user credentials.
- Do not write `res_users.password` hashes by hand unless ORM is impossible.
- Do not silently modify several credential systems at once.
- Do not delete, deactivate, or recreate users without explicit authorization.
- Do not announce restore success until database, `odoo.conf`, `data_dir`, and filestore expectations are aligned.
- Do not ignore Odoo version, enterprise addons, or custom addons compatibility.
- Do not overwrite an existing local database without explicit confirmation.
- Do not assume SQL restore means attachments and images are available.
- Do not forget to update `odoo.conf` after restoring or renaming a database.

Treat these as protected. Read-only access is allowed; mutation requires exceptional user authorization and manual review.

Protected models include:

- `res.users`
- `res.company`
- `ir.config_parameter`
- `ir.model.access`
- `ir.rule`
- `ir.module.module`
- `account.move`
- `account.move.line`
- `stock.move`
- `stock.picking`
- `stock.quant`
- `payment.*`
- `account.*`
- `stock.*`
- `ir.*`

Protected fields include:

- `password`
- `groups_id`
- `company_id`
- `company_ids`
- `parent_id` on companies
- `active` on users/companies
- accounting state fields such as `state`, `payment_state`, `move_type`
- stock state/location fields such as `state`, `location_id`, `location_dest_id`, `quantity`, `reserved_quantity`, `inventory_quantity`
- any field containing `token`, `secret`, `key`, `password`, or `credential`

The mutation script enforces a denylist by default. Do not bypass it casually.

## Notification and tracking safety

When doing batch creates/updates that could trigger chatter messages or emails, prefer quiet context:

```json
{
  "mail_create_nosubscribe": true,
  "mail_notrack": true,
  "tracking_disable": true,
  "mail_auto_subscribe_no_notify": true
}
```

Use `--quiet-mail` in `scripts/odoo_mutate.py` to apply this context.

## Output handling

- Scripts print JSON to stdout.
- Errors should be treated as actionable diagnostics.
- Do not paste secrets into the final answer.
- Redact passwords/API keys when summarizing config.
- Save snapshots generated by mutation scripts; they are rollback/audit aids, not a full database backup.
- When discussing behavior or writing custom code, mention whether the answer is based on configured `odoo_version` or a detected server version.

## When scripts are insufficient

If a task requires a custom Odoo method call, first inspect the model and method behavior. For non-mutating calls, use `scripts/odoo_query.py call-readonly` only when the method is known to be safe. For mutating business workflows such as confirming sale orders, validating pickings, posting invoices, reconciling payments, changing stock quantities, cancelling documents, resetting posted documents, installing modules, changing access rules, or modifying users/companies, do not call raw methods until the user explicitly authorizes the workflow and the agent explains the expected effect.

## Agent response style when using this skill

- For read-only lookups, summarize what was checked: profile, model, domain, fields, and key result.
- For configuration, say which profile was saved and whether login/version detection succeeded. Never reveal the password or API key.
- For dry-run mutations, show the target IDs, before values, proposed values, and exact command needed to execute.
- For executed mutations, show the final status, affected IDs, and snapshot path if available.
- If the Odoo server is unreachable or credentials fail, provide the actionable error and the profile name; do not invent database results.
