#!/usr/bin/env python3
"""CLIProxyAPI Management API client.

Purpose:
- Store one or more CLIProxyAPI Management API connection profiles locally.
- Let an AI agent call every CLIProxyAPI Management API endpoint without opening the Web UI.
- Provide safe redacted output by default.

Storage:
- Windows: %USERPROFILE%\\.config\\cliproxyapi\\connections.json
- Linux/macOS: ~/.config/cliproxyapi/connections.json

Requires Python 3.8+ and no third-party packages.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import getpass
import json
import mimetypes
import os
import pathlib
import secrets
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple

APP_NAME = "cliproxyapi"
CONFIG_VERSION = 2
DEFAULT_PROFILE = "default"
DEFAULT_TIMEOUT = 60
MANAGEMENT_PREFIX = "/v0/management"
SECRET_HINTS = (
    "api-key", "api_key", "apikey", "key", "password", "secret", "token",
    "authorization", "bearer", "private_key", "client_secret", "refresh_token",
)

# Human-friendly list of Management API endpoints. The raw command can call all of them.
ENDPOINTS: List[Dict[str, str]] = [
    {"method": "GET", "path": "/usage", "body": "none", "purpose": "Retrieve in-memory usage metrics."},
    {"method": "GET", "path": "/usage/export", "body": "none", "purpose": "Export complete usage snapshot."},
    {"method": "POST", "path": "/usage/import", "body": "JSON export", "purpose": "Import and merge usage snapshot."},
    {"method": "GET", "path": "/config", "body": "none", "purpose": "Get parsed runtime config as JSON."},
    {"method": "GET", "path": "/latest-version", "body": "none", "purpose": "Fetch latest CLIProxyAPI release version string."},
    {"method": "GET", "path": "/debug", "body": "none", "purpose": "Get debug state."},
    {"method": "PUT/PATCH", "path": "/debug", "body": '{"value": true|false}', "purpose": "Set debug state."},
    {"method": "GET", "path": "/config.yaml", "body": "none", "purpose": "Download persisted YAML config."},
    {"method": "PUT", "path": "/config.yaml", "body": "application/yaml", "purpose": "Replace persisted YAML config after validation."},
    {"method": "GET", "path": "/logging-to-file", "body": "none", "purpose": "Check file logging toggle."},
    {"method": "PUT/PATCH", "path": "/logging-to-file", "body": '{"value": true|false}', "purpose": "Enable/disable file logging."},
    {"method": "GET", "path": "/logs?after=<unix_ts>", "body": "none", "purpose": "Stream recent log lines."},
    {"method": "DELETE", "path": "/logs", "body": "none", "purpose": "Clear rotated and active logs."},
    {"method": "GET", "path": "/request-error-logs", "body": "none", "purpose": "List error request log files."},
    {"method": "GET", "path": "/request-error-logs/:name", "body": "none", "purpose": "Download a named error log file."},
    {"method": "GET", "path": "/usage-statistics-enabled", "body": "none", "purpose": "Check usage telemetry collection toggle."},
    {"method": "PUT/PATCH", "path": "/usage-statistics-enabled", "body": '{"value": true|false}', "purpose": "Enable/disable usage telemetry."},
    {"method": "GET", "path": "/proxy-url", "body": "none", "purpose": "Get global upstream proxy URL."},
    {"method": "PUT/PATCH", "path": "/proxy-url", "body": '{"value":"socks5://..."}', "purpose": "Set global proxy URL."},
    {"method": "DELETE", "path": "/proxy-url", "body": "none", "purpose": "Clear global proxy URL."},
    {"method": "GET", "path": "/quota-exceeded/switch-project", "body": "none", "purpose": "Get Gemini quota project-switch behavior."},
    {"method": "PUT/PATCH", "path": "/quota-exceeded/switch-project", "body": '{"value": true|false}', "purpose": "Set Gemini quota project-switch behavior."},
    {"method": "GET", "path": "/quota-exceeded/switch-preview-model", "body": "none", "purpose": "Get preview-model switch behavior."},
    {"method": "PUT/PATCH", "path": "/quota-exceeded/switch-preview-model", "body": '{"value": true|false}', "purpose": "Set preview-model switch behavior."},
    {"method": "GET", "path": "/api-keys", "body": "none", "purpose": "List client API keys accepted by proxy service."},
    {"method": "PUT", "path": "/api-keys", "body": '["k1","k2"] or {"items":[...]}', "purpose": "Replace client API keys."},
    {"method": "PATCH", "path": "/api-keys", "body": '{"old":"k1","new":"k2"} or {"index":0,"value":"k"}', "purpose": "Modify one client API key."},
    {"method": "DELETE", "path": "/api-keys?value=<key>|index=<n>", "body": "none", "purpose": "Delete one client API key."},
    {"method": "GET", "path": "/gemini-api-key", "body": "none", "purpose": "List Gemini API key entries."},
    {"method": "PUT", "path": "/gemini-api-key", "body": "array of key entries", "purpose": "Replace Gemini API key entries."},
    {"method": "PATCH", "path": "/gemini-api-key", "body": '{"index":0,"value":{...}} or {"match":"key","value":{...}}', "purpose": "Modify one Gemini API key entry."},
    {"method": "DELETE", "path": "/gemini-api-key?api-key=<key>|index=<n>", "body": "none", "purpose": "Delete one Gemini API key entry."},
    {"method": "GET", "path": "/codex-api-key", "body": "none", "purpose": "List Codex API key entries."},
    {"method": "PUT", "path": "/codex-api-key", "body": "array of key entries", "purpose": "Replace Codex API key entries."},
    {"method": "PATCH", "path": "/codex-api-key", "body": '{"index":0,"value":{...}} or {"match":"key","value":{...}}', "purpose": "Modify one Codex API key entry."},
    {"method": "DELETE", "path": "/codex-api-key?api-key=<key>|index=<n>", "body": "none", "purpose": "Delete one Codex API key entry."},
    {"method": "GET", "path": "/request-retry", "body": "none", "purpose": "Get retry count."},
    {"method": "PUT/PATCH", "path": "/request-retry", "body": '{"value": 3}', "purpose": "Set retry count."},
    {"method": "GET", "path": "/max-retry-interval", "body": "none", "purpose": "Get max retry wait seconds."},
    {"method": "PUT/PATCH", "path": "/max-retry-interval", "body": '{"value": 60}', "purpose": "Set max retry wait seconds."},
    {"method": "GET", "path": "/request-log", "body": "none", "purpose": "Get request log toggle."},
    {"method": "PUT/PATCH", "path": "/request-log", "body": '{"value": true|false}', "purpose": "Set request log toggle."},
    {"method": "GET", "path": "/ws-auth", "body": "none", "purpose": "Get WebSocket auth toggle."},
    {"method": "PUT/PATCH", "path": "/ws-auth", "body": '{"value": true|false}', "purpose": "Set WebSocket auth toggle."},
    {"method": "GET", "path": "/claude-api-key", "body": "none", "purpose": "List Claude API key entries."},
    {"method": "PUT", "path": "/claude-api-key", "body": "array of key entries", "purpose": "Replace Claude API key entries."},
    {"method": "PATCH", "path": "/claude-api-key", "body": '{"index":0,"value":{...}} or {"match":"key","value":{...}}', "purpose": "Modify one Claude API key entry."},
    {"method": "DELETE", "path": "/claude-api-key?api-key=<key>|index=<n>", "body": "none", "purpose": "Delete one Claude API key entry."},
    {"method": "GET", "path": "/openai-compatibility", "body": "none", "purpose": "List OpenAI-compatible upstream providers."},
    {"method": "PUT", "path": "/openai-compatibility", "body": "array of provider entries", "purpose": "Replace OpenAI-compatible providers."},
    {"method": "PATCH", "path": "/openai-compatibility", "body": '{"index":0,"value":{...}} or {"name":"provider","value":{...}}', "purpose": "Modify one OpenAI-compatible provider."},
    {"method": "DELETE", "path": "/openai-compatibility?name=<name>|index=<n>", "body": "none", "purpose": "Delete one OpenAI-compatible provider."},
    {"method": "GET", "path": "/oauth-excluded-models", "body": "none", "purpose": "Get OAuth provider excluded model map."},
    {"method": "PUT", "path": "/oauth-excluded-models", "body": '{"openai":["model"]}', "purpose": "Replace OAuth excluded model map."},
    {"method": "PATCH", "path": "/oauth-excluded-models", "body": '{"provider":"claude","models":["model"]}', "purpose": "Upsert/delete one provider model block."},
    {"method": "DELETE", "path": "/oauth-excluded-models?provider=<provider>", "body": "none", "purpose": "Delete provider model block."},
    {"method": "GET", "path": "/auth-files", "body": "none", "purpose": "List auth JSON token files."},
    {"method": "GET", "path": "/auth-files/download?name=<file.json>", "body": "none", "purpose": "Download an auth JSON token file."},
    {"method": "POST", "path": "/auth-files?name=<file.json>", "body": "raw JSON or multipart file", "purpose": "Upload an auth JSON token file."},
    {"method": "DELETE", "path": "/auth-files?name=<file.json>", "body": "none", "purpose": "Delete one auth JSON token file."},
    {"method": "DELETE", "path": "/auth-files?all=true", "body": "none", "purpose": "Delete all on-disk auth JSON token files."},
    {"method": "POST", "path": "/vertex/import", "body": "multipart file + location", "purpose": "Import Vertex service account JSON."},
    {"method": "GET", "path": "/anthropic-auth-url", "body": "none", "purpose": "Start Anthropic OAuth login."},
    {"method": "GET", "path": "/codex-auth-url", "body": "none", "purpose": "Start Codex OAuth login."},
    {"method": "GET", "path": "/gemini-cli-auth-url?project_id=<id>", "body": "none", "purpose": "Start Gemini CLI OAuth login."},
    {"method": "GET", "path": "/antigravity-auth-url", "body": "none", "purpose": "Start Antigravity OAuth login."},
    {"method": "GET", "path": "/get-auth-status?state=<state>", "body": "none", "purpose": "Poll OAuth login state."},
]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def config_dir() -> pathlib.Path:
    override = os.environ.get("CLIPROXYAPI_CONFIG_DIR")
    if override:
        return pathlib.Path(override).expanduser()
    return pathlib.Path.home() / ".config" / APP_NAME


def connections_file() -> pathlib.Path:
    return config_dir() / "connections.json"


def ensure_config_dir() -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(config_dir(), 0o700)
    except OSError:
        pass


def secure_write_json(path: pathlib.Path, payload: Dict[str, Any]) -> None:
    ensure_config_dir()
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        try:
            os.chmod(tmp_name, 0o600)
        except OSError:
            pass
        os.replace(tmp_name, path)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def load_state() -> Dict[str, Any]:
    path = connections_file()
    if not path.exists():
        return {"version": CONFIG_VERSION, "default": DEFAULT_PROFILE, "profiles": {}}
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid config file: {path}")
    data.setdefault("version", CONFIG_VERSION)
    data.setdefault("default", DEFAULT_PROFILE)
    data.setdefault("profiles", {})
    return data


def save_state(state: Dict[str, Any]) -> None:
    state["version"] = CONFIG_VERSION
    secure_write_json(connections_file(), state)


def normalize_base_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url:
        raise ValueError("CLIProxyAPI URL cannot be empty")
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("CLIProxyAPI URL must start with http:// or https://")
    if url.endswith(MANAGEMENT_PREFIX):
        url = url[: -len(MANAGEMENT_PREFIX)]
    return url.rstrip("/")


def management_url(base_url: str, path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    if path.startswith(MANAGEMENT_PREFIX + "/") or path == MANAGEMENT_PREFIX:
        return normalize_base_url(base_url) + path
    return normalize_base_url(base_url) + MANAGEMENT_PREFIX + path


def get_profile(name: Optional[str]) -> Dict[str, Any]:
    state = load_state()
    profile_name = name or state.get("default") or DEFAULT_PROFILE
    profiles = state.get("profiles", {})
    if profile_name not in profiles:
        available = ", ".join(sorted(profiles)) or "<none>"
        raise SystemExit(f"Profile '{profile_name}' not found. Available: {available}. Run setup first.")
    profile = dict(profiles[profile_name])
    profile["name"] = profile_name
    env_key = os.environ.get("CLIPROXYAPI_MANAGEMENT_KEY")
    if env_key:
        profile["management_key"] = env_key
    if not profile.get("management_key"):
        raise SystemExit("No management key saved. Run setup or set CLIPROXYAPI_MANAGEMENT_KEY.")
    return profile


def should_redact_key(key: str) -> bool:
    k = key.lower().replace("_", "-")
    return any(h in k for h in SECRET_HINTS)


def redact_string(s: str) -> str:
    if len(s) <= 8:
        return "***"
    return f"{s[:3]}...{s[-3:]}"


def redact(value: Any, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: (redact_string(str(v)) if should_redact_key(k) and isinstance(v, (str, int, float)) else redact(v, k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v, parent_key) for v in value]
    if should_redact_key(parent_key) and isinstance(value, (str, int, float)):
        return redact_string(str(value))
    return value


def parse_json_value(text: Optional[str]) -> Any:
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON: {exc}")


def print_json(obj: Any, *, raw: bool = False) -> None:
    if not raw:
        obj = redact(obj)
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def read_stdin_bytes() -> bytes:
    return sys.stdin.buffer.read()


def http_request(
    profile: Dict[str, Any],
    method: str,
    path: str,
    *,
    data: Optional[bytes] = None,
    content_type: Optional[str] = None,
    output: Optional[pathlib.Path] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[int, Dict[str, str], bytes]:
    method = method.upper()
    url = management_url(profile["url"], path)
    headers = {
        "Authorization": f"Bearer {profile['management_key']}",
        "User-Agent": "cliproxyapi-manager-skill/2.0",
    }
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            headers_out = {k.lower(): v for k, v in resp.headers.items()}
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(body)
            return resp.status, headers_out, body
    except urllib.error.HTTPError as exc:
        body = exc.read()
        try:
            err = json.loads(body.decode("utf-8"))
            print_json({"http_status": exc.code, "error": err}, raw=False)
        except Exception:
            sys.stderr.write(body.decode("utf-8", errors="replace") + "\n")
        raise SystemExit(exc.code)
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connection failed: {exc}")


def decode_body(body: bytes, headers: Dict[str, str]) -> Any:
    content_type = headers.get("content-type", "")
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type or text.strip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except Exception:
            return text
    return text


def multipart_body(fields: Dict[str, str], file_field: str, file_path: pathlib.Path) -> Tuple[bytes, str]:
    boundary = "----cliproxyapi" + secrets.token_hex(16)
    chunks: List[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode())
        chunks.append(b"\r\n")
    filename = file_path.name
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    chunks.append(f"--{boundary}\r\n".encode())
    chunks.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode())
    chunks.append(f"Content-Type: {mime}\r\n\r\n".encode())
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def cmd_paths(_args: argparse.Namespace) -> None:
    print_json({
        "platform": sys.platform,
        "home": str(pathlib.Path.home()),
        "config_dir": str(config_dir()),
        "connections_file": str(connections_file()),
        "python": sys.executable,
        "python_version": sys.version.split()[0],
        "env_overrides": {
            "CLIPROXYAPI_CONFIG_DIR": os.environ.get("CLIPROXYAPI_CONFIG_DIR", ""),
            "CLIPROXYAPI_MANAGEMENT_KEY": "set" if os.environ.get("CLIPROXYAPI_MANAGEMENT_KEY") else "",
            "CLIPROXYAPI_UPSTREAM_API_KEY": "set" if os.environ.get("CLIPROXYAPI_UPSTREAM_API_KEY") else "",
        },
    }, raw=True)


def cmd_setup(args: argparse.Namespace) -> None:
    key = args.key or os.environ.get("CLIPROXYAPI_MANAGEMENT_KEY")
    if not key and not args.no_prompt:
        key = getpass.getpass("CLIProxyAPI management key/password: ")
    if not key:
        raise SystemExit("Missing management key/password. Use --key, CLIPROXYAPI_MANAGEMENT_KEY, or interactive prompt.")
    state = load_state()
    profiles = state.setdefault("profiles", {})
    name = args.name or DEFAULT_PROFILE
    profiles[name] = {
        "url": normalize_base_url(args.url),
        "management_key": key,
        "created_at": profiles.get(name, {}).get("created_at", utc_now()),
        "updated_at": utc_now(),
    }
    if args.default or not state.get("default") or state.get("default") not in profiles:
        state["default"] = name
    save_state(state)
    print_json({"status": "ok", "saved_profile": name, "default": state.get("default"), "file": str(connections_file())})


def cmd_profiles(args: argparse.Namespace) -> None:
    state = load_state()
    if args.raw:
        print_json(state, raw=True)
        return
    out = {
        "default": state.get("default"),
        "profiles": {
            name: {k: v for k, v in profile.items() if k != "management_key"}
            for name, profile in state.get("profiles", {}).items()
        },
        "file": str(connections_file()),
    }
    print_json(out, raw=True)


def cmd_use_profile(args: argparse.Namespace) -> None:
    state = load_state()
    if args.name not in state.get("profiles", {}):
        raise SystemExit(f"Profile '{args.name}' not found")
    state["default"] = args.name
    save_state(state)
    print_json({"status": "ok", "default": args.name})


def cmd_delete_profile(args: argparse.Namespace) -> None:
    state = load_state()
    profiles = state.get("profiles", {})
    if args.name not in profiles:
        raise SystemExit(f"Profile '{args.name}' not found")
    del profiles[args.name]
    if state.get("default") == args.name:
        state["default"] = sorted(profiles.keys())[0] if profiles else DEFAULT_PROFILE
    save_state(state)
    print_json({"status": "ok", "deleted": args.name, "default": state.get("default")})


def call_and_print(args: argparse.Namespace, method: str, path: str, data: Optional[bytes] = None, content_type: Optional[str] = None, output: Optional[pathlib.Path] = None) -> None:
    profile = get_profile(args.profile)
    status, headers, body = http_request(profile, method, path, data=data, content_type=content_type, output=output, timeout=args.timeout)
    if output:
        print_json({"status": "ok", "http_status": status, "saved_to": str(output)}, raw=True)
        return
    decoded = decode_body(body, headers)
    if isinstance(decoded, (dict, list)):
        print_json(decoded, raw=args.raw)
    else:
        print(decoded)


def cmd_test(args: argparse.Namespace) -> None:
    profile = get_profile(args.profile)
    try:
        status, headers, body = http_request(profile, "GET", "/latest-version", timeout=args.timeout)
        decoded = decode_body(body, headers)
        print_json({"status": "ok", "http_status": status, "profile": profile["name"], "latest_version": decoded}, raw=args.raw)
    except SystemExit:
        # Some old deployments may fail latest-version due outbound GitHub access, so try /config.
        status, headers, body = http_request(profile, "GET", "/config", timeout=args.timeout)
        decoded = decode_body(body, headers)
        print_json({"status": "ok", "http_status": status, "profile": profile["name"], "config_present": bool(decoded)}, raw=True)


def cmd_raw(args: argparse.Namespace) -> None:
    data = None
    content_type = None
    if args.data is not None:
        data = args.data.encode("utf-8")
        content_type = args.content_type or "application/json"
    elif args.data_file:
        data = pathlib.Path(args.data_file).read_bytes()
        content_type = args.content_type or "application/octet-stream"
    elif args.stdin:
        data = read_stdin_bytes()
        content_type = args.content_type or "application/json"
    output = pathlib.Path(args.output).expanduser() if args.output else None
    call_and_print(args, args.method, args.path, data=data, content_type=content_type, output=output)


def cmd_get(args: argparse.Namespace) -> None:
    call_and_print(args, "GET", args.path)


def cmd_set_value(args: argparse.Namespace) -> None:
    payload: Any
    # Convert common scalar values while preserving strings.
    raw_value = args.value
    lowered = raw_value.lower()
    if lowered == "true":
        payload = {"value": True}
    elif lowered == "false":
        payload = {"value": False}
    else:
        try:
            payload = {"value": int(raw_value)}
        except ValueError:
            payload = {"value": raw_value}
    call_and_print(args, args.method, args.path, data=json.dumps(payload).encode(), content_type="application/json")


def cmd_config(args: argparse.Namespace) -> None:
    if args.format == "yaml":
        call_and_print(args, "GET", "/config.yaml", output=pathlib.Path(args.output).expanduser() if args.output else None)
    else:
        call_and_print(args, "GET", "/config")


def cmd_put_config_yaml(args: argparse.Namespace) -> None:
    path = pathlib.Path(args.file).expanduser()
    call_and_print(args, "PUT", "/config.yaml", data=path.read_bytes(), content_type="application/yaml")


def cmd_endpoints(args: argparse.Namespace) -> None:
    if args.json:
        print_json(ENDPOINTS, raw=True)
        return
    for e in ENDPOINTS:
        print(f"{e['method']:<10} {e['path']:<48} {e['body']:<45} {e['purpose']}")


def cmd_list_aliases(args: argparse.Namespace) -> None:
    profile = get_profile(args.profile)
    status, headers, body = http_request(profile, "GET", "/config", timeout=args.timeout)
    cfg = decode_body(body, headers)
    if not isinstance(cfg, dict):
        raise SystemExit("/config did not return JSON object")
    rows: List[Dict[str, Any]] = []
    sections = ["openai-compatibility", "codex-api-key", "claude-api-key", "gemini-api-key"]
    for section in sections:
        entries = cfg.get(section, [])
        if not isinstance(entries, list):
            continue
        for index, item in enumerate(entries):
            if not isinstance(item, dict):
                continue
            provider = item.get("name") or item.get("base-url") or f"{section}[{index}]"
            models = item.get("models") or []
            if isinstance(models, list):
                for m in models:
                    if isinstance(m, dict):
                        rows.append({
                            "section": section,
                            "provider": provider,
                            "alias": m.get("alias") or "",
                            "upstream_model": m.get("name") or "",
                        })
    if args.json:
        print_json({"aliases": rows}, raw=args.raw)
        return
    if not rows:
        print("No model aliases found in openai-compatibility/codex-api-key/claude-api-key/gemini-api-key.")
        return
    alias_w = max(5, max(len(str(r["alias"])) for r in rows))
    section_w = max(7, max(len(str(r["section"])) for r in rows))
    provider_w = max(8, max(len(str(r["provider"])) for r in rows))
    print(f"{'alias'.ljust(alias_w)}  {'section'.ljust(section_w)}  {'provider'.ljust(provider_w)}  upstream_model")
    print(f"{'-'*alias_w}  {'-'*section_w}  {'-'*provider_w}  {'-'*14}")
    for r in rows:
        print(f"{str(r['alias']).ljust(alias_w)}  {str(r['section']).ljust(section_w)}  {str(r['provider']).ljust(provider_w)}  {r['upstream_model']}")


def cmd_openai_compat_add(args: argparse.Namespace) -> None:
    api_key = args.api_key or os.environ.get("CLIPROXYAPI_UPSTREAM_API_KEY")
    if not api_key and not args.no_prompt:
        api_key = getpass.getpass("Upstream OpenAI-compatible API key: ")
    if not api_key:
        raise SystemExit("Missing upstream API key. Use --api-key, CLIPROXYAPI_UPSTREAM_API_KEY, or prompt.")
    entry = {
        "name": args.name,
        "base-url": args.base_url.rstrip("/"),
        "api-key-entries": [{"api-key": api_key, "proxy-url": args.proxy_url or ""}],
        "models": [],
        "headers": parse_json_value(args.headers) if args.headers else {},
    }
    if args.model_name:
        entry["models"].append({"name": args.model_name, "alias": args.alias or args.model_name})
    profile = get_profile(args.profile)
    status, headers, body = http_request(profile, "GET", "/openai-compatibility", timeout=args.timeout)
    current = decode_body(body, headers)
    providers = []
    if isinstance(current, dict):
        providers = current.get("openai-compatibility") or []
    if not isinstance(providers, list):
        providers = []
    replaced = False
    for i, p in enumerate(providers):
        if isinstance(p, dict) and p.get("name") == args.name:
            if not args.force:
                raise SystemExit(f"Provider '{args.name}' already exists. Use --force to replace it.")
            providers[i] = entry
            replaced = True
            break
    if not replaced:
        providers.append(entry)
    data = json.dumps(providers, ensure_ascii=False).encode()
    status, headers, body = http_request(profile, "PUT", "/openai-compatibility", data=data, content_type="application/json", timeout=args.timeout)
    decoded = decode_body(body, headers)
    print_json({"status": "ok", "changed": "replaced" if replaced else "added", "provider": entry, "api_response": decoded}, raw=args.raw)


def cmd_openai_compat_add_model(args: argparse.Namespace) -> None:
    profile = get_profile(args.profile)
    status, headers, body = http_request(profile, "GET", "/openai-compatibility", timeout=args.timeout)
    current = decode_body(body, headers)
    providers = current.get("openai-compatibility") if isinstance(current, dict) else []
    if not isinstance(providers, list):
        raise SystemExit("Unexpected /openai-compatibility response")
    found = False
    for p in providers:
        if isinstance(p, dict) and p.get("name") == args.name:
            p.setdefault("models", [])
            models = p["models"]
            if not isinstance(models, list):
                p["models"] = models = []
            alias = args.alias or args.model_name
            for m in models:
                if isinstance(m, dict) and (m.get("alias") == alias or m.get("name") == args.model_name):
                    if not args.force:
                        raise SystemExit("Model mapping already exists. Use --force to replace it.")
                    m["name"] = args.model_name
                    m["alias"] = alias
                    break
            else:
                models.append({"name": args.model_name, "alias": alias})
            found = True
            break
    if not found:
        raise SystemExit(f"Provider '{args.name}' not found. Use openai-compat-add first.")
    data = json.dumps(providers, ensure_ascii=False).encode()
    status, headers, body = http_request(profile, "PUT", "/openai-compatibility", data=data, content_type="application/json", timeout=args.timeout)
    print_json(decode_body(body, headers), raw=args.raw)


def cmd_auth_upload(args: argparse.Namespace) -> None:
    path = pathlib.Path(args.file).expanduser()
    if args.multipart:
        data, ctype = multipart_body({}, "file", path)
        call_and_print(args, "POST", "/auth-files", data=data, content_type=ctype)
    else:
        name = args.name or path.name
        call_and_print(args, "POST", f"/auth-files?name={urllib.parse.quote(name)}", data=path.read_bytes(), content_type="application/json")


def cmd_vertex_import(args: argparse.Namespace) -> None:
    path = pathlib.Path(args.file).expanduser()
    fields = {}
    if args.location:
        fields["location"] = args.location
    data, ctype = multipart_body(fields, "file", path)
    call_and_print(args, "POST", "/vertex/import", data=data, content_type=ctype)


def add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--profile", default=None, help="Saved profile name. Defaults to configured default profile.")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout seconds.")
    p.add_argument("--raw", action="store_true", help="Do not redact secrets in JSON output.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage CLIProxyAPI via Management API.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("paths", help="Show config paths and environment overrides.")
    p.set_defaults(func=cmd_paths)

    p = sub.add_parser("setup", help="Save CLIProxyAPI URL and management key/password.")
    p.add_argument("--url", required=True, help="CLIProxyAPI base URL, e.g. http://127.0.0.1:8317")
    p.add_argument("--key", help="Management key/password. Omit to prompt.")
    p.add_argument("--name", default=DEFAULT_PROFILE, help="Profile name.")
    p.add_argument("--default", action="store_true", help="Make this profile default.")
    p.add_argument("--no-prompt", action="store_true", help="Do not prompt for password.")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("profiles", help="List saved profiles without printing secrets.")
    p.add_argument("--raw", action="store_true", help="Show raw saved JSON including secrets. Use carefully.")
    p.set_defaults(func=cmd_profiles)

    p = sub.add_parser("use-profile", help="Set default profile.")
    p.add_argument("name")
    p.set_defaults(func=cmd_use_profile)

    p = sub.add_parser("delete-profile", help="Delete saved local profile only; does not touch CLIProxyAPI server.")
    p.add_argument("name")
    p.set_defaults(func=cmd_delete_profile)

    p = sub.add_parser("test", help="Test Management API connection.")
    add_common(p)
    p.set_defaults(func=cmd_test)

    p = sub.add_parser("endpoints", help="Print all known CLIProxyAPI Management API endpoints.")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_endpoints)

    p = sub.add_parser("raw", help="Call any Management API endpoint. Example: raw GET /config")
    add_common(p)
    p.add_argument("method", help="HTTP method: GET/POST/PUT/PATCH/DELETE")
    p.add_argument("path", help="Management path, e.g. /config or /api-keys?index=0")
    p.add_argument("--data", help="Request body string, usually JSON.")
    p.add_argument("--data-file", help="Read request body from file.")
    p.add_argument("--stdin", action="store_true", help="Read request body from STDIN.")
    p.add_argument("--content-type", help="Override Content-Type.")
    p.add_argument("--output", help="Save response body to file.")
    p.set_defaults(func=cmd_raw)

    p = sub.add_parser("get", help="GET any Management API path.")
    add_common(p)
    p.add_argument("path")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("set-value", help="Set scalar endpoint using {value: ...}. Useful for toggles and integers.")
    add_common(p)
    p.add_argument("path", help="Endpoint path, e.g. /debug")
    p.add_argument("value", help="true/false/int/string")
    p.add_argument("--method", default="PATCH", choices=["PUT", "PATCH"])
    p.set_defaults(func=cmd_set_value)

    p = sub.add_parser("config", help="Read /config or /config.yaml.")
    add_common(p)
    p.add_argument("--format", choices=["json", "yaml"], default="json")
    p.add_argument("--output", help="Only for --format yaml: save YAML to file.")
    p.set_defaults(func=cmd_config)

    p = sub.add_parser("put-config-yaml", help="Replace config.yaml via PUT /config.yaml.")
    add_common(p)
    p.add_argument("file")
    p.set_defaults(func=cmd_put_config_yaml)

    p = sub.add_parser("list-aliases", help="Extract model aliases from config.")
    add_common(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list_aliases)

    p = sub.add_parser("openai-compat-add", help="Add or replace one openai-compatibility provider.")
    add_common(p)
    p.add_argument("--name", required=True)
    p.add_argument("--base-url", required=True)
    p.add_argument("--api-key", help="Upstream API key; can use CLIPROXYAPI_UPSTREAM_API_KEY or prompt.")
    p.add_argument("--proxy-url", default="")
    p.add_argument("--headers", help='JSON object, e.g. {"X-Provider":"openrouter"}')
    p.add_argument("--model-name", help="Upstream model name.")
    p.add_argument("--alias", help="Local alias used by clients.")
    p.add_argument("--force", action="store_true")
    p.add_argument("--no-prompt", action="store_true")
    p.set_defaults(func=cmd_openai_compat_add)

    p = sub.add_parser("openai-compat-add-model", help="Add or replace a model alias on an existing OpenAI-compatible provider.")
    add_common(p)
    p.add_argument("--name", required=True, help="Provider name")
    p.add_argument("--model-name", required=True, help="Upstream model name")
    p.add_argument("--alias", help="Local alias. Defaults to model-name.")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_openai_compat_add_model)

    p = sub.add_parser("auth-upload", help="Upload auth JSON file to /auth-files.")
    add_common(p)
    p.add_argument("file")
    p.add_argument("--name", help="Remote filename for raw JSON upload. Defaults to local filename.")
    p.add_argument("--multipart", action="store_true", help="Use multipart/form-data instead of raw JSON upload.")
    p.set_defaults(func=cmd_auth_upload)

    p = sub.add_parser("vertex-import", help="Import Vertex service account JSON.")
    add_common(p)
    p.add_argument("file")
    p.add_argument("--location", default="us-central1")
    p.set_defaults(func=cmd_vertex_import)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
