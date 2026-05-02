# CLIProxyAPI Management API Full Reference

Base path:

```text
http://localhost:8317/v0/management
```

Authentication:

```http
Authorization: Bearer <MANAGEMENT_KEY>
```

or:

```http
X-Management-Key: <MANAGEMENT_KEY>
```

All requests, including localhost requests, need a valid management key. For remote access, CLIProxyAPI must allow remote management or be started/configured with a management password mode that enables it.

Request conventions:

- JSON by default: `Content-Type: application/json`
- YAML config upload: `Content-Type: application/yaml`
- Scalar update endpoints use `{ "value": <boolean|integer|string> }`
- Array replace endpoints usually accept a raw array or `{ "items": [...] }`
- Array patch endpoints usually accept `old/new`, `index/value`, or key-specific matchers.

## Usage Statistics

### GET `/usage`

Retrieve aggregated in-memory request metrics.

```bash
curl -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/usage
```

### GET `/usage/export`

Export a complete usage snapshot for backup/migration.

```bash
curl -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/usage/export > usage-export.json
```

### POST `/usage/import`

Import and merge a usage snapshot.

```bash
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  --data-binary @usage-export.json \
  http://localhost:8317/v0/management/usage/import
```

## Config

### GET `/config`

Get the full parsed config as JSON.

```bash
curl -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/config
```

### GET `/config.yaml`

Download the persisted YAML file as-is.

```bash
curl -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/config.yaml > config.yaml
```

### PUT `/config.yaml`

Replace the config with YAML. The server validates the YAML before saving.

```bash
curl -X PUT -H "Content-Type: application/yaml" \
  -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  --data-binary @config.yaml \
  http://localhost:8317/v0/management/config.yaml
```

## Latest Version

### GET `/latest-version`

Fetch latest release version string.

```bash
curl -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/latest-version
```

## Debug

### GET `/debug`

Get current debug state.

### PUT/PATCH `/debug`

Set debug state.

```json
{ "value": true }
```

## Logging to File

### GET `/logging-to-file`

Check whether file logging is enabled.

### PUT/PATCH `/logging-to-file`

Enable or disable file logging.

```json
{ "value": false }
```

## Log Files

### GET `/logs`

Stream recent log lines.

Optional query:

```text
after=<unix_timestamp>
```

### DELETE `/logs`

Remove rotated log files and truncate the active log.

## Request Error Logs

### GET `/request-error-logs`

List error request log files.

### GET `/request-error-logs/:name`

Download a specific error request log file.

The file name must be a safe `error-*.log` filename.

## Usage Statistics Toggle

### GET `/usage-statistics-enabled`

Check whether usage telemetry collection is active.

### PUT/PATCH `/usage-statistics-enabled`

Enable or disable usage telemetry.

```json
{ "value": true }
```

## Proxy Server URL

### GET `/proxy-url`

Get global proxy URL.

### PUT/PATCH `/proxy-url`

Set global proxy URL.

```json
{ "value": "socks5://127.0.0.1:1080" }
```

### DELETE `/proxy-url`

Clear global proxy URL.

## Quota Exceeded Behavior

### GET `/quota-exceeded/switch-project`

Get quota project-switch behavior.

### PUT/PATCH `/quota-exceeded/switch-project`

Set quota project-switch behavior.

```json
{ "value": false }
```

### GET `/quota-exceeded/switch-preview-model`

Get preview model switch behavior.

### PUT/PATCH `/quota-exceeded/switch-preview-model`

Set preview model switch behavior.

```json
{ "value": true }
```

## API Keys: Proxy Service Auth

These are client API keys accepted by the proxy service itself. They are not upstream provider keys.

### GET `/api-keys`

Return the full list.

### PUT `/api-keys`

Replace the full list.

```json
["k1", "k2", "k3"]
```

or:

```json
{ "items": ["k1", "k2", "k3"] }
```

### PATCH `/api-keys`

Modify one item.

