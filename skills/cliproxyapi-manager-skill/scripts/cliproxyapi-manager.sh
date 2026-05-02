#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$SCRIPT_DIR/cliproxyapi_manager.py" "$@"
elif command -v python >/dev/null 2>&1; then
  exec python "$SCRIPT_DIR/cliproxyapi_manager.py" "$@"
else
  echo "Python 3.8+ is required but was not found in PATH." >&2
  exit 127
fi
