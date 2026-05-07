#!/usr/bin/env bash
# launch-chrome-debug.sh — launch Google Chrome with --remote-debugging-port=9222
# so fetch-gated.mjs --connect-cdp can attach.
#
# Usage:
#   bash scripts/launch-chrome-debug.sh           # default port 9222
#   bash scripts/launch-chrome-debug.sh 9333      # custom port
#
# Notes:
# - This QUITS your existing Chrome (asks AppleScript to do it cleanly) and
#   relaunches with the debug flag. Open tabs are preserved by Chrome's
#   session restore, but you'll want to make sure nothing critical is in
#   flight before running.
# - Your normal Chrome profile (with all your logins) is loaded — that's
#   the whole point. Playwright connects via CDP, opens new tabs, fetches
#   from the configured X / LinkedIn / wearesellers sources, and closes
#   ONLY the tabs it opened. Your existing tabs are not touched.
# - Chrome must remain running with this flag every time you fetch. If you
#   reboot or quit Chrome normally, run this script again before fetching.

set -euo pipefail

# Help flag handling — bail out before any destructive action.
case "${1:-}" in
  -h|--help)
    cat <<'EOF'
launch-chrome-debug.sh — launch Chrome with --remote-debugging-port

USAGE
  bash scripts/launch-chrome-debug.sh           # default port 9222
  bash scripts/launch-chrome-debug.sh 9333      # custom port (must be numeric)
  bash scripts/launch-chrome-debug.sh --help    # this message

WHAT IT DOES
  Quits your existing Chrome cleanly, then relaunches it with
  --remote-debugging-port=<PORT>. Your normal profile + logins are
  preserved (Chrome's session restore picks up where you left off).

WHY YOU'D RUN THIS
  fetch-gated.mjs --connect-cdp needs Chrome to expose CDP on a port.
  That requires Chrome to be launched with the debug flag from a fully-
  quit state. Running this script is the simplest way to get there.

WARNING
  Make sure nothing critical is in flight in Chrome (active form, paid
  upload, etc.) before running. The script will close all Chrome windows.
EOF
    exit 0
    ;;
esac

PORT="${1:-9222}"

# Validate port is numeric to avoid surprises like passing --help here.
if ! [[ "$PORT" =~ ^[0-9]+$ ]]; then
  echo "Error: PORT must be a numeric value (got: $PORT)"
  echo "Run: bash scripts/launch-chrome-debug.sh --help"
  exit 1
fi
if (( PORT < 1024 || PORT > 65535 )); then
  echo "Error: PORT must be between 1024 and 65535 (got: $PORT)"
  exit 1
fi

# macOS-only path; if you're on Linux, replace with `google-chrome` or
# `chromium-browser` and adjust the quit logic.
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launch script targets macOS. On Linux, run:"
  echo "  google-chrome --remote-debugging-port=$PORT &"
  exit 1
fi

CHROME_APP="/Applications/Google Chrome.app"
if [[ ! -d "$CHROME_APP" ]]; then
  echo "Google Chrome not found at $CHROME_APP."
  echo "Install it from https://www.google.com/chrome/ first."
  exit 1
fi

echo "Quitting existing Chrome (if running)…"
osascript -e 'tell application "Google Chrome" to quit' 2>/dev/null || true
sleep 1

# In rare cases Chrome's process lingers; force kill if so.
if pgrep -x "Google Chrome" > /dev/null; then
  echo "Chrome still running — sending SIGTERM."
  pkill -TERM -x "Google Chrome" || true
  sleep 1
fi

echo "Launching Chrome with --remote-debugging-port=$PORT …"
open -na "Google Chrome" --args --remote-debugging-port="$PORT"

# Verify by hitting the DevTools endpoint. Use 127.0.0.1 explicitly because
# `localhost` on macOS resolves to ::1 (IPv6) but Chrome only binds IPv4
# for --remote-debugging-port. Retry for up to ~12 seconds since Chrome can
# take a few seconds to fully initialize the debug endpoint.
echo "Waiting for DevTools endpoint to come up (up to 12s)…"
ENDPOINT="http://127.0.0.1:$PORT/json/version"
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if curl -fsS "$ENDPOINT" > /dev/null 2>&1; then
    echo "✓ Chrome is reachable at http://127.0.0.1:$PORT (after ${i}s)"
    echo ""
    echo "Now run:"
    echo "  node scripts/fetch-gated.mjs --connect-cdp --setup"
    echo "  node scripts/fetch-gated.mjs --connect-cdp --date \$(date +%F)"
    exit 0
  fi
  sleep 1
done

echo "⚠ Chrome launched but DevTools endpoint at $ENDPOINT didn't respond"
echo "  within 12 seconds. Manual check:"
echo "    curl $ENDPOINT"
echo ""
echo "  If that returns JSON, Chrome is fine and you can proceed. If it"
echo "  still fails:"
echo "    1. Confirm Chrome window is open (not just Cmd+Q'd)"
echo "    2. Try: lsof -nP -iTCP:$PORT | grep LISTEN"
echo "       — should show 'Google Chrome' process listening"
echo "    3. Try a different port: bash scripts/launch-chrome-debug.sh 9333"
exit 1
