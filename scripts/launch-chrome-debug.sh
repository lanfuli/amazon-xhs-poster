#!/usr/bin/env bash
# launch-chrome-debug.sh — launch Google Chrome (separate debug profile)
# with --remote-debugging-port=9222 so fetch-gated.mjs --connect-cdp can
# attach.
#
# Usage:
#   bash scripts/launch-chrome-debug.sh           # default port 9222
#   bash scripts/launch-chrome-debug.sh 9333      # custom port
#
# Notes:
# - Chrome 136+ refuses --remote-debugging-port with the default user
#   profile (security hardening). This script launches Chrome with a
#   DEDICATED profile at ~/.config/amazon-xhs-poster/chrome-debug-profile/
#   — a SEPARATE Chrome instance from your daily Chrome. Your daily Chrome
#   is never touched.
# - First run: a fresh Chrome window opens with empty profile. You manually
#   log into X / LinkedIn / wearesellers in that window once. Cookies
#   persist in the dedicated profile dir, so subsequent runs don't need
#   to log in again until cookies expire (~30 days for X / LinkedIn).
# - Subsequent runs: if the debug Chrome instance is already running, the
#   script detects it and exits immediately (no relaunch). Idempotent.
# - To start fresh / wipe logins:
#     rm -rf ~/.config/amazon-xhs-poster/chrome-debug-profile/

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
  Launches a SEPARATE Chrome instance with a dedicated profile at
  ~/.config/amazon-xhs-poster/chrome-debug-profile/ and
  --remote-debugging-port=<PORT>. Your daily Chrome is untouched —
  the two run in parallel as separate Chrome windows.

  Chrome 136+ refuses --remote-debugging-port with the default user
  profile (security policy preventing malicious sites from sniffing
  logged-in sessions), so a separate profile is required.

  Idempotent: if the debug Chrome is already running, exits early.

FIRST RUN
  An empty Chrome window opens. Manually log into:
    https://x.com/login
    https://www.linkedin.com/login
    https://www.wearesellers.com/account/login/
  Cookies persist in the dedicated profile until they expire (~30 days
  for X/LinkedIn).

WHY YOU'D RUN THIS
  fetch-gated.mjs --connect-cdp needs Chrome to expose CDP on a port.
  This script is the canonical way to start that Chrome.

TO RESET (wipe all logins)
  rm -rf ~/.config/amazon-xhs-poster/chrome-debug-profile/
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
# Chrome 136+ refuses --remote-debugging-port with the default user profile
# (security hardening to prevent malicious sites from sniffing logged-in
# sessions). We MUST use a separate user-data-dir. Pick a persistent path
# so cookies survive reboots — the user only logs in once and the profile
# stays valid until cookies expire (~30 days for X/LinkedIn).
PROFILE_DIR="${HOME}/.config/amazon-xhs-poster/chrome-debug-profile"

if [[ ! -x "$CHROME_BIN" ]]; then
  echo "Google Chrome binary not found at:"
  echo "  $CHROME_BIN"
  echo ""
  echo "If Chrome is installed under a different path (Canary, Beta, custom),"
  echo "edit CHROME_BIN at the top of this script. Otherwise install Chrome"
  echo "from https://www.google.com/chrome/"
  exit 1
fi

# Create profile dir (idempotent).
mkdir -p "$PROFILE_DIR"

# ---- Check if THIS profile's Chrome is already running ----
# We launch Chrome with our dedicated --user-data-dir. If a Chrome instance
# is already using that profile (from a previous run of this script), we
# don't need to relaunch — just verify it's listening on the debug port
# and exit early. This means subsequent runs don't disturb the user's
# daily Chrome at all.
ENDPOINT="http://127.0.0.1:$PORT/json/version"
if curl -fsS --max-time 2 "$ENDPOINT" > /dev/null 2>&1; then
  echo "✓ Chrome is already running with debug port $PORT (profile: $PROFILE_DIR)"
  echo "  Endpoint: $ENDPOINT"
  echo ""
  echo "Next steps:"
  echo "  node scripts/fetch-gated.mjs --connect-cdp --setup"
  echo "  node scripts/fetch-gated.mjs --connect-cdp --date \$(date +%F)"
  exit 0
fi

# ---- Launch Chrome with debug flag + dedicated profile ----
# Direct binary execution (more reliable than `open -na`). We do NOT
# touch the user's daily Chrome (different --user-data-dir means it's
# a separate Chrome instance running in parallel).
echo "Launching Chrome (separate debug profile at $PROFILE_DIR)…"
echo "  Note: this is a SEPARATE Chrome window from your daily Chrome."
echo "        Your daily Chrome is untouched. Persistent — log in once,"
echo "        cookies stick around."
echo "  (launch log: $LAUNCH_LOG)"

nohup "$CHROME_BIN" \
  --remote-debugging-port="$PORT" \
  --user-data-dir="$PROFILE_DIR" \
  --remote-allow-origins='*' \
  --no-first-run \
  --no-default-browser-check \
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
echo "  2. The dedicated profile dir is corrupted — wipe and retry:"
echo "       rm -rf $PROFILE_DIR"
echo "       bash scripts/launch-chrome-debug.sh"
echo "  3. Different Chrome installed (Canary, Beta, Chromium, Brave, etc.)"
echo "     Edit CHROME_BIN at the top of this script."
echo "  4. Inspect launch log for early-crash details:"
echo "       cat $LAUNCH_LOG"
exit 1
