#!/usr/bin/env python3
"""Shared helpers for the odoorpc-agent skill."""
from __future__ import annotations

import json
import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

try:
    import yaml
except Exception as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required. Run with `uv run ...` or install PyYAML.") from exc

CONFIG_DIR = Path.home() / ".config" / "odoorpc"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
TYPO_CONFIG_FILE = CONFIG_DIR / "config.ymal"
SNAPSHOT_DIR = CONFIG_DIR / "snapshots"

SUPPORTED_PROTOCOLS = {"jsonrpc", "jsonrpc+ssl", "xmlrpc", "xmlrpc+ssl"}

QUIET_MAIL_CONTEXT = {
    "mail_create_nosubscribe": True,
    "mail_notrack": True,
    "tracking_disable": True,
    "mail_auto_subscribe_no_notify": True,
}

PROTECTED_MODELS_EXACT = {
    "res.users",
    "res.company",
    "account.move",
    "account.move.line",
    "stock.picking",
    "stock.move",
    "stock.quant",
    "ir.config_parameter",
    "ir.model.access",
    "ir.rule",
    "ir.module.module",
}
PROTECTED_MODEL_PREFIXES = ("account.", "stock.", "payment.", "ir.")
PROTECTED_FIELD_NAMES = {
    "password",
    "groups_id",
    "company_id",
    "company_ids",
}
PROTECTED_FIELD_KEYWORDS = ("password", "token", "secret", "key", "credential")


class SkillError(Exception):
    """Human-readable script error."""

    exit_code = 2


class ConfigError(SkillError):
    exit_code = 3


class AuthError(SkillError):
    exit_code = 4


class SafetyError(SkillError):
    exit_code = 5


@dataclass(frozen=True)
class Profile:
    name: str
    host: str
    port: int
    protocol: str
    database: str
    username: str
    password: str
    timeout: int = 30
    odoo_version: Optional[str] = None

    @classmethod
    def from_mapping(cls, name: str, raw: Mapping[str, Any]) -> "Profile":
        missing = [k for k in ("host", "port", "protocol", "database", "username", "password") if raw.get(k) in (None, "")]
        if missing:
            raise ConfigError(f"Profile '{name}' is missing required keys: {', '.join(missing)}")
        protocol = str(raw["protocol"])
        if protocol not in SUPPORTED_PROTOCOLS:
            raise ConfigError(f"Profile '{name}' has unsupported protocol '{protocol}'. Expected one of: {sorted(SUPPORTED_PROTOCOLS)}")
        try:
            port = int(raw["port"])
        except Exception as exc:
            raise ConfigError(f"Profile '{name}' port must be an integer.") from exc
        try:
            timeout = int(raw.get("timeout", 30))
        except Exception as exc:
            raise ConfigError(f"Profile '{name}' timeout must be an integer.") from exc
        raw_version = raw.get("odoo_version")
        odoo_version = None if raw_version in (None, "") else str(raw_version)
        return cls(
            name=name,
            host=str(raw["host"]),
            port=port,
            protocol=protocol,
            database=str(raw["database"]),
            username=str(raw["username"]),
            password=str(raw["password"]),
            timeout=timeout,
            odoo_version=odoo_version,
        )


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def json_dump(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False, default=str))


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, stat.S_IRWXU)
    except PermissionError:
        pass
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(SNAPSHOT_DIR, stat.S_IRWXU)
    except PermissionError:
        pass


def active_config_path() -> Path:
    if CONFIG_FILE.exists():
        return CONFIG_FILE
    if TYPO_CONFIG_FILE.exists():
        return TYPO_CONFIG_FILE
    return CONFIG_FILE


def load_config(allow_missing: bool = False) -> Dict[str, Any]:
    path = active_config_path()
    if not path.exists():
        if allow_missing:
            return {"default_profile": None, "profiles": {}}
        raise ConfigError(f"Config not found: {CONFIG_FILE}. Create one with scripts/odoo_config.py set-profile.")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"Config file must contain a YAML mapping: {path}")
    data.setdefault("profiles", {})
    if not isinstance(data["profiles"], dict):
        raise ConfigError("Config key 'profiles' must be a mapping.")
    return data


