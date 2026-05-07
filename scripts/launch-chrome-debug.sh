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
CHROME_BIN="$CHROME_APP/Contents/MacOS/Google Chrome"
LAUNCH_LOG="/tmp/chrome-debug-launch.log"

if [[ ! -x "$CHROME_BIN" ]]; then
  echo "Google Chrome binary not found at:"
  echo "  $CHROME_BIN"
  echo ""
  echo "If Chrome is installed under a different path (e.g. Chrome Canary,"
  echo "Beta, or a custom location), edit CHROME_BIN at the top of this"
  echo "script. Otherwise install Chrome from https://www.google.com/chrome/"
  exit 1
fi

# ---- Quit existing Chrome ----
# AppleScript graceful quit → SIGTERM → SIGKILL escalation. Chrome can
# linger for several seconds after a Cmd+Q if there are unsaved tabs.
echo "Quitting existing Chrome (if running)…"
osascript -e 'tell application "Google Chrome" to quit' 2>/dev/null || true
sleep 2
if pgrep -x "Google Chrome" > /dev/null; then
  echo "  graceful quit didn't finish — sending SIGTERM"
  pkill -TERM -x "Google Chrome" 2>/dev/null || true
  sleep 2
fi
if pgrep -x "Google Chrome" > /dev/null; then
  echo "  SIGTERM didn't work — sending SIGKILL"
  pkill -KILL -x "Google Chrome" 2>/dev/null || true
  sleep 1
fi

# ---- Launch Chrome with debug flag ----
# Use direct binary execution rather than `open -na "Google Chrome" --args`
# because macOS `open` sometimes silently drops --args when an existing
# Chrome instance is being recycled by launchd. Direct exec via the binary
# is reliable.
echo "Launching Chrome with --remote-debugging-port=$PORT (direct binary)…"
echo "  (launch log: $LAUNCH_LOG)"
nohup "$CHROME_BIN" \
  --remote-debugging-port="$PORT" \
  --remote-allow-origins='*' \
  > "$LAUNCH_LOG" 2>&1 &
CHROME_PID=$!
disown "$CHROME_PID" 2>/dev/null || true

# ---- Poll DevTools endpoint ----
# 127.0.0.1 (IPv4) explicitly, because `localhost` on macOS resolves to ::1
# but Chrome's --remote-debugging-port only binds IPv4. Up to 15 seconds
# of polling — Chrome can take 3-5s to fully initialize on busy machines.
ENDPOINT="http://127.0.0.1:$PORT/json/version"
echo "Waiting for DevTools endpoint at $ENDPOINT (up to 15s)…"
for i in $(seq 1 15); do
  if curl -fsS --max-time 2 "$ENDPOINT" > /dev/null 2>&1; then
    echo "✓ Chrome is reachable at $ENDPOINT (after ${i}s)"
    echo ""
    echo "Next steps:"
    echo "  node scripts/fetch-gated.mjs --connect-cdp --setup"
    echo "  node scripts/fetch-gated.mjs --connect-cdp --date \$(date +%F)"
    exit 0
  fi
  sleep 1
done

# ---- Diagnostics on failure ----
echo ""
echo "⚠ DevTools endpoint at $ENDPOINT did not respond within 15 seconds."
echo ""
echo "Diagnostics:"
echo ""

if pgrep -x "Google Chrome" > /dev/null; then
  PIDS=$(pgrep -x "Google Chrome" | tr '\n' ' ')
  echo "  • Chrome process state: RUNNING (pid: $PIDS)"
else
  echo "  • Chrome process state: NOT RUNNING"
  echo "    Chrome failed to launch or crashed early. See log below."
fi

echo "  • Port $PORT listeners:"
LSOF_OUT=$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null || true)
if [[ -z "$LSOF_OUT" ]]; then
  echo "    (nothing listening on port $PORT)"
else
  echo "$LSOF_OUT" | sed 's/^/    /'
fi

echo "  • Last 20 lines of Chrome launch log ($LAUNCH_LOG):"
if [[ -s "$LAUNCH_LOG" ]]; then
  tail -20 "$LAUNCH_LOG" | sed 's/^/    /'
else
  echo "    (empty — Chrome wrote no output to stdout/stderr)"
fi

echo ""
echo "Common causes:"
echo "  1. Chrome enterprise policy disabling --remote-debugging-port"
echo "     (check /Library/Managed Preferences/com.google.Chrome.plist)"
echo "  2. Profile lock contention — try restarting macOS, or use a"
echo "     separate user-data-dir:"
echo "       \"$CHROME_BIN\" --remote-debugging-port=$PORT \\"
echo "         --user-data-dir=/tmp/chrome-debug-profile"
echo "  3. Different Chrome installed (Canary, Beta, Chromium, Brave, etc.)"
echo "     Edit CHROME_BIN at the top of this script."
exit 1
