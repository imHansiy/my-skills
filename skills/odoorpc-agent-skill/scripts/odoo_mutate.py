#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "odoorpc>=0.10,<1",
#   "PyYAML>=6,<7",
# ]
# ///
"""Guarded OdooRPC create/update/delete operations for the odoorpc-agent skill."""
from __future__ import annotations

import argparse
from typing import Any, Dict, List

from odoo_common import (
    connect,
    enforce_mutation_safety,
    json_dump,
    make_context,
    parse_fields,
    parse_ids,
    parse_json_object,
    read_snapshot,
    run_main,
    save_snapshot,
    SkillError,
    SafetyError,
)

MAX_DEFAULT_MUTATION_IDS = 20
MAX_DEFAULT_DELETE_IDS = 5


def changed_fields(values: Dict[str, Any]) -> List[str]:
    return sorted(values.keys())


def cmd_create(args: argparse.Namespace) -> None:
    values = parse_json_object(args.values_json, "--values-json")
    enforce_mutation_safety(args.model, values, allow_protected=args.allow_protected)

    odoo, profile = connect(args.profile)
    context = make_context(args.quiet_mail)
    payload = {
        "ok": True,
        "profile": profile.name,
        "operation": "create",
        "model": args.model,
        "values": values,
        "dry_run": not args.execute,
        "context": context,
    }
    if not args.execute:
        payload["message"] = "Dry-run only. Add --execute --confirm CREATE to create the record."
        json_dump(payload)
        return
    if args.confirm != "CREATE":
        raise SafetyError("Create execution requires --confirm CREATE")

    Model = odoo.env[args.model]
    if context:
        new_id = Model.with_context(**context).create(values)
    else:
        new_id = Model.create(values)
    after = read_snapshot(odoo, args.model, [new_id], None)
    snapshot = save_snapshot(profile, "create", args.model, [new_id], before=None, after=after)
    payload.update({"created_id": new_id, "after": after, "snapshot_path": str(snapshot)})
    json_dump(payload)


def cmd_update(args: argparse.Namespace) -> None:
    ids = parse_ids(args.ids)
    values = parse_json_object(args.values_json, "--values-json")
    if len(ids) > args.max_records:
        raise SafetyError(f"Refusing to update {len(ids)} records; --max-records is {args.max_records}.")
    enforce_mutation_safety(args.model, values, allow_protected=args.allow_protected)

    odoo, profile = connect(args.profile)
    fields = sorted(set(["id", "display_name"] + changed_fields(values) + (parse_fields(args.snapshot_fields) or [])))
    before = read_snapshot(odoo, args.model, ids, fields)
    context = make_context(args.quiet_mail)
    payload = {
        "ok": True,
        "profile": profile.name,
        "operation": "update",
        "model": args.model,
        "ids": ids,
        "fields_to_change": changed_fields(values),
        "values": values,
        "before": before,
        "dry_run": not args.execute,
        "context": context,
    }
    if not args.execute:
        snapshot = save_snapshot(profile, "update-dry-run", args.model, ids, before=before, after=None)
        payload["message"] = "Dry-run only. Review before-values and add --execute --confirm UPDATE to write."
        payload["snapshot_path"] = str(snapshot)
        json_dump(payload)
        return
    if args.confirm != "UPDATE":
        raise SafetyError("Update execution requires --confirm UPDATE")

    Model = odoo.env[args.model]
    if context:
        ok = Model.with_context(**context).write(ids, values)
    else:
        ok = Model.write(ids, values)
    after = read_snapshot(odoo, args.model, ids, fields)
    snapshot = save_snapshot(profile, "update", args.model, ids, before=before, after=after)
    payload.update({"write_result": ok, "after": after, "snapshot_path": str(snapshot)})
    json_dump(payload)


def cmd_delete(args: argparse.Namespace) -> None:
    ids = parse_ids(args.ids)
    if len(ids) > args.max_records:
        raise SafetyError(f"Refusing to delete {len(ids)} records; --max-records is {args.max_records}.")
    enforce_mutation_safety(args.model, None, allow_protected=args.allow_protected)

    odoo, profile = connect(args.profile)
    before = read_snapshot(odoo, args.model, ids, parse_fields(args.snapshot_fields))
    payload = {
        "ok": True,
        "profile": profile.name,
        "operation": "delete",
        "model": args.model,
        "ids": ids,
        "before": before,
        "dry_run": not args.execute,
    }
    if args.prefer_archive and _model_has_active(odoo, args.model):
        payload["archive_available"] = True
        payload["message"] = "Model has an active field. Prefer `archive` over `delete` unless deletion is explicitly required."
    if not args.execute:
        snapshot = save_snapshot(profile, "delete-dry-run", args.model, ids, before=before, after=None)
        payload["message"] = payload.get("message", "Dry-run only. Add --execute --confirm DELETE to unlink records.")
        payload["snapshot_path"] = str(snapshot)
        json_dump(payload)
        return
    if args.confirm != "DELETE":
        raise SafetyError("Delete execution requires --confirm DELETE")

    result = odoo.env[args.model].unlink(ids)
    snapshot = save_snapshot(profile, "delete", args.model, ids, before=before, after=None)
    payload.update({"unlink_result": result, "snapshot_path": str(snapshot)})
    json_dump(payload)


