# odoorpc-agent-skill

A product-neutral Agent Skill for connecting AI coding agents to Odoo through Python OdooRPC. It is written to encourage agents to actively use live Odoo read-only inspection when a configured profile is available, while keeping write/delete operations strict and auditable.

This version also absorbs the local Odoo development/operations workflows from `odoo-dev-assistant`, so one Odoo skill can cover both live RPC inspection and server/module maintenance tasks.

## What it changes from the original example

- Generalized for Claude Code, OpenCode, Codex, Manus, and other Agent Skills-compatible agents.
- Uses `~/.config/odoorpc/config.yaml` profile-based configuration instead of environment variables.
- Supports multiple named Odoo connections, each with optional `odoo_version` metadata.
- Expands the Skill description, trigger words, decision policy, and Odoo task playbooks so agents proactively use it for real Odoo troubleshooting, lookup, and integration tasks.
- Adds local Odoo operations playbooks for `odoo.conf` inspection, active database/addons detection, `admin` login password reset, module `static/description/index.html` generation, and Odoo.sh backup restore with filestore checks.
- Adds strict safeguards around update and delete operations.
- Bundles reusable scripts with JSON output, `--help`, dry-run defaults, explicit confirmation flags, and a `detect-version --save` helper.

## Install location examples

Claude Code personal skill:

```bash
mkdir -p ~/.claude/skills
cp -R odoorpc-agent-skill ~/.claude/skills/odoorpc-agent-skill
```

Project-local skill:

```bash
mkdir -p .claude/skills
cp -R odoorpc-agent-skill .claude/skills/odoorpc-agent-skill
```

For OpenCode/Codex/other tools, place this directory wherever that tool reads Agent Skills or repository instructions.


## Proactive usage

This skill is designed to be used actively for Odoo work, not only when the user says “OdooRPC”. Agents should consider it whenever the user asks about Odoo customers, vendors, contacts, sale orders, purchase orders, invoices, bills, payments, products, variants, inventory, stock pickings, projects, tasks, users, companies, access rules, modules, connector imports, synchronization issues, Odoo model/field data, `odoo.conf`, addons paths, module docs, database restores, filestore issues, or Odoo login/admin repair.

Read-only commands are safe defaults when a configured profile exists. Create/update/delete operations remain dry-run by default and require explicit execution flags plus confirmation phrases.

## Quick check

```bash
uv run scripts/odoo_config.py --help
uv run scripts/odoo_query.py --help
uv run scripts/odoo_mutate.py --help
```


## Version-aware configuration

Each profile can store the Odoo version:

```yaml
profiles:
  customer-dev:
    host: odoo.example.com
    port: 443
    protocol: jsonrpc+ssl
    database: customer_db
    username: admin@example.com
    password: "replace-with-api-key-or-password"
    timeout: 30
    odoo_version: "19.0"
```

Create/update a profile with a known version:

```bash
printf '%s' 'SECRET_VALUE' | uv run scripts/odoo_config.py set-profile   --profile customer-dev   --host odoo.example.com   --port 443   --protocol jsonrpc+ssl   --database customer_db   --username admin@example.com   --password-stdin   --odoo-version 19.0   --set-default
```

Detect and save the server version after connecting:

```bash
uv run scripts/odoo_config.py detect-version --profile customer-dev --save
```
