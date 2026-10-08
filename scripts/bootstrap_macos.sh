#!/usr/bin/env bash
# Crea un ambiente locale senza modificare Python di sistema.
set -euo pipefail
cd "$(dirname "$0")/.."
JAZZGPT_PYTHON="${JAZZGPT_PYTHON:-}"
if [[ -z "$JAZZGPT_PYTHON" ]]; then
  for candidate in /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert sys.version_info >= (3, 11)' >/dev/null 2>&1; then
      JAZZGPT_PYTHON="$candidate"
      break
    fi
  done
fi
if [[ -z "$JAZZGPT_PYTHON" ]]; then
  echo "Serve Python 3.11+ ARM64. Installa Python 3.12 o imposta JAZZGPT_PYTHON." >&2
  exit 1
fi
"$JAZZGPT_PYTHON" -c 'import platform, sys; assert sys.version_info >= (3, 11); print("Python:", platform.python_version(), platform.machine())'
if [[ ! -d .venv ]]; then
  "$JAZZGPT_PYTHON" -m venv .venv
fi
.venv/bin/python -c 'import sys; assert sys.version_info >= (3, 11), "Ricrea .venv con Python 3.11+"'
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m jazzgpt doctor
.venv/bin/python -m jazzgpt generate --tokens renders/demo.tokens.json
echo "Pronto. Apri JazzGPT.code-workspace in VS Code."
