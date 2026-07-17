---
name: telecom-gateway-portmap
description: Operate China Telecom intelligent gateway (LuCI, e.g. ZTE ZXHN F4600T) for login and port mapping. Use when the user wants to log into 192.168.1.1/cgi-bin/luci, add/list/enable/disable/delete port-forward rules, or automate 电信智能网关 端口映射 / 虚拟服务 / NAT 转发.
license: MIT
metadata:
  author: imHansiy
  version: "0.1.1"
---

# Telecom Gateway Port Map

Use `scripts/gateway-portmap.mjs` for deterministic login and port-map operations against China Telecom intelligent gateways that expose LuCI at `http://192.168.1.1/cgi-bin/luci` (confirmed on ZXHN F4600T). Prefer the script over replaying browser clicks.

## Safety

- Never put the gateway password in git, commit messages, logs, or the final chat reply.
- Do not print `sysauth` cookies or CSRF tokens unless the user explicitly asks for debug output.
- Port mapping exposes LAN services to WAN. Confirm target host/port with the user before `add` when intent is ambiguous.
- Session idles out after ~5 minutes of inactivity; re-login if a write returns login HTML or fails auth.
- Config file may contain the password in plaintext under the user home directory. Treat it as secret; do not copy it into the repo.

## Config (mandatory first step)

Config path (fixed):

| OS | Path |
|----|------|
| Windows | `%USERPROFILE%\.config\telecom-gateway.yaml` |
| Linux / macOS | `~/.config/telecom-gateway.yaml` |

Schema:

```yaml
baseUrl: http://192.168.1.1
username: useradmin
password: <gateway-password>
```

### Always resolve config before any gateway call

1. Run:

```powershell
node scripts/gateway-portmap.mjs config show
```

2. Inspect JSON:
   - `ready: true` → use saved defaults; **do not** re-ask for username/password.
   - `ready: false` and `missing` lists fields → **stop gateway work**. Ask the user once for every missing field (at least **username** and **password**; `baseUrl` defaults to `http://192.168.1.1` if omitted).

3. When the user provides credentials, save immediately:

```powershell
node scripts/gateway-portmap.mjs config set `
  --base-url http://192.168.1.1 `
  --username useradmin `
  --password-stdin
```

Pass the password only through stdin (or the agent’s secure subprocess stdin). Example PowerShell:

```powershell
"plain-password-here" | node scripts/gateway-portmap.mjs config set --username useradmin --password-stdin
```

4. Re-run `config show` and confirm `ready: true` before `list` / `add` / etc.

### Empty or missing config — required agent behaviour

If the config file is missing, empty, or lacks `username`/`password`:

1. Tell the user clearly that gateway credentials are not saved yet.
2. Ask for:
   - 路由器管理地址（默认 `http://192.168.1.1`，可改）
   - 用户名（常见 `useradmin`）
   - 密码
3. Save with `config set` as above.
4. Only then continue the original task.

Do **not** invent a password. Do **not** skip saving after the user provides credentials. Do **not** keep re-prompting on later turns once `ready: true`.

### Override order (runtime)

1. Explicit CLI flags (`--base-url`, `--username`, `--password` / `--password-stdin`)
2. Env `TELECOM_GATEWAY_PASSWORD` (password only)
3. Saved `~/.config/telecom-gateway.yaml`

Gateway operations fail with exit code `2` and JSON `needConfig: true` when password cannot be resolved — treat that as “ask user + config set”, not as a hard crash.

## Workflow

### 1. Resolve config (see above)

Completion: `config show` → `ready: true`.

### 2. List existing rules

```powershell
node scripts/gateway-portmap.mjs list
```

Completion: prints `count` and each rule (`desp`, `client`, `protocol`, `exPort`, `inPort`, `enable`).

### 3. Add a mapping

Collect: service name, LAN IP, protocol (`TCP`|`UDP`|`BOTH`), external port, internal port.

```powershell
node scripts/gateway-portmap.mjs add `
  --name "my-service" `
  --client 192.168.1.10 `
  --protocol TCP `
  --ex-port 2222 `
  --in-port 22
```

Completion: `retVal: 0` and the rule appears in a subsequent `list`.

### 4. Enable / disable / delete

```powershell
node scripts/gateway-portmap.mjs enable --name "my-service"
node scripts/gateway-portmap.mjs disable --name "my-service"
node scripts/gateway-portmap.mjs del --name "my-service" --yes
```

Bulk:

```powershell
node scripts/gateway-portmap.mjs enable-all
node scripts/gateway-portmap.mjs disable-all
```

### 5. Report to user

Summarize: gateway base URL, rule name, `WAN:exPort -> client:inPort (protocol)`, enable state. Do not dump credentials.

## UI path (manual fallback)

If the script cannot reach the gateway, guide the browser path:

1. Open `http://192.168.1.1/cgi-bin/luci`
2. Username + password → **确认登录**
3. **高级设置** → **端口映射**
4. Fill 虚拟服务名称 / 局域网IP / 协议 / 内部端口 / 外部端口 → **添加映射**
5. **映射列表** for enable/disable/delete and bulk actions

## Validation rules (client-side, same as gateway)

- Name: required, max 31, no special chars, unique among existing `desp`
- LAN IP: valid IPv4, not equal to gateway LAN IP, same subnet as LAN
- Ports: valid port numbers for both internal and external

## Deep reference

Read [references/api.md](references/api.md) when debugging HTTP status codes, token/cookie behaviour, request field names, or reverse-engineering a firmware variant that differs from F4600T.
