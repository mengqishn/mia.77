#!/bin/zsh
set -euo pipefail

CHROME_APP_NAME="${CHROME_APP_NAME:-Google Chrome}"
CHROME_PATH="${CHROME_PATH:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
REMOTE_DEBUG_PORT="${REMOTE_DEBUG_PORT:-9223}"
USER_DATA_DIR="${USER_DATA_DIR:-$HOME/.codex/redbook-chrome-cdp}"
PROFILE_DIRECTORY="${PROFILE_DIRECTORY:-Default}"
START_URL="${START_URL:-https://www.xiaohongshu.com/}"

if [[ ! -x "$CHROME_PATH" ]]; then
  echo "Chrome executable not found: $CHROME_PATH" >&2
  exit 1
fi

echo "Launching Chrome with remote debugging on port $REMOTE_DEBUG_PORT"
echo "Profile: $PROFILE_DIRECTORY"
echo "User data dir: $USER_DATA_DIR"

mkdir -p "$USER_DATA_DIR"

open -na "$CHROME_APP_NAME" --args \
  --remote-debugging-port="$REMOTE_DEBUG_PORT" \
  --user-data-dir="$USER_DATA_DIR" \
  --profile-directory="$PROFILE_DIRECTORY" \
  --no-first-run \
  --new-window "$START_URL"

for _ in {1..20}; do
  if /usr/bin/curl -fsS "http://127.0.0.1:${REMOTE_DEBUG_PORT}/json/version" >/dev/null 2>&1; then
    echo "CDP is ready at http://127.0.0.1:${REMOTE_DEBUG_PORT}"
    exit 0
  fi
  sleep 1
done

echo "CDP did not come up on port ${REMOTE_DEBUG_PORT}." >&2
echo "If Chrome is already using the same profile, fully quit that Chrome instance and rerun this script." >&2
exit 1