By old/new:

```json
{ "old": "k2", "new": "k2b" }
```

By index/value:

```json
{ "index": 0, "value": "k1b" }
```

### DELETE `/api-keys?value=<key>`

Delete by value.

### DELETE `/api-keys?index=<n>`

Delete by index.

## Gemini API Key

### GET `/gemini-api-key`

List Gemini API key entries.

Entry shape:

```json
{
  "api-key": "AIzaSy...",
  "base-url": "https://generativelanguage.googleapis.com",
  "headers": { "X-Custom-Header": "custom-value" },
  "proxy-url": "",
  "excluded-models": ["gemini-1.5-flash"]
}
```

### PUT `/gemini-api-key`

Replace Gemini API key entries.

```json
[
  {
    "api-key": "AIzaSy-1",
    "headers": { "X-Custom-Header": "vendor-value" },
    "excluded-models": ["gemini-1.5-flash"]
  }
]
```

### PATCH `/gemini-api-key`

Update by index:

```json
{
  "index": 0,
  "value": {
    "api-key": "AIzaSy-1",
    "base-url": "https://custom.example.com",
    "headers": { "X-Custom-Header": "custom-value" },
    "proxy-url": "",
    "excluded-models": ["gemini-1.5-pro"]
  }
}
```

Update by api-key match:

```json
{
  "match": "AIzaSy-1",
  "value": {
    "api-key": "AIzaSy-1",
    "proxy-url": "socks5://proxy.example.com:1080",
    "excluded-models": ["gemini-1.5-pro-latest"]
  }
}
```

### DELETE `/gemini-api-key?api-key=<key>`

Delete by API key.

### DELETE `/gemini-api-key?index=<n>`

Delete by index.

## Codex API Key

### GET `/codex-api-key`

List Codex API key entries.

Entry shape:

```json
{
  "api-key": "sk-a",
  "base-url": "https://codex.example.com/v1",
  "proxy-url": "socks5://proxy.example.com:1080",
  "headers": { "X-Team": "cli" },
  "models": [ { "name": "real-model", "alias": "local-alias" } ],
  "excluded-models": ["gpt-4o-mini"]
}
```

### PUT `/codex-api-key`

Replace Codex API key entries.

### PATCH `/codex-api-key`

Update by index:

```json
{ "index": 1, "value": { "api-key": "sk-b2", "base-url": "https://c.example.com" } }
```

Update by match:

```json
{ "match": "sk-a", "value": { "api-key": "sk-a", "base-url": "https://codex.example.com/v1" } }
```

### DELETE `/codex-api-key?api-key=<key>`

Delete by API key.

### DELETE `/codex-api-key?index=<n>`

Delete by index.

Notes:

- `base-url` is required.
- Empty `base-url` in PUT/PATCH removes the entry.
- `headers` are optional.
- `excluded-models` are trimmed/lowercased/deduplicated.

## Request Retry Count

### GET `/request-retry`

Get integer retry count.

### PUT/PATCH `/request-retry`

Set integer retry count.

```json
{ "value": 5 }
```

## Max Retry Interval

### GET `/max-retry-interval`

Get maximum retry interval in seconds.

### PUT/PATCH `/max-retry-interval`

Set maximum retry interval in seconds.

```json
{ "value": 60 }
```

## Request Log

### GET `/request-log`

Get request logging toggle.

### PUT/PATCH `/request-log`

Set request logging toggle.

```json
{ "value": true }
```

## WebSocket Authentication

### GET `/ws-auth`

Check whether `/ws/*` endpoints require authentication.

### PUT/PATCH `/ws-auth`

Enable or disable WebSocket gateway authentication.

```json
{ "value": false }
```

## Claude API Key

### GET `/claude-api-key`

List Claude API key entries.

Entry shape:

