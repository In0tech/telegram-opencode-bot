#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 1; }
command -v git >/dev/null || { echo "git not found" >&2; exit 1; }
command -v opencode >/dev/null || {
  echo "opencode not found. Install OpenCode v2 first." >&2
  exit 1
}

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env."
  echo "Edit TELEGRAM_BOT_TOKEN and ALLOWED_TELEGRAM_USER_IDS before starting."
fi

echo
echo "Installed successfully."
echo "Next:"
echo "  nano .env"
echo "  source .venv/bin/activate"
echo "  python bot.py"
