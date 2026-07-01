#!/usr/bin/env bash

set -euo pipefail

DASHBOARD_URL="${1:?dashboard url required}"
CURSOR_TIMEOUT="${2:?cursor timeout required}"
PROFILE_DIR="${3:?profile dir required}"

pkill -f 'firefox --kiosk' 2>/dev/null || true
pkill unclutter 2>/dev/null || true

if command -v unclutter >/dev/null 2>&1; then
    unclutter -idle "$CURSOR_TIMEOUT" -root &
fi

exec firefox --kiosk --no-remote --profile "$PROFILE_DIR" "$DASHBOARD_URL"