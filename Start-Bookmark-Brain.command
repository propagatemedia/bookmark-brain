#!/bin/bash
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/downloads/macos/"
  read -r -p "Press Return to close. "
  exit 1
fi
echo "Open http://127.0.0.1:${BOOKMARK_PORT:-5055} after the server starts."
echo "Keep this Terminal window open. Press Ctrl+C to stop."
exec python3 app.py
