#!/usr/bin/env python3
"""Encrypted, Git-friendly configuration vault for humans and AI agents."""

from __future__ import annotations

import argparse
import base64
import configparser
import getpass
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

try:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
except ModuleNotFoundError:
    print("ERROR: Missing dependency. Run: python -m pip install 'cryptography>=3.4.8'", file=sys.stderr)
    raise SystemExit(3)


MANIFEST_NAME = "vault.json"
KEY_ENVELOPE_NAME = "vault-key.json"
OBJECTS_DIR = "objects"
VAULT_VERSION = 1
OBJECT_VERSION = 1
KEY_ENVELOPE_VERSION = 1
KDF_N = 2**15
KDF_R = 8
KDF_P = 1
KEY_LENGTH = 32
MIN_PASSPHRASE_BYTES = 16
DEFAULTS_VERSION = 1
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
BRANCH_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
SUPPORTED_FORMATS = {"text", "env", "json", "toml", "ini", "yaml", "powershell"}


class VaultError(RuntimeError):
    """Expected user-facing error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def b64encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def b64decode(value: str, field: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:  # binascii.Error differs slightly across Python versions.
        raise VaultError(f"Invalid base64 in {field}") from exc


def atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.chmod(temp_path, mode)
        except OSError:
            pass
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def restrict_user_only(path: Path) -> None:
    if os.name != "nt":
        os.chmod(path, 0o600)
        return
    identity_result = subprocess.run(["whoami"], text=True, capture_output=True, check=False)
    identity = identity_result.stdout.strip()
    if identity_result.returncode != 0 or not identity or not shutil.which("icacls"):
        raise VaultError(f"Cannot determine a Windows identity to protect {path}")
    acl_result = subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", f"{identity}:(F)"],
        text=True,
        capture_output=True,
        check=False,
    )
    if acl_result.returncode != 0:
        raise VaultError(f"Cannot restrict access to {path}")


def default_config_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        return Path(base) / "config-vault" if base else Path.home() / "AppData" / "Roaming" / "config-vault"
    base = os.environ.get("XDG_CONFIG_HOME")
    return Path(base) / "config-vault" if base else Path.home() / ".config" / "config-vault"


def default_checkout_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return Path(base) / "config-vault" / "checkout" if base else default_config_dir() / "checkout"
    base = os.environ.get("XDG_DATA_HOME")
    return Path(base) / "config-vault" / "checkout" if base else Path.home() / ".local" / "share" / "config-vault" / "checkout"


def defaults_path(args: argparse.Namespace) -> Path:
    configured = getattr(args, "config_file", None)
    return Path(configured).expanduser().resolve() if configured else (default_config_dir() / "config.json").resolve()


def load_defaults(args: argparse.Namespace) -> dict[str, Any]:
    path = defaults_path(args)
    if not path.exists():
        return {}
    defaults = load_json(path)
    if defaults.get("version") != DEFAULTS_VERSION:
        raise VaultError(f"Unsupported defaults version in {path}")
    return defaults


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VaultError(f"Missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VaultError(f"Invalid JSON in {path}: line {exc.lineno}, column {exc.colno}") from exc
    if not isinstance(value, dict):
        raise VaultError(f"Expected a JSON object in {path}")
    return value


def save_json(path: Path, value: dict[str, Any]) -> None:
    data = (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    atomic_write(path, data)


def read_passphrase(key_file: str | None, env_name: str = "CONFIG_VAULT_KEY", prompt: bool = False) -> bytes:
    if key_file:
        try:
            value = Path(key_file).expanduser().read_bytes().rstrip(b"\r\n")
        except OSError as exc:
            raise VaultError(f"Cannot read key file: {key_file}") from exc
    elif os.environ.get(env_name):
        value = os.environ[env_name].encode("utf-8")
    elif prompt and sys.stdin.isatty():
        value = getpass.getpass("Vault key: ").encode("utf-8")
    else:
        raise VaultError(f"Provide --key-file or set {env_name}; raw keys are not accepted as arguments")
    if len(value) < MIN_PASSPHRASE_BYTES:
        raise VaultError(f"Vault key must contain at least {MIN_PASSPHRASE_BYTES} bytes")
    return value


def derive_wrap_key(passphrase: bytes, salt: bytes, n: int, r: int, p: int) -> bytes:
    return Scrypt(salt=salt, length=KEY_LENGTH, n=n, r=r, p=p).derive(passphrase)


def wrap_master_key(master_key: bytes, passphrase: bytes) -> dict[str, Any]:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    header = {
        "version": KEY_ENVELOPE_VERSION,
        "kdf": {"name": "scrypt", "n": KDF_N, "r": KDF_R, "p": KDF_P, "salt": b64encode(salt)},
        "cipher": {"name": "AES-256-GCM", "nonce": b64encode(nonce)},
    }
    wrap_key = derive_wrap_key(passphrase, salt, KDF_N, KDF_R, KDF_P)
    ciphertext = AESGCM(wrap_key).encrypt(nonce, master_key, canonical_json(header))
    return {**header, "ciphertext": b64encode(ciphertext)}


def unwrap_master_key(envelope: dict[str, Any], passphrase: bytes) -> bytes:
    try:
        if envelope.get("version") != KEY_ENVELOPE_VERSION:
            raise VaultError(f"Unsupported key envelope version: {envelope.get('version')!r}")
        kdf = envelope["kdf"]
        cipher = envelope["cipher"]
        if kdf.get("name") != "scrypt" or cipher.get("name") != "AES-256-GCM":
            raise VaultError("Unsupported vault key algorithm")
        salt = b64decode(kdf["salt"], "kdf.salt")
        nonce = b64decode(cipher["nonce"], "cipher.nonce")
        ciphertext = b64decode(envelope["ciphertext"], "ciphertext")
        header = {"version": envelope["version"], "kdf": kdf, "cipher": cipher}
        wrap_key = derive_wrap_key(passphrase, salt, int(kdf["n"]), int(kdf["r"]), int(kdf["p"]))
        master_key = AESGCM(wrap_key).decrypt(nonce, ciphertext, canonical_json(header))
    except InvalidTag as exc:
        raise VaultError("Vault key is incorrect or vault-key.json was modified") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise VaultError("Malformed vault-key.json") from exc
    if len(master_key) != KEY_LENGTH:
        raise VaultError("Malformed master key")
    return master_key


def encrypt_object(master_key: bytes, item_id: str, plaintext: bytes) -> dict[str, Any]:
    nonce = os.urandom(12)
    header = {
        "version": OBJECT_VERSION,
        "cipher": {"name": "AES-256-GCM", "nonce": b64encode(nonce)},
    }
    aad = canonical_json({"context": "config-vault-object", "id": item_id, **header})
    ciphertext = AESGCM(master_key).encrypt(nonce, plaintext, aad)
    return {**header, "ciphertext": b64encode(ciphertext)}


def decrypt_object(master_key: bytes, item_id: str, payload: dict[str, Any]) -> bytes:
    try:
        if payload.get("version") != OBJECT_VERSION:
            raise VaultError(f"Unsupported encrypted object version for {item_id}")
        cipher = payload["cipher"]
        if cipher.get("name") != "AES-256-GCM":
            raise VaultError(f"Unsupported object cipher for {item_id}")
        nonce = b64decode(cipher["nonce"], f"{item_id}.cipher.nonce")
        ciphertext = b64decode(payload["ciphertext"], f"{item_id}.ciphertext")
        header = {"version": payload["version"], "cipher": cipher}
        aad = canonical_json({"context": "config-vault-object", "id": item_id, **header})
        return AESGCM(master_key).decrypt(nonce, ciphertext, aad)
    except InvalidTag as exc:
        raise VaultError(f"Cannot authenticate encrypted object: {item_id}") from exc
    except (KeyError, TypeError, ValueError) as exc:
        raise VaultError(f"Malformed encrypted object: {item_id}") from exc


def vault_root(args: argparse.Namespace) -> Path:
    if not args.vault:
        raise VaultError("No default vault configured; run 'configure' once or pass --vault")
    return Path(args.vault).expanduser().resolve()


def manifest_path(root: Path) -> Path:
    return root / MANIFEST_NAME


def load_manifest(root: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path(root))
    if manifest.get("version") != VAULT_VERSION:
        raise VaultError(f"Unsupported vault version: {manifest.get('version')!r}")
    if not isinstance(manifest.get("items"), list):
        raise VaultError("vault.json must contain an items array")
    return manifest


def save_manifest(root: Path, manifest: dict[str, Any]) -> None:
    manifest["updatedAt"] = utc_now()
    manifest["items"] = sorted(manifest["items"], key=lambda item: item["id"])
    save_json(manifest_path(root), manifest)


def unlock(root: Path, args: argparse.Namespace, env_name: str = "CONFIG_VAULT_KEY") -> bytes:
    passphrase = read_passphrase(getattr(args, "key_file", None), env_name=env_name, prompt=getattr(args, "prompt_key", False))
    return unwrap_master_key(load_json(root / KEY_ENVELOPE_NAME), passphrase)


def object_relpath(item_id: str) -> str:
    digest = hashlib.sha256(item_id.encode("utf-8")).hexdigest()
    return f"{OBJECTS_DIR}/{digest}.vault"


def object_path(root: Path, item: dict[str, Any]) -> Path:
    return root / PurePosixPath(item["object"])


def item_by_id(manifest: dict[str, Any], item_id: str) -> dict[str, Any]:
    for item in manifest["items"]:
        if item.get("id") == item_id:
            return item
    raise VaultError(f"Unknown item: {item_id}")


def validate_id(item_id: str) -> None:
    if not ID_PATTERN.fullmatch(item_id):
        raise VaultError("Item id must use lowercase letters, digits, dots, underscores, or hyphens")


def normalize_os(value: str | None = None) -> str:
    if value:
        return value
    system = platform.system().lower()
    return {"windows": "windows", "darwin": "darwin", "linux": "linux"}.get(system, system)


def safe_target(value: str) -> str:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", normalized):
        raise VaultError(f"Target must be a safe path relative to the home directory: {value}")
    return path.as_posix()


def parse_targets(values: list[str] | None) -> dict[str, str]:
    targets: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise VaultError("Targets must use OS=relative/path, for example windows=Documents/app/config.json")
        os_name, target = value.split("=", 1)
        os_name = os_name.strip().lower()
        if os_name not in {"default", "windows", "linux", "darwin"}:
            raise VaultError(f"Unsupported target OS: {os_name}")
        targets[os_name] = safe_target(target.strip())
    return targets


def parse_mode(value: str) -> str:
    if not re.fullmatch(r"0?[0-7]{3}", value):
        raise VaultError("Mode must be an octal value such as 600 or 0644")
    return f"{int(value, 8):04o}"


def validate_plaintext(fmt: str, plaintext: bytes, item_id: str) -> None:
    if fmt not in SUPPORTED_FORMATS:
        raise VaultError(f"Unsupported format: {fmt}")
    if fmt in {"text", "env", "yaml", "powershell"}:
        try:
            plaintext.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise VaultError(f"{item_id} must contain UTF-8 text") from exc
        return
    try:
        text = plaintext.decode("utf-8")
        if fmt == "json":
            json.loads(text)
        elif fmt == "toml":
            import tomllib

            tomllib.loads(text)
        elif fmt == "ini":
            parser = configparser.ConfigParser()
            parser.read_string(text)
    except (UnicodeDecodeError, json.JSONDecodeError, configparser.Error, Exception) as exc:
        # Preserve VaultError and avoid exposing file contents in parser errors.
        if isinstance(exc, VaultError):
            raise
        raise VaultError(f"Invalid {fmt} content for {item_id}: {exc.__class__.__name__}") from exc


def read_input(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read()
    try:
        return Path(path).expanduser().read_bytes()
    except OSError as exc:
        raise VaultError(f"Cannot read input file: {path}") from exc


def read_item(root: Path, master_key: bytes, item: dict[str, Any]) -> bytes:
    return decrypt_object(master_key, item["id"], load_json(object_path(root, item)))


def write_item(root: Path, master_key: bytes, item: dict[str, Any], plaintext: bytes) -> None:
    payload = encrypt_object(master_key, item["id"], plaintext)
    save_json(object_path(root, item), payload)


def selected_items(manifest: dict[str, Any], args: argparse.Namespace) -> list[dict[str, Any]]:
    ids = set(getattr(args, "ids", None) or [])
    tags = set(getattr(args, "tags", None) or [])
    profile = getattr(args, "profile", None)
    os_name = normalize_os(getattr(args, "os_name", None))
    selected: list[dict[str, Any]] = []
    for item in manifest["items"]:
        if ids and item["id"] not in ids:
            continue
        if tags and not tags.issubset(set(item.get("tags", []))):
            continue
        profiles = item.get("profiles", ["*"])
        operating_systems = item.get("os", ["*"])
        if profile and "*" not in profiles and profile not in profiles:
            continue
        if "*" not in operating_systems and os_name not in operating_systems:
            continue
        selected.append(item)
    missing = ids - {item["id"] for item in selected}
    if missing:
        raise VaultError(f"Items not found or excluded by rules: {', '.join(sorted(missing))}")
    return selected


def resolve_target(item: dict[str, Any], os_name: str) -> str | None:
    targets = item.get("targets", {})
    return targets.get(os_name) or targets.get("default")


def command_init(args: argparse.Namespace) -> int:
    root = vault_root(args)
    if (root / MANIFEST_NAME).exists() or (root / KEY_ENVELOPE_NAME).exists():
        raise VaultError(f"Vault already exists: {root}")
    root.mkdir(parents=True, exist_ok=True)
    (root / OBJECTS_DIR).mkdir(exist_ok=True)
    passphrase = read_passphrase(args.key_file, prompt=args.prompt_key)
    master_key = os.urandom(KEY_LENGTH)
    manifest = {"version": VAULT_VERSION, "createdAt": utc_now(), "updatedAt": utc_now(), "items": []}
    save_json(root / KEY_ENVELOPE_NAME, wrap_master_key(master_key, passphrase))
    save_json(root / MANIFEST_NAME, manifest)
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        atomic_write(gitignore, b"*.tmp\n.plaintext/\n", mode=0o644)
    if args.git and not (root / ".git").exists():
        run_git(root, ["init"])
    print(f"Initialized vault at {root}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    manifest = load_manifest(vault_root(args))
    items = selected_items(manifest, args)
    if args.json:
        print(json.dumps(items, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        for item in items:
            tags = ",".join(item.get("tags", [])) or "-"
            print(f"{item['id']}\t{item.get('format', 'text')}\t{tags}\t{item.get('description', '')}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    root = vault_root(args)
    manifest = load_manifest(root)
    items = selected_items(manifest, args)
    query = args.query.casefold()
    master_key = unlock(root, args) if args.content else None
    found = 0
    for item in items:
        metadata = json.dumps(item, ensure_ascii=False, sort_keys=True).casefold()
        metadata_match = query in metadata
        content_matches: list[tuple[int, str]] = []
        if args.content and master_key is not None:
            text = read_item(root, master_key, item).decode("utf-8", errors="replace")
            content_matches = [(number, line) for number, line in enumerate(text.splitlines(), 1) if query in line.casefold()]
        if metadata_match or content_matches:
            found += 1
            print(item["id"])
            if args.show_matches:
                for number, line in content_matches:
                    print(f"  {number}: {line}")
    return 0 if found else 1


def command_read(args: argparse.Namespace) -> int:
    root = vault_root(args)
    item = item_by_id(load_manifest(root), args.item_id)
    sys.stdout.buffer.write(read_item(root, unlock(root, args), item))
    return 0


def command_add(args: argparse.Namespace) -> int:
    root = vault_root(args)
    manifest = load_manifest(root)
    validate_id(args.item_id)
    if any(item.get("id") == args.item_id for item in manifest["items"]):
        raise VaultError(f"Item already exists: {args.item_id}")
    plaintext = read_input(args.input)
    validate_plaintext(args.format, plaintext, args.item_id)
    targets = parse_targets(args.target)
    item = {
        "id": args.item_id,
        "object": object_relpath(args.item_id),
        "description": args.description or "",
        "format": args.format,
        "mode": parse_mode(args.mode),
        "tags": sorted(set(args.item_tags or [])),
        "profiles": sorted(set(args.item_profiles or ["*"])),
        "os": sorted(set(args.item_os or ["*"])),
        "targets": targets,
    }
    master_key = unlock(root, args)
    write_item(root, master_key, item, plaintext)
    manifest["items"].append(item)
    save_manifest(root, manifest)
    print(f"Added {args.item_id}")
    return 0


def command_update(args: argparse.Namespace) -> int:
    root = vault_root(args)
    manifest = load_manifest(root)
    item = item_by_id(manifest, args.item_id)
    master_key = unlock(root, args)
    changed = False
    next_format = args.format or item.get("format", "text")
    if args.input is not None:
        plaintext = read_input(args.input)
        validate_plaintext(next_format, plaintext, args.item_id)
        write_item(root, master_key, item, plaintext)
        changed = True
    elif args.format:
        validate_plaintext(next_format, read_item(root, master_key, item), args.item_id)
    replacements = {
        "description": args.description,
        "format": args.format,
        "mode": parse_mode(args.mode) if args.mode else None,
        "tags": sorted(set(args.item_tags)) if args.item_tags is not None else None,
        "profiles": sorted(set(args.item_profiles)) if args.item_profiles is not None else None,
        "os": sorted(set(args.item_os)) if args.item_os is not None else None,
        "targets": parse_targets(args.target) if args.target is not None else None,
    }
    for field, value in replacements.items():
        if value is not None and item.get(field) != value:
            item[field] = value
            changed = True
    if not changed:
        raise VaultError("No update was requested")
    save_manifest(root, manifest)
    print(f"Updated {args.item_id}")
    return 0


def command_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        raise VaultError("Delete requires --yes")
    root = vault_root(args)
    manifest = load_manifest(root)
    item = item_by_id(manifest, args.item_id)
    unlock(root, args)  # Require possession of the vault key for destructive changes.
    object_path(root, item).unlink(missing_ok=True)
    manifest["items"] = [candidate for candidate in manifest["items"] if candidate["id"] != args.item_id]
    save_manifest(root, manifest)
    print(f"Deleted {args.item_id}; already-applied target files are not pruned automatically")
    return 0


def command_apply(args: argparse.Namespace) -> int:
    root = vault_root(args)
    manifest = load_manifest(root)
    items = selected_items(manifest, args)
    master_key = unlock(root, args)
    home = Path(args.home).expanduser().resolve()
    os_name = normalize_os(args.os_name)
    plan: list[tuple[str, dict[str, Any], Path, bytes]] = []
    for item in items:
        target_value = resolve_target(item, os_name)
        if not target_value:
            continue
        target = (home / PurePosixPath(safe_target(target_value))).resolve()
        try:
            target.relative_to(home)
        except ValueError as exc:
            raise VaultError(f"Target escapes home directory: {target_value}") from exc
        plaintext = read_item(root, master_key, item)
        if not target.exists():
            action = "create"
        elif target.read_bytes() == plaintext:
            action = "unchanged"
        else:
            action = "update"
        plan.append((action, item, target, plaintext))
    updates = [entry for entry in plan if entry[0] == "update"]
    for action, item, target, _ in plan:
        print(f"{action}\t{item['id']}\t{target}")
    if args.dry_run:
        return 0
    if updates and not args.force:
        raise VaultError("Existing files would change; inspect --dry-run output and pass --force")
    for action, item, target, plaintext in plan:
        if action == "unchanged":
            continue
        atomic_write(target, plaintext, mode=int(item.get("mode", "0600"), 8))
    return 0


def validate_vault(root: Path, master_key: bytes | None = None) -> list[str]:
    errors: list[str] = []
    try:
        manifest = load_manifest(root)
    except VaultError as exc:
        return [str(exc)]
    seen: set[str] = set()
    expected_objects: set[Path] = set()
    for index, item in enumerate(manifest["items"]):
        label = item.get("id", f"item[{index}]")
        try:
            validate_id(item["id"])
            if item["id"] in seen:
                raise VaultError(f"Duplicate item id: {item['id']}")
            seen.add(item["id"])
            if item.get("object") != object_relpath(item["id"]):
                raise VaultError(f"Unexpected object path for {item['id']}")
            expected_objects.add(object_path(root, item).resolve())
            if not object_path(root, item).is_file():
                raise VaultError(f"Missing encrypted object for {item['id']}")
            if item.get("format", "text") not in SUPPORTED_FORMATS:
                raise VaultError(f"Unsupported format for {item['id']}")
            parse_mode(item.get("mode", "0600"))
            for target in item.get("targets", {}).values():
                safe_target(target)
            if master_key is not None:
                plaintext = read_item(root, master_key, item)
                validate_plaintext(item.get("format", "text"), plaintext, item["id"])
        except (VaultError, KeyError, TypeError) as exc:
            errors.append(f"{label}: {exc}")
    objects_root = root / OBJECTS_DIR
    if objects_root.exists():
        for path in objects_root.glob("*.vault"):
            if path.resolve() not in expected_objects:
                errors.append(f"Orphan encrypted object: {path.relative_to(root).as_posix()}")
    return errors


def command_validate(args: argparse.Namespace) -> int:
    root = vault_root(args)
    master_key = unlock(root, args) if args.decrypt else None
    errors = validate_vault(root, master_key)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Vault is valid ({'metadata and plaintext' if args.decrypt else 'metadata only'})")
    return 0


def command_rekey(args: argparse.Namespace) -> int:
    root = vault_root(args)
    master_key = unlock(root, args)
    new_passphrase = read_passphrase(args.new_key_file, env_name="CONFIG_VAULT_NEW_KEY", prompt=args.prompt_new_key)
    save_json(root / KEY_ENVELOPE_NAME, wrap_master_key(master_key, new_passphrase))
    print("Rewrapped the vault master key; encrypted objects were unchanged")
    return 0


def run_git(root: Path, arguments: list[str], capture: bool = True) -> subprocess.CompletedProcess[str]:
    if not shutil.which("git"):
        raise VaultError("git is not installed or not on PATH")
    result = subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=capture,
        check=False,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "git command failed").strip()
        raise VaultError(message)
    return result


def clone_repository(repository: str, destination: Path, branch: str | None = None) -> None:
    if not shutil.which("git"):
        raise VaultError("git is not installed or not on PATH")
    if destination.exists() and any(destination.iterdir()):
        raise VaultError(f"Clone destination is not empty: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["git", "clone"]
    if branch:
        command.extend(["--branch", branch])
    command.extend(["--", repository, str(destination)])
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise VaultError((result.stderr or result.stdout).strip())


def command_clone(args: argparse.Namespace) -> int:
    destination = Path(args.destination).expanduser().resolve()
    clone_repository(args.repository, destination, args.branch)
    print(f"Cloned vault to {destination}")
    return 0


def command_configure(args: argparse.Namespace) -> int:
    config_path = defaults_path(args)
    existing = load_defaults(args)
    repository = args.repository or existing.get("repository")
    branch = args.branch or existing.get("branch") or "main"
    checkout_value = args.checkout or existing.get("vault")
    checkout = Path(checkout_value).expanduser().resolve() if checkout_value else default_checkout_dir().resolve()

    if not (checkout / MANIFEST_NAME).exists():
        if args.no_clone:
            raise VaultError(f"No vault found at {checkout}")
        if not repository:
            raise VaultError("Provide --repository to clone the default vault")
        clone_repository(repository, checkout, branch)

    if not (checkout / KEY_ENVELOPE_NAME).is_file():
        raise VaultError(f"Not a config vault checkout: {checkout}")

    if args.key_stdin:
        passphrase = sys.stdin.buffer.read().rstrip(b"\r\n")
        if len(passphrase) < MIN_PASSPHRASE_BYTES:
            raise VaultError(f"Vault password must contain at least {MIN_PASSPHRASE_BYTES} bytes")
        key_path = (config_path.parent / "vault.key").resolve()
    else:
        key_value = args.key_file or existing.get("keyFile")
        if not key_value:
            raise VaultError("Provide --password-stdin the first time; --key-file remains available for migration")
        key_path = Path(key_value).expanduser().resolve()
        passphrase = read_passphrase(str(key_path))

    # Save defaults only after the supplied key authenticates the selected vault.
    unwrap_master_key(load_json(checkout / KEY_ENVELOPE_NAME), passphrase)
    if args.key_stdin:
        atomic_write(key_path, passphrase + b"\n", mode=0o600)
        restrict_user_only(key_path)

    settings = {
        "version": DEFAULTS_VERSION,
        "repository": repository or "",
        "vault": str(checkout),
        "keyFile": str(key_path),
        "profile": args.profile or existing.get("profile") or "default",
        "os": args.os_name or existing.get("os") or normalize_os(),
        "remote": args.remote or existing.get("remote") or "origin",
        "branch": branch,
        "updatedAt": utc_now(),
    }
    save_json(config_path, settings)
    restrict_user_only(config_path)
    print(f"Saved default vault configuration to {config_path}")
    print(f"Default checkout: {checkout}")
    return 0


def command_defaults(args: argparse.Namespace) -> int:
    path = defaults_path(args)
    settings = load_defaults(args)
    if not settings:
        raise VaultError(f"No default vault configured at {path}")
    if args.json:
        print(json.dumps(settings, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(f"config\t{path}")
        for key in ("repository", "vault", "keyFile", "profile", "os", "remote", "branch"):
            print(f"{key}\t{settings.get(key, '')}")
    return 0


def command_pull(args: argparse.Namespace) -> int:
    root = vault_root(args)
    run_git(root, ["pull", "--ff-only", args.remote, args.branch])
    print(f"Updated {root} from {args.remote}/{args.branch}")
    return 0


def command_status(args: argparse.Namespace) -> int:
    result = run_git(vault_root(args), ["status", "--short"])
    sys.stdout.write(result.stdout)
    return 0


def publish_impl(args: argparse.Namespace) -> int:
    root = vault_root(args)
    if not BRANCH_PATTERN.fullmatch(args.branch) or ".." in args.branch or args.branch.endswith("/"):
        raise VaultError("Invalid branch name")
    errors = validate_vault(root, unlock(root, args))
    if errors:
        raise VaultError("Refusing to publish an invalid vault: " + "; ".join(errors))
    staged_before = run_git(root, ["diff", "--cached", "--name-only"]).stdout.splitlines()
    unrelated = [
        path
        for path in staged_before
        if path not in {MANIFEST_NAME, KEY_ENVELOPE_NAME, ".gitignore"}
        and not path.replace("\\", "/").startswith(f"{OBJECTS_DIR}/")
    ]
    if unrelated:
        raise VaultError("Refusing to include unrelated staged files: " + ", ".join(unrelated))
    current = run_git(root, ["branch", "--show-current"]).stdout.strip()
    if current != args.branch:
        existing = run_git(root, ["branch", "--list", args.branch]).stdout.strip()
        run_git(root, ["switch", args.branch] if existing else ["switch", "-c", args.branch])
    run_git(root, ["add", "--", MANIFEST_NAME, KEY_ENVELOPE_NAME, OBJECTS_DIR, ".gitignore"])
    diff = subprocess.run(
        ["git", "-C", str(root), "diff", "--cached", "--quiet"],
        text=True,
        capture_output=True,
        check=False,
    )
    if diff.returncode == 0:
        print("No vault changes to publish")
        return 0
    if diff.returncode != 1:
        raise VaultError((diff.stderr or "git diff failed").strip())
    run_git(root, ["commit", "-m", args.message])
    if not args.no_push:
        run_git(root, ["push", "-u", args.remote, "HEAD"])
    print(f"Published vault changes on branch {args.branch}")
    return 0


def add_key_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--key-file", help="Read the vault passphrase from this file")
    parser.add_argument("--prompt-key", action="store_true", help="Prompt for the vault passphrase on a TTY")


def add_selectors(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--id", dest="ids", action="append", help="Select an item id; repeatable")
    parser.add_argument("--tag", dest="tags", action="append", help="Require a tag; repeatable and combined with AND")
    parser.add_argument("--profile", help="Apply profile rules")
    parser.add_argument("--os", dest="os_name", choices=["windows", "linux", "darwin"], help="Apply OS rules")


def apply_saved_defaults(args: argparse.Namespace) -> None:
    if args.command in {"configure", "defaults", "clone", "init"}:
        return
    settings = load_defaults(args)
    explicit_vault = bool(args.vault)
    saved_vault = settings.get("vault")
    same_vault = not explicit_vault
    if explicit_vault and saved_vault:
        same_vault = Path(args.vault).expanduser().resolve() == Path(saved_vault).expanduser().resolve()
    if not args.vault and saved_vault:
        args.vault = saved_vault
    if same_vault and hasattr(args, "key_file") and not args.key_file:
        args.key_file = settings.get("keyFile")
    if args.command == "apply":
        args.profile = args.profile or (settings.get("profile") if same_vault else None) or "default"
        args.os_name = args.os_name or (settings.get("os") if same_vault else None) or normalize_os()
    if args.command == "pull":
        args.remote = args.remote or (settings.get("remote") if same_vault else None) or "origin"
        args.branch = args.branch or (settings.get("branch") if same_vault else None) or "main"
    if args.command == "publish":
        args.remote = args.remote or (settings.get("remote") if same_vault else None) or "origin"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", help="Vault checkout directory; defaults to the saved configuration")
    parser.add_argument("--config-file", help="Override the per-user defaults file")
    parser.add_argument("--debug", action="store_true", help="Show Python tracebacks")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize a new encrypted vault")
    add_key_options(init_parser)
    init_parser.add_argument("--git", action="store_true", help="Initialize a Git repository")
    init_parser.set_defaults(func=command_init)

    clone_parser = subparsers.add_parser("clone", help="Clone a remote vault repository")
    clone_parser.add_argument("repository")
    clone_parser.add_argument("destination")
    clone_parser.add_argument("--branch", help="Branch to check out")
    clone_parser.set_defaults(func=command_clone)

    configure_parser = subparsers.add_parser("configure", help="Save the default repository, key, and rules")
    configure_parser.add_argument("--repository", help="Git repository URL")
    configure_parser.add_argument("--checkout", help="Persistent checkout directory")
    key_group = configure_parser.add_mutually_exclusive_group()
    key_group.add_argument("--key-file", help="Existing vault key file for migration or advanced use")
    key_group.add_argument(
        "--password-stdin", "--key-stdin", dest="key_stdin", action="store_true",
        help="Read the Vault password from standard input and store it for future AI use",
    )
    configure_parser.add_argument("--profile", help="Default rule profile")
    configure_parser.add_argument("--os", dest="os_name", choices=["windows", "linux", "darwin"])
    configure_parser.add_argument("--remote", help="Default Git remote")
    configure_parser.add_argument("--branch", help="Default branch to pull")
    configure_parser.add_argument("--no-clone", action="store_true", help="Require an existing local checkout")
    configure_parser.set_defaults(func=command_configure)

    defaults_parser = subparsers.add_parser("defaults", help="Show the saved default configuration")
    defaults_parser.add_argument("--json", action="store_true")
    defaults_parser.set_defaults(func=command_defaults)

    list_parser = subparsers.add_parser("list", help="List catalog metadata without decrypting content")
    add_selectors(list_parser)
    list_parser.add_argument("--json", action="store_true")
    list_parser.set_defaults(func=command_list)

    search_parser = subparsers.add_parser("search", help="Search metadata and optionally decrypted content")
    add_key_options(search_parser)
    add_selectors(search_parser)
    search_parser.add_argument("query")
    search_parser.add_argument("--content", action="store_true", help="Search decrypted content and print matching ids")
    search_parser.add_argument("--show-matches", action="store_true", help="Print matching plaintext lines")
    search_parser.set_defaults(func=command_search)

    read_parser = subparsers.add_parser("read", help="Write one decrypted item to stdout")
    add_key_options(read_parser)
    read_parser.add_argument("item_id")
    read_parser.set_defaults(func=command_read)

    add_parser = subparsers.add_parser("add", help="Add and encrypt an item")
    add_key_options(add_parser)
    add_parser.add_argument("item_id")
    add_parser.add_argument("--from", dest="input", required=True, help="Plaintext file or - for stdin")
    add_parser.add_argument("--description")
    add_parser.add_argument("--format", choices=sorted(SUPPORTED_FORMATS), default="text")
    add_parser.add_argument("--mode", default="0600")
    add_parser.add_argument("--item-tag", dest="item_tags", action="append")
    add_parser.add_argument("--item-profile", dest="item_profiles", action="append")
    add_parser.add_argument("--item-os", dest="item_os", action="append", choices=["*", "windows", "linux", "darwin"])
    add_parser.add_argument("--target", action="append", help="OS=relative/path; repeatable")
    add_parser.set_defaults(func=command_add)

    update_parser = subparsers.add_parser("update", help="Replace plaintext and/or metadata for an item")
    add_key_options(update_parser)
    update_parser.add_argument("item_id")
    update_parser.add_argument("--from", dest="input", help="Replacement plaintext file or - for stdin")
    update_parser.add_argument("--description")
    update_parser.add_argument("--format", choices=sorted(SUPPORTED_FORMATS))
    update_parser.add_argument("--mode")
    update_parser.add_argument("--item-tag", dest="item_tags", action="append")
    update_parser.add_argument("--item-profile", dest="item_profiles", action="append")
    update_parser.add_argument("--item-os", dest="item_os", action="append", choices=["*", "windows", "linux", "darwin"])
    update_parser.add_argument("--target", action="append", help="Replace all targets with OS=relative/path values")
    update_parser.set_defaults(func=command_update)

    delete_parser = subparsers.add_parser("delete", help="Delete an item from the vault")
    add_key_options(delete_parser)
    delete_parser.add_argument("item_id")
    delete_parser.add_argument("--yes", action="store_true")
    delete_parser.set_defaults(func=command_delete)

    apply_parser = subparsers.add_parser("apply", help="Decrypt selected items into a home directory")
    add_key_options(apply_parser)
    add_selectors(apply_parser)
    apply_parser.add_argument("--home", required=True, help="Destination home directory")
    apply_parser.add_argument("--dry-run", action="store_true")
    apply_parser.add_argument("--force", action="store_true", help="Allow updates to existing files")
    apply_parser.set_defaults(func=command_apply)

    validate_parser = subparsers.add_parser("validate", help="Validate the catalog and encrypted objects")
    add_key_options(validate_parser)
    validate_parser.add_argument("--decrypt", action="store_true", help="Decrypt and validate every plaintext item")
    validate_parser.set_defaults(func=command_validate)

    rekey_parser = subparsers.add_parser("rekey", help="Change the passphrase wrapping the vault master key")
    add_key_options(rekey_parser)
    rekey_parser.add_argument("--new-key-file", help="Read the new key from this file; otherwise CONFIG_VAULT_NEW_KEY")
    rekey_parser.add_argument("--prompt-new-key", action="store_true")
    rekey_parser.set_defaults(func=command_rekey)

    pull_parser = subparsers.add_parser("pull", help="Fast-forward a local checkout")
    pull_parser.add_argument("--remote")
    pull_parser.add_argument("--branch")
    pull_parser.set_defaults(func=command_pull)

    status_parser = subparsers.add_parser("status", help="Show Git changes in the vault checkout")
    status_parser.set_defaults(func=command_status)

    publish_parser = subparsers.add_parser("publish", help="Validate, commit, and optionally push a branch")
    add_key_options(publish_parser)
    publish_parser.add_argument("--branch", required=True)
    publish_parser.add_argument("--message", required=True)
    publish_parser.add_argument("--remote")
    publish_parser.add_argument("--no-push", action="store_true")
    publish_parser.set_defaults(func=publish_impl)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        apply_saved_defaults(args)
        return int(args.func(args))
    except VaultError as exc:
        if args.debug:
            raise
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
