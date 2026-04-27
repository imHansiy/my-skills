#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "PyYAML>=6,<7",
#   "odoorpc>=0.10,<1",
# ]
# ///
"""Manage ~/.config/odoorpc/config.yaml profiles for the odoorpc-agent skill."""
from __future__ import annotations

import argparse
import sys
from typing import Any, Dict

from odoo_common import CONFIG_FILE, active_config_path, connect, detect_odoo_version, json_dump, load_config, redact_profile, run_main, save_config, SkillError, SUPPORTED_PROTOCOLS


def cmd_list(args: argparse.Namespace) -> None:
    cfg = load_config(allow_missing=True)
    profiles = cfg.get("profiles", {})
    json_dump({
        "ok": True,
        "config_path": str(active_config_path()),
        "canonical_config_path": str(CONFIG_FILE),
        "default_profile": cfg.get("default_profile"),
        "profiles": {name: redact_profile(raw) for name, raw in profiles.items()},
    })


def cmd_show(args: argparse.Namespace) -> None:
    cfg = load_config()
    profiles = cfg.get("profiles", {})
    raw = profiles.get(args.profile)
    if raw is None:
        raise SkillError(f"Profile not found: {args.profile}")
    json_dump({"ok": True, "profile": args.profile, "config": redact_profile(raw)})


def cmd_set_profile(args: argparse.Namespace) -> None:
    password = args.password
    if args.password_stdin:
        password = sys.stdin.read()
    if password is None:
        raise SkillError("Provide --password or --password-stdin.")
    password = password.rstrip("\n")
    if not password:
        raise SkillError("Password/API key cannot be empty.")
    if args.protocol not in SUPPORTED_PROTOCOLS:
        raise SkillError(f"--protocol must be one of: {sorted(SUPPORTED_PROTOCOLS)}")

    cfg = load_config(allow_missing=True)
    profiles: Dict[str, Any] = cfg.setdefault("profiles", {})
    profiles[args.profile] = {
        "host": args.host,
        "port": int(args.port),
        "protocol": args.protocol,
        "database": args.database,
        "username": args.username,
        "password": password,
        "timeout": int(args.timeout),
        "odoo_version": args.odoo_version,
    }
    if args.set_default or not cfg.get("default_profile"):
        cfg["default_profile"] = args.profile
    path = save_config(cfg)
    json_dump({
        "ok": True,
        "message": "Profile saved.",
        "config_path": str(path),
        "default_profile": cfg.get("default_profile"),
        "profile": args.profile,
        "saved": redact_profile(profiles[args.profile]),
    })


def cmd_detect_version(args: argparse.Namespace) -> None:
    cfg = load_config()
    odoo, profile = connect(args.profile)
    detected = detect_odoo_version(odoo)
    if not detected:
        raise SkillError("Connected successfully, but OdooRPC did not expose a server version.")

    if args.save:
        raw = cfg.get("profiles", {}).get(profile.name)
        if raw is None:
            raise SkillError(f"Profile not found while saving version: {profile.name}")
        raw["odoo_version"] = detected
        path = save_config(cfg)
    else:
        path = active_config_path()

    json_dump({
        "ok": True,
        "profile": profile.name,
        "database": profile.database,
        "configured_odoo_version": profile.odoo_version,
        "detected_odoo_version": detected,
        "saved": bool(args.save),
        "config_path": str(path),
    })


def cmd_remove_profile(args: argparse.Namespace) -> None:
    if args.confirm != "DELETE-PROFILE":
        raise SkillError("Removing a profile requires --confirm DELETE-PROFILE")
    cfg = load_config()
    profiles = cfg.get("profiles", {})
    if args.profile not in profiles:
        raise SkillError(f"Profile not found: {args.profile}")
    removed = redact_profile(profiles.pop(args.profile))
    if cfg.get("default_profile") == args.profile:
        cfg["default_profile"] = next(iter(profiles.keys()), None)
    path = save_config(cfg)
    json_dump({
        "ok": True,
        "message": "Profile removed.",
        "config_path": str(path),
        "removed_profile": args.profile,
        "removed": removed,
        "default_profile": cfg.get("default_profile"),
    })


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Manage named OdooRPC profiles in ~/.config/odoorpc/config.yaml.",
        epilog="Examples:\n"
        "  uv run scripts/odoo_config.py list\n"
        "  printf '%s' 'API_KEY' | uv run scripts/odoo_config.py set-profile --profile prod --host odoo.example.com --port 443 --protocol jsonrpc+ssl --database prod_db --username admin@example.com --password-stdin --set-default\n"
        "  uv run scripts/odoo_config.py show --profile prod\n"
        "  uv run scripts/odoo_config.py remove-profile --profile old --confirm DELETE-PROFILE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("list", help="List profiles with secrets redacted.")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show", help="Show one profile with secrets redacted.")
    sp.add_argument("--profile", required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("set-profile", help="Create or update a profile.")
    sp.add_argument("--profile", required=True, help="Profile name, e.g. local, staging, production, customer-a-prod.")
    sp.add_argument("--host", required=True, help="Odoo host without protocol, e.g. 127.0.0.1 or odoo.example.com.")
    sp.add_argument("--port", required=True, type=int, help="Odoo port, e.g. 8069 or 443.")
    sp.add_argument("--protocol", required=True, choices=sorted(SUPPORTED_PROTOCOLS), help="OdooRPC protocol.")
    sp.add_argument("--database", required=True, help="Odoo database name.")
    sp.add_argument("--username", required=True, help="Odoo login username/email.")
    secret = sp.add_mutually_exclusive_group(required=True)
    secret.add_argument("--password", help="Password or API key. Prefer --password-stdin to avoid shell history.")
    secret.add_argument("--password-stdin", action="store_true", help="Read password/API key from stdin.")
    sp.add_argument("--timeout", default=30, type=int)
    sp.add_argument("--odoo-version", help="Optional Odoo major/minor version for this profile, e.g. 16.0, 17.0, 18.0, 19.0.")
    sp.add_argument("--set-default", action="store_true", help="Make this the default profile.")
    sp.set_defaults(func=cmd_set_profile)

    sp = sub.add_parser("detect-version", help="Connect to a profile, detect the Odoo server version, and optionally save it.")
    sp.add_argument("--profile", required=True)
    sp.add_argument("--save", action="store_true", help="Write detected version to profiles.<name>.odoo_version.")
    sp.set_defaults(func=cmd_detect_version)

    sp = sub.add_parser("remove-profile", help="Remove a profile from the config file.")
    sp.add_argument("--profile", required=True)
    sp.add_argument("--confirm", required=True, help="Must equal DELETE-PROFILE.")
    sp.set_defaults(func=cmd_remove_profile)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    run_main(main)
