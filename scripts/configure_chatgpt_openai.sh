#!/usr/bin/env bash
set -euo pipefail

OPENCODE_BIN="${OPENCODE_BIN:-opencode}"
PROVIDER="${OPENCODE_PROVIDER:-openai}"

if ! command -v "$OPENCODE_BIN" >/dev/null 2>&1 && [[ ! -x "$OPENCODE_BIN" ]]; then
  echo "OpenCode not found: $OPENCODE_BIN" >&2
  exit 1
fi

echo "Checking OpenCode auth..."
"$OPENCODE_BIN" auth list || true

echo
echo "Available models for provider '$PROVIDER':"
MODELS="$("$OPENCODE_BIN" models "$PROVIDER" 2>&1 || true)"
printf '%s\n' "$MODELS"

MODEL="${OPENCODE_MODEL:-}"
if [[ -z "$MODEL" ]]; then
  MODEL="$(printf '%s\n' "$MODELS" | awk -v p="$PROVIDER/" '$1 ~ "^" p {print $1; exit}')"
fi

if [[ -z "$MODEL" ]]; then
  cat >&2 <<EOF
No $PROVIDER model was found.

Run:
  opencode
Then inside OpenCode:
  /connect
Choose:
  OpenAI -> ChatGPT Plus/Pro

After browser OAuth, run:
  /models

Then rerun this script.
EOF
  exit 2
fi

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"
CONFIG_FILE="$CONFIG_DIR/opencode.json"
mkdir -p "$CONFIG_DIR"

python3 - "$CONFIG_FILE" "$MODEL" "$PROVIDER" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
model = sys.argv[2]
provider = sys.argv[3]

data = {}
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except json.JSONDecodeError:
        backup = path.with_suffix(path.suffix + ".bak")
        backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"Warning: invalid JSON backed up to {backup}")
        data = {}

data["$schema"] = "https://opencode.ai/config.json"
data["model"] = model
data["enabled_providers"] = [provider]

path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"Configured {path}")
print(f"model={model}")
print(f"enabled_providers=[{provider}]")
PY

echo
echo "Verification:"
"$OPENCODE_BIN" run --standalone --model "$MODEL" "Ответь одним словом: OK"
