# Telecom Gateway LuCI API (ZXHN F4600T / 中国电信智能网关)

Captured from live Anything Analyzer session against `http://192.168.1.1/cgi-bin/luci`.

## Device fingerprint

| Field | Example |
|-------|---------|
| UI title | 中国电信智能网关 |
| Product | ZXHN F4600T |
| Vendor | zhongxing |
| SWVer | 23ZTW40002 |
| LAN IP | 192.168.1.1 |
| UI stack | LuCI + jQuery XHR helpers |

## Auth

### Login

```http
POST /cgi-bin/luci
Content-Type: application/x-www-form-urlencoded

username=<user>&psd=<password>
```

| Item | Value |
|------|--------|
| Default username | `useradmin` |
| Password field name | `psd` (not `password`) |
| Success | HTTP `302` → `/cgi-bin/luci/` |
| Session cookie | `sysauth=<hex>` ; path `/cgi-bin/luci/` ; session cookie |
| CSRF token | Embedded in admin HTML as `token: '...'` in logout/reboot/portmap scripts |

Subsequent admin GETs/POSTs must send `Cookie: sysauth=...`. Write POSTs must include the page `token`.

Idle timeout: ~300000 ms (5 minutes). After timeout, POSTs may return login HTML (`DOCTYPE` body); re-login.

### Logout

```http
POST /cgi-bin/luci/admin/logout
Content-Type: application/x-www-form-urlencoded

token=<csrf>
```

## Port map endpoints

### List rules

```http
GET /cgi-bin/luci/admin/settings/pmDisplay
Cookie: sysauth=...
```

Response JSON:

```json
{
  "count": 1,
  "lanIp": "192.168.1.1",
  "mask": "255.255.255.0",
  "pmRule1": {
    "protocol": "TCP",
    "inPort": 2222,
    "enable": 1,
    "desp": "树莓派ssh",
    "client": "192.168.1.10",
    "exPort": 2222
  }
}
```

Rules are numbered `pmRule1` … `pmRuleN`. Field mapping:

| API field | UI label |
|-----------|----------|
| `desp` | 虚拟服务名称 |
| `client` | 局域网 IP |
| `protocol` | 服务协议 (`TCP` / `UDP` / `BOTH`) |
| `inPort` | 内部端口 |
| `exPort` | 外部端口 |
| `enable` | 1=on, 0=off |

### Add / enable / disable / delete one rule

```http
POST /cgi-bin/luci/admin/settings/pmSetSingle
Content-Type: application/x-www-form-urlencoded
Cookie: sysauth=...
```

Common form fields: `token`, `op`, `srvname` (same as `desp` / UI name).

#### `op=add`

```
token=...&op=add&srvname=<name>&client=<lan-ip>&protocol=TCP|UDP|BOTH&exPort=<n>&inPort=<n>
```

Success: `{"retVal":0}`

#### `op=enable` / `op=disable` / `op=del`

```
token=...&op=enable&srvname=<name>
token=...&op=disable&srvname=<name>
token=...&op=del&srvname=<name>
```

### Bulk enable / disable

```http
POST /cgi-bin/luci/admin/settings/pmSetAll
Content-Type: application/x-www-form-urlencoded

token=...&op=enable
token=...&op=disable
```

UI confirms via parent popup (`#confirm` / `#cancel`) before these POSTs.

## UI pages (iframe sources)

| Purpose | Path |
|---------|------|
| Login shell | `/cgi-bin/luci` |
| Post-login shell | `/cgi-bin/luci/` |
| Add mapping form | `/cgi-bin/luci/admin/settings/portmap_config` |
| Mapping list | `/cgi-bin/luci/admin/settings/portmap_list` |
| Gateway info | `/cgi-bin/luci/admin/settings/gwinfo?get=all` or `get=part` |

Menu element IDs (browser automation):

| Menu | Element id |
|------|------------|
| 高级设置 | `#first_menu_setting` |
| 端口映射 | `#sub_second_menu_setting_portmap` |
| 映射列表 | `#sub_third_menu_setting_portmap_portmap_list` |
| Login user | `#login_username` |
| Login password | `#login_password` |
| Login submit | `button.btn` text 确认登录 |

## Client validation (from `portmap_config`)

Before `op=add` the UI rejects:

1. Empty name → 虚拟服务名称不能为空
2. Invalid filename chars → 虚拟服务名称含有特殊字符
3. Duplicate `desp` → 虚拟服务名称已存在
4. Invalid IP → 局域网IP无效
5. IP equals `lanIp` → 局域网IP与网关IP相同
6. Different subnet than `lanIp`/`mask` → 局域网IP与当前局域网不是同一网段
7. Invalid internal port → 内部端口值无效
8. Invalid external port → 外部端口值无效

## Script implementation notes

1. Login with POST form → capture `Set-Cookie: sysauth`.
2. GET `portmap_config` (or any admin HTML) → extract `token: '...'` with regex.
3. Reuse cookie + token for `pmDisplay` / `pmSetSingle` / `pmSetAll`.
4. Treat non-JSON body starting with `<!DOCTYPE` as session expired.
5. Cache-buster `_=Math.random()` is optional; UI XHR often appends it.

## Example successful add (observed)

```
srvname=test
client=192.168.1.2
protocol=TCP
exPort=65238
inPort=65238
→ {"retVal":0}
→ pmDisplay count becomes 2 with pmRule2 enable=1
```
