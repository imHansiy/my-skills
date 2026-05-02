#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "odoorpc>=0.10,<1",
#   "PyYAML>=6,<7",
# ]
# ///
"""Read-only OdooRPC operations for the odoorpc-agent skill."""
from __future__ import annotations

import argparse
from typing import Any, Dict

from odoo_common import connect, detect_odoo_version, json_dump, parse_fields, parse_json_array, parse_json_object, run_main, SkillError


def cmd_test(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    user = odoo.env.user
    json_dump({
        "ok": True,
        "profile": profile.name,
        "database": profile.database,
        "uid": getattr(odoo, "uid", None),
        "user_name": getattr(user, "name", None),
        "user_login": getattr(user, "login", None),
        "configured_odoo_version": profile.odoo_version,
        "detected_odoo_version": detect_odoo_version(odoo),
    })


def cmd_fields(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    Model = odoo.env[args.model]
    attrs = parse_fields(args.attributes) or ["string", "type", "required", "readonly", "relation", "selection", "help"]
    result: Dict[str, Any] = Model.fields_get(parse_fields(args.fields), attributes=attrs)
    json_dump({"ok": True, "profile": profile.name, "model": args.model, "fields": result})


def cmd_search_read(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    domain = parse_json_array(args.domain_json, "--domain-json")
    fields = parse_fields(args.fields)
    kwargs: Dict[str, Any] = {"limit": args.limit, "offset": args.offset, "order": args.order}
    if fields:
        kwargs["fields"] = fields
    records = odoo.env[args.model].search_read(domain, **kwargs)
    json_dump({
        "ok": True,
        "profile": profile.name,
        "model": args.model,
        "domain": domain,
        "limit": args.limit,
        "offset": args.offset,
        "count_returned": len(records),
        "records": records,
    })


def cmd_count(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    domain = parse_json_array(args.domain_json, "--domain-json")
    count = odoo.env[args.model].search_count(domain)
    json_dump({"ok": True, "profile": profile.name, "model": args.model, "domain": domain, "count": count})


def cmd_read(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    if not ids:
        raise SkillError("--ids cannot be empty.")
    fields = parse_fields(args.fields)
    records = odoo.env[args.model].read(ids, fields) if fields else odoo.env[args.model].read(ids)
    json_dump({"ok": True, "profile": profile.name, "model": args.model, "ids": ids, "records": records})


def cmd_call_readonly(args: argparse.Namespace) -> None:
    odoo, profile = connect(args.profile)
    args_list = parse_json_array(args.args_json, "--args-json") if args.args_json else []
    kwargs = parse_json_object(args.kwargs_json, "--kwargs-json") if args.kwargs_json else {}
    if not args.i_know_method_is_readonly:
        raise SkillError("call-readonly requires --i-know-method-is-readonly to avoid accidental side effects.")
    Model = odoo.env[args.model]
    method = getattr(Model, args.method)
    result = method(*args_list, **kwargs)
    json_dump({
        "ok": True,
        "profile": profile.name,
        "model": args.model,
        "method": args.method,
        "result": result,
    })


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run read-only OdooRPC operations. Outputs JSON.",
        epilog="Examples:\n"
        "  uv run scripts/odoo_query.py --profile local test\n"
        "  uv run scripts/odoo_query.py --profile local fields --model res.partner --fields name,email\n"
        "  uv run scripts/odoo_query.py --profile local search-read --model res.partner --domain-json '[[\"is_company\",\"=\",true]]' --fields name,email --limit 10\n"
        "  uv run scripts/odoo_query.py --profile local count --model sale.order --domain-json '[[\"state\",\"=\",\"sale\"]]'",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--profile", help="Profile name. Defaults to config default_profile.")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("test", help="Connect and report current user/version.")
    sp.set_defaults(func=cmd_test)

    sp = sub.add_parser("fields", help="Inspect model fields.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--fields", help="Comma-separated field names to inspect. Omit for all fields.")
    sp.add_argument("--attributes", help="Comma-separated field metadata attributes. Defaults to common attributes.")
    sp.set_defaults(func=cmd_fields)

    sp = sub.add_parser("search-read", help="Search and read records using a JSON domain.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--domain-json", default="[]", help="Odoo domain as JSON array, e.g. '[[\"name\",\"ilike\",\"abc\"]]'.")
    sp.add_argument("--fields", help="Comma-separated fields to read.")
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--offset", type=int, default=0)
    sp.add_argument("--order", default="id desc")
    sp.set_defaults(func=cmd_search_read)

    sp = sub.add_parser("count", help="Count records matching a JSON domain.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--domain-json", default="[]")
    sp.set_defaults(func=cmd_count)

    sp = sub.add_parser("read", help="Read exact IDs.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--ids", required=True, help="Comma-separated IDs.")
    sp.add_argument("--fields", help="Comma-separated fields to read.")
    sp.set_defaults(func=cmd_read)

    sp = sub.add_parser("call-readonly", help="Call a method only when known to be read-only.")
    sp.add_argument("--model", required=True)
    sp.add_argument("--method", required=True)
    sp.add_argument("--args-json", help="JSON array of positional args.")
    sp.add_argument("--kwargs-json", help="JSON object of keyword args.")
    sp.add_argument("--i-know-method-is-readonly", action="store_true")
    sp.set_defaults(func=cmd_call_readonly)
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    run_main(main)
