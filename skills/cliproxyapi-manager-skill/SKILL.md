---
name: cliproxyapi-manager
description: Manage CLIProxyAPI or CLIProxyAPIPlus only: save CLIProxyAPI Management API URL and password under the user's home .config/cliproxyapi directory, call every CLIProxyAPI Management API endpoint, manage config/auth files/provider keys/model aliases/logs/usage/OAuth URLs, and work on Windows, Linux, and macOS without opening the web UI.
---

# CLIProxyAPI Manager Skill

Use this skill when the user asks an AI coding agent to manage **CLIProxyAPI / CLIProxyAPIPlus / CLI Proxy API** from the terminal.

This skill is intentionally **only about CLIProxyAPI**. Do **not** add opencode, Codex client, Claude Code client, Gemini CLI client, or other AI client configuration unless the user explicitly asks in a separate task.

## What this skill does

- Saves CLIProxyAPI Management API connection profiles locally.
- Reads and updates the CLIProxyAPI runtime configuration through `/v0/management`.
- Documents all CLIProxyAPI Management API endpoints in `references/management-api-full.md`.
- Lets the AI call every endpoint through the bundled `raw` command.
- Provides convenience commands for config, aliases, auth files, OpenAI-compatible providers, Vertex import, scalar toggles, and endpoint discovery.
- Redacts secrets by default when printing JSON.
- Works on Windows, Linux, and macOS.

## What this skill does not do

- It does not configure opencode.
- It does not configure OpenAI SDK clients.
- It does not call upstream model APIs directly.
- It does not store secrets in the repository, skill files, prompts, or examples.

## CLIProxyAPI Management API basics

Base URL format:

```text
<CLIProxyAPI_BASE_URL>/v0/management
```

Example local base URL:

```text
http://127.0.0.1:8317/v0/management
```

Authentication headers:

```http
Authorization: Bearer <MANAGEMENT_KEY>
```

or:

```http
X-Management-Key: <MANAGEMENT_KEY>
```

The bundled script uses `Authorization: Bearer ...`.

Content conventions:

- JSON requests: `Content-Type: application/json`
- YAML config upload: `Content-Type: application/yaml`
- Boolean/int/string endpoints expect `{ "value": ... }`
- Array replace endpoints accept either raw array or `{ "items": [...] }`
- Object-array patch endpoints usually accept `{ "index": 0, "value": {...} }` or a key-based matcher such as `{ "match": "...", "value": {...} }` / `{ "name": "...", "value": {...} }`

## Cross-platform paths

The Python script uses only standard library modules and supports Python 3.8+.

Saved connection file:

| System | Path |
|---|---|
| Windows | `%USERPROFILE%\.config\cliproxyapi\connections.json` |
| Linux | `~/.config/cliproxyapi/connections.json` |
| macOS | `~/.config/cliproxyapi/connections.json` |

Override path:

```bash
CLIPROXYAPI_CONFIG_DIR=/custom/path
```

Sensitive environment variables supported by the script:

```bash
CLIPROXYAPI_MANAGEMENT_KEY      # management password/key
CLIPROXYAPI_UPSTREAM_API_KEY    # upstream provider key for add-provider commands
```

## Installation

### Linux / macOS

```bash
mkdir -p ~/.agents/skills
unzip cliproxyapi-manager-skill.zip -d ~/.agents/skills
chmod +x ~/.agents/skills/cliproxyapi-manager-skill/scripts/cliproxyapi-manager.sh
~/.agents/skills/cliproxyapi-manager-skill/scripts/cliproxyapi-manager.sh paths
```

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.agents\skills" | Out-Null
Expand-Archive .\cliproxyapi-manager-skill.zip -DestinationPath "$env:USERPROFILE\.agents\skills" -Force
& "$env:USERPROFILE\.agents\skills\cliproxyapi-manager-skill\scripts\cliproxyapi-manager.ps1" paths
```

If PowerShell blocks local scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
& "$env:USERPROFILE\.agents\skills\cliproxyapi-manager-skill\scripts\cliproxyapi-manager.ps1" paths
```