def cmd_archive(args: argparse.Namespace) -> None:
    ids = parse_ids(args.ids)
    if len(ids) > args.max_records:
        raise SafetyError(f"Refusing to archive {len(ids)} records; --max-records is {args.max_records}.")
    enforce_mutation_safety(args.model, {"active": False}, allow_protected=args.allow_protected)
    odoo, profile = connect(args.profile)
    if not _model_has_active(odoo, args.model):
        raise SkillError(f"Model '{args.model}' does not appear to have an 'active' field.")
    before = read_snapshot(odoo, args.model, ids, ["id", "display_name", "active"])
    payload = {
        "ok": True,
        "profile": profile.name,
        "operation": "archive",
        "model": args.model,
        "ids": ids,
        "before": before,
        "dry_run": not args.execute,
    }
    if not args.execute:
        snapshot = save_snapshot(profile, "archive-dry-run", args.model, ids, before=before, after=None)
        payload["message"] = "Dry-run only. Add --execute --confirm ARCHIVE to set active=false."
        payload["snapshot_path"] = str(snapshot)
        json_dump(payload)
        return
    if args.confirm != "ARCHIVE":
        raise SafetyError("Archive execution requires --confirm ARCHIVE")
    result = odoo.env[args.model].write(ids, {"active": False})
    after = read_snapshot(odoo, args.model, ids, ["id", "display_name", "active"])
    snapshot = save_snapshot(profile, "archive", args.model, ids, before=before, after=after)
    payload.update({"write_result": result, "after": after, "snapshot_path": str(snapshot)})
    json_dump(payload)


def _model_has_active(odoo: Any, model: str) -> bool:
    try:
        return "active" in odoo.env[model].fields_get(["active"])
    except Exception:
        return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Guarded OdooRPC mutations. Defaults to dry-run. Outputs JSON.",
        epilog="Examples:\n"
        "  uv run scripts/odoo_mutate.py create --profile local --model res.partner --values-json '{\"name\":\"Demo\"}'\n"
        "  uv run scripts/odoo_mutate.py create --profile local --model res.partner --values-json '{\"name\":\"Demo\"}' --execute --confirm CREATE\n"
        "  uv run scripts/odoo_mutate.py update --profile local --model res.partner --ids 12 --values-json '{\"email\":\"new@example.com\"}'\n"
        "  uv run scripts/odoo_mutate.py update --profile local --model res.partner --ids 12 --values-json '{\"email\":\"new@example.com\"}' --execute --confirm UPDATE\n"
        "  uv run scripts/odoo_mutate.py archive --profile local --model res.partner --ids 12 --execute --confirm ARCHIVE\n"
        "  uv run scripts/odoo_mutate.py delete --profile local --model res.partner --ids 99 --execute --confirm DELETE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--profile", help="Profile name. Defaults to config default_profile.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("create", help="Create a record. Dry-run unless --execute --confirm CREATE.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--values-json", required=True)
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--confirm")
    sp.add_argument("--quiet-mail", action="store_true")
    sp.add_argument("--allow-protected", action="store_true")
    sp.set_defaults(func=cmd_create)

    sp = sub.add_parser("update", help="Update exact IDs. Dry-run unless --execute --confirm UPDATE.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--ids", required=True)
    sp.add_argument("--values-json", required=True)
    sp.add_argument("--snapshot-fields", help="Extra comma-separated fields to include in before/after snapshot.")
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--confirm")
    sp.add_argument("--quiet-mail", action="store_true")
    sp.add_argument("--allow-protected", action="store_true")
    sp.add_argument("--max-records", type=int, default=MAX_DEFAULT_MUTATION_IDS)
    sp.set_defaults(func=cmd_update)

    sp = sub.add_parser("archive", help="Set active=false on exact IDs. Safer than delete when supported.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--ids", required=True)
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--confirm")
    sp.add_argument("--allow-protected", action="store_true")
    sp.add_argument("--max-records", type=int, default=MAX_DEFAULT_MUTATION_IDS)
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("delete", help="Unlink exact IDs. Dry-run unless --execute --confirm DELETE.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--ids", required=True)
    sp.add_argument("--snapshot-fields", help="Comma-separated fields to include in before snapshot. Omit for all readable fields.")
    sp.add_argument("--execute", action="store_true")
    sp.add_argument("--confirm")
    sp.add_argument("--allow-protected", action="store_true")
    sp.add_argument("--prefer-archive", action="store_true", default=True)
    sp.add_argument("--max-records", type=int, default=MAX_DEFAULT_DELETE_IDS)
    sp.set_defaults(func=cmd_delete)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    run_main(main)