```json
{
  "api-key": "sk-a",
  "base-url": "https://example.com/api",
  "proxy-url": "socks5://proxy.example.com:1080",
  "headers": { "X-Workspace": "team-a" },
  "models": [ { "name": "claude-3-5-sonnet-20241022", "alias": "claude-sonnet-latest" } ],
  "excluded-models": ["claude-3-opus"]
}
```

### PUT `/claude-api-key`

Replace Claude API key entries.

### PATCH `/claude-api-key`

Update by index or match.

By index:

```json
{ "index": 1, "value": { "api-key": "sk-b2", "base-url": "https://c.example.com" } }
```

By match:

```json
{ "match": "sk-a", "value": { "api-key": "sk-a", "proxy-url": "socks5://proxy.example.com:1080" } }
```

### DELETE `/claude-api-key?api-key=<key>`

Delete by API key.

### DELETE `/claude-api-key?index=<n>`

Delete by index.

## OpenAI Compatibility Providers

### GET `/openai-compatibility`

List OpenAI-compatible providers.

Provider shape:

```json
{
  "name": "openrouter",
  "base-url": "https://openrouter.ai/api/v1",
  "api-key-entries": [
    { "api-key": "sk", "proxy-url": "" }
  ],
  "models": [
    { "name": "moonshotai/kimi-k2:free", "alias": "kimi-k2" }
  ],
  "headers": { "X-Provider": "openrouter" }
}
```

### PUT `/openai-compatibility`

Replace all OpenAI-compatible providers.

```json
[
  {
    "name": "openrouter",
    "base-url": "https://openrouter.ai/api/v1",
    "api-key-entries": [ { "api-key": "sk", "proxy-url": "" } ],
    "models": [ { "name": "m", "alias": "a" } ],
    "headers": { "X-Provider": "openrouter" }
  }
]
```

### PATCH `/openai-compatibility`

Update by index:

```json
{
  "index": 0,
  "value": {
    "name": "openrouter",
    "base-url": "https://openrouter.ai/api/v1",
    "api-key-entries": [ { "api-key": "sk", "proxy-url": "" } ],
    "models": [],
    "headers": { "X-Provider": "openrouter" }
  }
}
```

Update by provider name:

```json
{
  "name": "openrouter",
  "value": {
    "name": "openrouter",
    "base-url": "https://openrouter.ai/api/v1",
    "api-key-entries": [ { "api-key": "sk", "proxy-url": "" } ],
    "models": [ { "name": "real-model", "alias": "alias" } ],
    "headers": {}
  }
}
```

Notes:

- Legacy `api-keys` input is accepted and migrated into `api-key-entries`.
- `headers` defines provider-wide HTTP headers.
- Blank headers are dropped.
- Providers without `base-url` are removed.
- Sending PATCH with empty `base-url` deletes that provider.

### DELETE `/openai-compatibility?name=<name>`

Delete by provider name.

### DELETE `/openai-compatibility?index=<n>`

Delete by index.

## OAuth Excluded Models

These configure per-provider model blocks for OAuth-based providers.

### GET `/oauth-excluded-models`

Get current map.

```json
{
  "oauth-excluded-models": {
    "openai": ["gpt-4.1-mini"],
    "claude": ["claude-3-5-haiku-20241022"]
  }
}
```

### PUT `/oauth-excluded-models`

Replace full map.

```json
{
  "openai": ["gpt-4.1-mini"],
  "claude": ["claude-3-5-haiku-20241022"]
}
```

or:

```json
{
  "items": {
    "openai": ["gpt-4.1-mini"]
  }
}
```

### PATCH `/oauth-excluded-models`

Upsert/delete a single provider entry.

Upsert:

```json
{ "provider": "claude", "models": ["claude-3-5-haiku-20241022"] }
```

Delete by sending empty models:

```json
{ "provider": "claude", "models": [] }
```

### DELETE `/oauth-excluded-models?provider=<provider>`

Delete all excluded models for a provider.

## Auth File Management

These manage JSON token files under `auth-dir`.

### GET `/auth-files`

List auth JSON token files.