### Windows CMD

```bat
mkdir "%USERPROFILE%\.agents\skills"
powershell -NoProfile -Command "Expand-Archive .\cliproxyapi-manager-skill.zip -DestinationPath $env:USERPROFILE\.agents\skills -Force"
"%USERPROFILE%\.agents\skills\cliproxyapi-manager-skill\scripts\cliproxyapi-manager.bat" paths
```

## Script path examples

Use the launcher for the current OS:

```bash
# Linux/macOS
./scripts/cliproxyapi-manager.sh paths

# Any OS with Python
python scripts/cliproxyapi_manager.py paths
```

```powershell
# Windows PowerShell
.\scripts\cliproxyapi-manager.ps1 paths

# Windows Python launcher
py -3 .\scripts\cliproxyapi_manager.py paths
```

```bat
REM Windows CMD
scripts\cliproxyapi-manager.bat paths
```

## First-time setup

When the user gives a CLIProxyAPI URL and management password/key, save them:

```bash
python scripts/cliproxyapi_manager.py setup \
  --url http://127.0.0.1:8317 \
  --key "MANAGEMENT_PASSWORD" \
  --name default \
  --default
```

If the user does not want the key visible in shell history, omit `--key`; the script prompts securely:

```bash
python scripts/cliproxyapi_manager.py setup --url http://127.0.0.1:8317
```

Or use an environment variable:

```bash
export CLIPROXYAPI_MANAGEMENT_KEY='MANAGEMENT_PASSWORD'
python scripts/cliproxyapi_manager.py setup --url http://127.0.0.1:8317 --no-prompt
```

Windows PowerShell:

```powershell
$env:CLIPROXYAPI_MANAGEMENT_KEY = 'MANAGEMENT_PASSWORD'
.\scripts\cliproxyapi-manager.ps1 setup --url http://127.0.0.1:8317 --no-prompt
```

## Core commands

Show paths:

```bash
python scripts/cliproxyapi_manager.py paths
```

List saved profiles without secrets:

```bash
python scripts/cliproxyapi_manager.py profiles
```

Test connection:

```bash
python scripts/cliproxyapi_manager.py test
```

Show all known CLIProxyAPI Management API endpoints:

```bash
python scripts/cliproxyapi_manager.py endpoints
python scripts/cliproxyapi_manager.py endpoints --json
```

Call any endpoint:

```bash
python scripts/cliproxyapi_manager.py raw GET /config
python scripts/cliproxyapi_manager.py raw GET /usage
python scripts/cliproxyapi_manager.py raw PATCH /debug --data '{"value":true}'
python scripts/cliproxyapi_manager.py raw DELETE '/api-keys?index=0'
```

Read config:

```bash
python scripts/cliproxyapi_manager.py config
python scripts/cliproxyapi_manager.py config --format yaml --output ./config.backup.yaml
```

Replace config YAML:

```bash
python scripts/cliproxyapi_manager.py put-config-yaml ./config.yaml
```

Set scalar values:

```bash
python scripts/cliproxyapi_manager.py set-value /debug true
python scripts/cliproxyapi_manager.py set-value /request-retry 5
python scripts/cliproxyapi_manager.py set-value /proxy-url socks5://127.0.0.1:1080
```

List model aliases from config:

```bash
python scripts/cliproxyapi_manager.py list-aliases
python scripts/cliproxyapi_manager.py list-aliases --json
```

## Manage OpenAI-compatible providers inside CLIProxyAPI

Add provider:

```bash
python scripts/cliproxyapi_manager.py openai-compat-add \
  --name openrouter \
  --base-url https://openrouter.ai/api/v1 \
  --api-key 'sk-or-v1-...' \
  --model-name 'moonshotai/kimi-k2:free' \
  --alias 'kimi-k2'
```

