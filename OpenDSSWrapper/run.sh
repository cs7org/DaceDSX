#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
    echo "Usage: $0 SCENARIO_ID INSTANCE_ID [--config FILE]" >&2
    exit 2
fi
if [[ ! $1 =~ ^[A-Za-z0-9_-]+$ || ! $2 =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "Scenario and instance IDs must use letters, digits, underscores or hyphens" >&2
    exit 2
fi
WRAPPER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${OPENDSS_PYTHON:-$WRAPPER_DIR/.venv/bin/python}"
if [[ -z "${OPENDSS_PYTHON:-}" && -x "$WRAPPER_DIR/.venv-linux/bin/python" ]]; then
    PYTHON_BIN="$WRAPPER_DIR/.venv-linux/bin/python"
fi
if [[ ! -x "$PYTHON_BIN" ]]; then
    if [[ -n "${OPENDSS_PYTHON:-}" ]]; then
        echo "OPENDSS_PYTHON is not executable: $PYTHON_BIN" >&2
        exit 2
    fi
    PYTHON_BIN="$(command -v python3)"
fi
mkdir -p "$WRAPPER_DIR/logs"
# SimService does not consume child stdout. Log directly to avoid a full pipe.
# exec keeps Python as the process SimService waits for and terminates.
exec "$PYTHON_BIN" -u "$WRAPPER_DIR/OpenDSSWrapper.py" "$@" \
    >> "$WRAPPER_DIR/logs/$1.$2.log" 2>&1