Response includes fields such as:

```json
{
  "files": [
    {
      "id": "account.json",
      "name": "account.json",
      "provider": "claude",
      "label": "Claude Prod",
      "status": "ready",
      "status_message": "ok",
      "disabled": false,
      "unavailable": false,
      "runtime_only": false,
      "source": "file",
      "path": "/abs/path/auths/account.json",
      "size": 2345,
      "modtime": "2025-08-30T12:34:56Z",
      "email": "user@example.com",
      "account_type": "anthropic",
      "account": "workspace-1",
      "created_at": "2025-08-30T12:00:00Z",
      "updated_at": "2025-08-31T01:23:45Z",
      "last_refresh": "2025-08-31T01:23:45Z"
    }
  ]
}
```

Notes:

- `runtime_only: true` credentials only exist in memory and cannot be downloaded/deleted through file endpoints.
- If the runtime auth manager is unavailable, response may fall back to basic file scan fields.

### GET `/auth-files/download?name=<file.json>`

Download a single auth JSON file.

### POST `/auth-files`

Upload auth file.

Multipart:

```bash
curl -X POST -F 'file=@/path/to/acc1.json' \
  -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  http://localhost:8317/v0/management/auth-files
```

Raw JSON:

```bash
curl -X POST -H "Content-Type: application/json" \
  -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  -d @/path/to/acc1.json \
  'http://localhost:8317/v0/management/auth-files?name=acc1.json'
```

### DELETE `/auth-files?name=<file.json>`

Delete one on-disk auth JSON file.

### DELETE `/auth-files?all=true`

Delete all on-disk auth JSON files under `auth-dir`.

## Vertex Credential Import

### POST `/vertex/import`

Upload a Vertex service account key. Stores as `vertex-<project>.json` under `auth-dir`.

Multipart fields:

- `file`: service account JSON
- `location`: optional; defaults to `us-central1`

```bash
curl -X POST \
  -H "Authorization: Bearer <MANAGEMENT_KEY>" \
  -F 'file=@/path/to/my-project-sa.json' \
  -F 'location=us-central1' \
  http://localhost:8317/v0/management/vertex/import
```

## Login / OAuth URLs

These initiate provider login flows and return a URL to open in a browser. Tokens are saved under `auths/` once complete.

For Anthropic, Codex, Gemini CLI, and Antigravity, `?is_webui=true` can be appended when launching from the built-in UI.

### GET `/anthropic-auth-url`

Start Anthropic / Claude login.

Response:

```json
{ "status": "ok", "url": "https://...", "state": "anth-1716206400" }
```

### GET `/codex-auth-url`

Start Codex login.

Response:

```json
{ "status": "ok", "url": "https://...", "state": "codex-1716206400" }
```

### GET `/gemini-cli-auth-url?project_id=<PROJECT_ID>`

Start Google / Gemini CLI login. `project_id` is optional.

Response:

```json
{ "status": "ok", "url": "https://...", "state": "gem-1716206400" }
```

### GET `/antigravity-auth-url`

Start Antigravity login.

Response:

```json
{ "status": "ok", "url": "https://...", "state": "ant-1716206400" }
```

### GET `/get-auth-status?state=<state>`

Poll OAuth login flow status.

Possible responses:

```json
{ "status": "wait" }
```

```json
{ "status": "ok" }
```

```json
{ "status": "error", "error": "Authentication failed" }
```

## Error Responses

Generic errors:

- `400 Bad Request`: `{ "error": "invalid body" }`
- `401 Unauthorized`: `{ "error": "missing management key" }` or `{ "error": "invalid management key" }`
- `403 Forbidden`: `{ "error": "remote management disabled" }`
- `404 Not Found`: `{ "error": "item not found" }` or `{ "error": "file not found" }`
- `422 Unprocessable Entity`: `{ "error": "invalid_config", "message": "..." }`
- `500 Internal Server Error`: `{ "error": "failed to save config: ..." }`
