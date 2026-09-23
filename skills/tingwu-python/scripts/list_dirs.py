"""列出文件夹（含 dirId），供 upload.py --dir 使用。

用法：
    python scripts/list_dirs.py
    python scripts/list_dirs.py --json
"""

from __future__ import annotations

import argparse
import sys

from _bootstrap import add_common, apply_sdk_arg, client, out


def main() -> int:
    ap = argparse.ArgumentParser(description="列出听悟文件夹")
    add_common(ap)
    args = ap.parse_args()

    apply_sdk_arg(args.sdk)
    c = client()
    flat = c.directory.flatten()

    if args.json:
        out(flat, as_json=True)
        return 0
    if not flat:
        print("(无文件夹)")
        return 0
    for d in flat:
        print(f"{d['dirId']:<10} {d['path']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(1)
