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
echo "Available models (filtering provider '$PROVIDER'):"
MODELS="$("$OPENCODE_BIN" models 2>&1 || true)"
printf '%s\n' "$MODELS" | awk -v p="$PROVIDER/" '$1 ~ "^" p'

MODEL="${OPENCODE_MODEL:-}"

if [[ -z "$MODEL" ]]; then
  mapfile -t CANDIDATES < <(
    printf '%s\n' "$MODELS" |
      awk -v p="$PROVIDER/" '$1 ~ "^" p {print $1}' |
      awk '!seen[$0]++' |
      awk '
        /gpt-5\.6-sol/ && !/-fast$/ {print "00 " $0; next}
        /gpt-5\.6-luna/ && !/-fast$/ {print "01 " $0; next}
        /gpt-5\.5$/ {print "02 " $0; next}
        /gpt-6-astra/ && !/-fast$/ {print "03 " $0; next}
        /codex/ {print "90 " $0; next}
        {print "50 " $0}
      ' |
      sort |
      cut -d' ' -f2-
  )

  echo
  echo "Probing models with the current ChatGPT/OpenAI auth..."
  for candidate in "${CANDIDATES[@]}"; do
    echo "  trying $candidate"
    set +e
    OUTPUT="$("$OPENCODE_BIN" run --standalone --model "$candidate" "Ответь одним словом: OK" 2>&1)"
    RC=$?
    set -e
    if [[ $RC -eq 0 ]]; then
      MODEL="$candidate"
      echo "  OK: $candidate"
      break
    fi
    printf '  failed: %s\n' "$OUTPUT" | tail -n 3
  done
fi

if [[ -z "$MODEL" ]]; then
  cat >&2 <<EOF
No OpenAI model worked with the current ChatGPT account authentication.

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

python3 - "$CONFIG_FILE" "$MODEL" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
model = sys.argv[2]

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

path.write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print(f"Configured {path}")
print(f"model={model}")
PY

echo
echo "Verification:"
"$OPENCODE_BIN" run --standalone --model "$MODEL" "Ответь одним словом: OK"