def save_config(data: Mapping[str, Any]) -> Path:
    ensure_config_dir()
    path = CONFIG_FILE
    tmp = path.with_suffix(".yaml.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        yaml.safe_dump(dict(data), f, allow_unicode=True, sort_keys=False)
    tmp.replace(path)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except PermissionError:
        pass
    return path


def redact_profile(raw: Mapping[str, Any]) -> Dict[str, Any]:
    result = dict(raw)
    for key in list(result.keys()):
        lk = str(key).lower()
        if any(term in lk for term in ("password", "token", "secret", "key", "credential")):
            value = result[key]
            result[key] = "" if value in (None, "") else "***REDACTED***"
    return result


def get_profile(profile_name: Optional[str]) -> Profile:
    cfg = load_config()
    name = profile_name or cfg.get("default_profile")
    if not name:
        names = sorted(cfg.get("profiles", {}).keys())
        raise ConfigError(f"No profile specified and no default_profile set. Available profiles: {names}")
    raw = cfg.get("profiles", {}).get(name)
    if raw is None:
        names = sorted(cfg.get("profiles", {}).keys())
        raise ConfigError(f"Profile '{name}' not found. Available profiles: {names}")
    return Profile.from_mapping(str(name), raw)


def detect_odoo_version(odoo: Any) -> Optional[str]:
    """Return the server version as a stable string when OdooRPC exposes it."""
    version = getattr(odoo, "version", None)
    if version in (None, ""):
        return None
    # OdooRPC may expose a string, tuple/list, or a lightweight object depending on versions.
    if isinstance(version, (tuple, list)):
        return ".".join(str(part) for part in version if part is not None)
    return str(version)


def connect(profile_name: Optional[str]):
    try:
        import odoorpc
    except Exception as exc:  # pragma: no cover
        raise ConfigError("odoorpc is required. Run with `uv run ...` or install odoorpc.") from exc

    profile = get_profile(profile_name)
    try:
        odoo = odoorpc.ODOO(profile.host, protocol=profile.protocol, port=profile.port, timeout=profile.timeout)
        odoo.login(profile.database, profile.username, profile.password)
    except Exception as exc:
        raise AuthError(f"Failed to connect/login using profile '{profile.name}': {exc}") from exc
    return odoo, profile


def parse_ids(value: str) -> List[int]:
    try:
        ids = [int(x.strip()) for x in value.split(",") if x.strip()]
    except Exception as exc:
        raise SkillError("--ids must be a comma-separated list of integer IDs, e.g. 1,2,3") from exc
    if not ids:
        raise SkillError("--ids cannot be empty.")
    if len(set(ids)) != len(ids):
        raise SkillError("--ids contains duplicates. Deduplicate before mutation.")
    return ids


def parse_json_object(value: str, flag_name: str) -> Dict[str, Any]:
    try:
        data = json.loads(value)
    except Exception as exc:
        raise SkillError(f"{flag_name} must be valid JSON.") from exc
    if not isinstance(data, dict):
        raise SkillError(f"{flag_name} must be a JSON object.")
    return data


def parse_json_array(value: str, flag_name: str) -> List[Any]:
    try:
        data = json.loads(value)
    except Exception as exc:
        raise SkillError(f"{flag_name} must be valid JSON.") from exc
    if not isinstance(data, list):
        raise SkillError(f"{flag_name} must be a JSON array.")
    return data


def parse_fields(value: Optional[str]) -> Optional[List[str]]:
    if value is None or value.strip() == "":
        return None
    fields = [x.strip() for x in value.split(",") if x.strip()]
    return fields or None


def is_protected_model(model: str) -> bool:
    return model in PROTECTED_MODELS_EXACT or model.startswith(PROTECTED_MODEL_PREFIXES)


def protected_fields_in(values: Mapping[str, Any]) -> List[str]:
    result = []
    for field in values.keys():
        lower = field.lower()
        if field in PROTECTED_FIELD_NAMES or any(term in lower for term in PROTECTED_FIELD_KEYWORDS):
            result.append(field)
    return result


def enforce_mutation_safety(model: str, values: Optional[Mapping[str, Any]] = None, allow_protected: bool = False) -> None:
    if allow_protected:
        return
    if is_protected_model(model):
        raise SafetyError(
            f"Refusing to mutate protected model '{model}'. Use --allow-protected only after explicit administrator-level user approval."
        )
    if values:
        protected = protected_fields_in(values)
        if protected:
            raise SafetyError(
                f"Refusing to mutate protected field(s) {protected}. Use --allow-protected only after explicit administrator-level user approval."
            )


def read_snapshot(odoo: Any, model: str, ids: Iterable[int], fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    record_ids = list(ids)
    if not record_ids:
        return []
    Model = odoo.env[model]
    return Model.read(record_ids, fields) if fields else Model.read(record_ids)


def save_snapshot(profile: Profile, operation: str, model: str, ids: Iterable[int], before: Any, after: Any = None) -> Path:
    from datetime import datetime, timezone

    ensure_config_dir()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = model.replace(".", "_")
    id_part = "-".join(str(x) for x in list(ids)[:10]) or "new"
    path = SNAPSHOT_DIR / f"{timestamp}_{profile.name}_{operation}_{safe_model}_{id_part}.json"
    payload = {
        "timestamp_utc": timestamp,
        "profile": profile.name,
        "configured_odoo_version": profile.odoo_version,
        "operation": operation,
        "model": model,
        "ids": list(ids),
        "before": before,
        "after": after,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except PermissionError:
        pass
    return path


def make_context(quiet_mail: bool = False, extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {}
    if quiet_mail:
        ctx.update(QUIET_MAIL_CONTEXT)
    if extra:
        ctx.update(dict(extra))
    return ctx


def run_main(fn) -> None:
    try:
        fn()
    except SkillError as exc:
        json_dump({"ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        raise SystemExit(getattr(exc, "exit_code", 2))
    except KeyboardInterrupt:
        json_dump({"ok": False, "error_type": "KeyboardInterrupt", "error": "Interrupted"})
        raise SystemExit(130)
    except Exception as exc:
        json_dump({"ok": False, "error_type": exc.__class__.__name__, "error": str(exc)})
        raise SystemExit(1)
