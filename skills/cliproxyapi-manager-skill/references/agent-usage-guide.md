# Agent Usage Guide for CLIProxyAPI Manager

This guide is for AI agents that do not know CLIProxyAPI.

## Never guess the API base path

Always call:

```text
<base_url>/v0/management/<endpoint>
```

If the user gives `http://127.0.0.1:8317`, then `/config` means:

```text
http://127.0.0.1:8317/v0/management/config
```

## Always authenticate

Use:

```http
Authorization: Bearer <management password>
```

The bundled script does this for you.

## Use the bundled script whenever possible

First save URL/password:

```bash
python scripts/cliproxyapi_manager.py setup --url http://127.0.0.1:8317
```

Then test:

```bash
python scripts/cliproxyapi_manager.py test
```

Then call API:

```bash
python scripts/cliproxyapi_manager.py raw GET /config
```

## Important mental model

CLIProxyAPI has two different classes of keys:

1. **Management key/password**: used to control CLIProxyAPI through `/v0/management`.
2. **Upstream provider API keys / auth files**: used by CLIProxyAPI to call upstream AI providers.

Do not confuse them.

## Common tasks

### Read full config

```bash
python scripts/cliproxyapi_manager.py config
```

### Back up YAML config

```bash
python scripts/cliproxyapi_manager.py config --format yaml --output ./config.backup.yaml
```

### List model aliases

```bash
python scripts/cliproxyapi_manager.py list-aliases
```

### Add OpenAI-compatible provider

```bash
python scripts/cliproxyapi_manager.py openai-compat-add \
  --name openrouter \
  --base-url https://openrouter.ai/api/v1 \
  --api-key 'sk-...' \
  --model-name 'real/model/name' \
  --alias 'local-alias'
```

### Toggle debug

```bash
python scripts/cliproxyapi_manager.py set-value /debug true
```

### Raw patch example

```bash
python scripts/cliproxyapi_manager.py raw PATCH /request-retry --data '{"value":5}'
```

## Output rules

The script redacts secrets by default. Do not pass `--raw` unless the user explicitly needs raw local values and understands the risk.
