# odoo-agent-skill

A product-neutral Agent Skill for Odoo implementation, troubleshooting, validation, and customer delivery work. It encourages agents to use real evidence from configured Odoo profiles, browser UI verification, local source/configuration inspection, and validation artifacts before writing answers or customer-facing demo scripts.

Python OdooRPC profiles are still supported for live record inspection and guarded data changes, but RPC is only one access method. The skill also covers server/module maintenance tasks, Odoo.sh backup restore, filestore checks, and reproducible customer recording documents.

## What it changes from the original example

- Generalized for Claude Code, OpenCode, Codex, Manus, and other Agent Skills-compatible agents.
- Uses `~/.config/odoorpc/config.yaml` profile-based configuration for RPC-backed live data access instead of environment variables.
- Supports multiple named Odoo connections, each with optional `odoo_version` metadata.
- Expands the Skill description, trigger words, decision policy, and Odoo task playbooks so agents proactively use it for real Odoo troubleshooting, lookup, integration, browser verification, and customer demo documentation tasks.
- Adds local Odoo operations playbooks for `odoo.conf` inspection, active database/addons detection, `admin` login password reset, module `static/description/index.html` generation, and Odoo.sh backup restore with filestore checks.
- Adds strict safeguards around update and delete operations.
- Bundles reusable scripts with JSON output, `--help`, dry-run defaults, explicit confirmation flags, and a `detect-version --save` helper.

## Install location examples

Claude Code personal skill:

```bash
mkdir -p ~/.claude/skills
cp -R odoo-agent-skill ~/.claude/skills/odoo-agent-skill
```

Project-local skill:

```bash
mkdir -p .claude/skills
cp -R odoo-agent-skill .claude/skills/odoo-agent-skill
```

For OpenCode/Codex/other tools, place this directory wherever that tool reads Agent Skills or repository instructions.


## Proactive usage

This skill is designed to be used actively for Odoo work, not only when the user names a specific tool. Agents should consider it whenever the user asks about Odoo customers, vendors, contacts, sale orders, purchase orders, invoices, bills, payments, products, variants, inventory, stock pickings, projects, tasks, users, companies, access rules, modules, connector imports, synchronization issues, Odoo model/field data, browser workflow validation, customer demo scripts, `odoo.conf`, addons paths, module docs, database restores, filestore issues, or Odoo login/admin repair.

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
  <profile-name>:
    host: <odoo-host>
    port: 443
    protocol: jsonrpc+ssl
    database: <database-name>
    username: <login-or-email>
    password: "replace-with-api-key-or-password"
    timeout: 30
    odoo_version: "19.0"
```

Create/update a profile with a known version:

```bash
printf '%s' 'SECRET_VALUE' | uv run scripts/odoo_config.py set-profile   --profile <profile-name>   --host <odoo-host>   --port 443   --protocol jsonrpc+ssl   --database <database-name>   --username <login-or-email>   --password-stdin   --odoo-version 19.0   --set-default
```

Detect and save the server version after connecting:

```bash
uv run scripts/odoo_config.py detect-version --profile <profile-name> --save
```