Use env var for the upstream key:

```bash
export CLIPROXYAPI_UPSTREAM_API_KEY='sk-or-v1-...'
python scripts/cliproxyapi_manager.py openai-compat-add \
  --name openrouter \
  --base-url https://openrouter.ai/api/v1 \
  --model-name 'moonshotai/kimi-k2:free' \
  --alias 'kimi-k2'
```

Add a new model alias to an existing provider:

```bash
python scripts/cliproxyapi_manager.py openai-compat-add-model \
  --name openrouter \
  --model-name 'openai/gpt-4.1' \
  --alias 'gpt-4.1-openrouter'
```

Delete a provider with raw API:

```bash
python scripts/cliproxyapi_manager.py raw DELETE '/openai-compatibility?name=openrouter'
```

## Manage auth files

List auth files:

```bash
python scripts/cliproxyapi_manager.py raw GET /auth-files
```

Download auth file:

```bash
python scripts/cliproxyapi_manager.py raw GET '/auth-files/download?name=acc1.json' --output ./acc1.json
```

Upload raw JSON auth file:

```bash
python scripts/cliproxyapi_manager.py auth-upload ./acc1.json --name acc1.json
```

Upload multipart auth file:

```bash
python scripts/cliproxyapi_manager.py auth-upload ./acc1.json --multipart
```

Delete one auth file:

```bash
python scripts/cliproxyapi_manager.py raw DELETE '/auth-files?name=acc1.json'
```

Delete all on-disk auth files:

```bash
python scripts/cliproxyapi_manager.py raw DELETE '/auth-files?all=true'
```

## Vertex import

```bash
python scripts/cliproxyapi_manager.py vertex-import ./service-account.json --location us-central1
```

## OAuth login URLs

Start OAuth and open returned URL manually:

```bash
python scripts/cliproxyapi_manager.py raw GET /anthropic-auth-url
python scripts/cliproxyapi_manager.py raw GET /codex-auth-url
python scripts/cliproxyapi_manager.py raw GET '/gemini-cli-auth-url?project_id=my-gcp-project'
python scripts/cliproxyapi_manager.py raw GET /antigravity-auth-url
```

Poll state:

```bash
python scripts/cliproxyapi_manager.py raw GET '/get-auth-status?state=STATE_FROM_AUTH_URL'
```

## Destructive-operation guidance for AI agents

Safe to do when asked generally:

- `GET /config`
- `GET /config.yaml`
- `GET /usage`
- `GET /logs`
- `GET /auth-files`
- `GET /openai-compatibility`
- `list-aliases`
- `endpoints`
- local `setup`, `profiles`, `paths`

Potentially destructive; only do when the user explicitly requests it:

- `PUT /config.yaml`
- `PUT` full-array replacement endpoints
- `DELETE /logs`
- `DELETE /api-keys`
- `DELETE /gemini-api-key`
- `DELETE /codex-api-key`
- `DELETE /claude-api-key`
- `DELETE /openai-compatibility`
- `DELETE /auth-files`
- `DELETE /auth-files?all=true`

## Troubleshooting

401 errors:

- Missing or wrong management key.
- Use `setup` again or set `CLIPROXYAPI_MANAGEMENT_KEY`.

403 errors:

- Remote management may be disabled for non-local connections.
- Use localhost, enable remote management in CLIProxyAPI config, or start with an allowed management password mode.

404 on every management endpoint:

- Management API may not be enabled, or no management secret is configured.

422 on `PUT /config.yaml`:

- YAML config failed server-side validation.

Connection refused:

- CLIProxyAPI is not running, URL/port is wrong, or firewall/proxy blocks it.

## Reference files

- `references/management-api-full.md`: full endpoint map and examples.
- `references/api-endpoints.json`: machine-readable endpoint list copied from the script.
- `references/agent-usage-guide.md`: short operating guide for weaker AI agents.
