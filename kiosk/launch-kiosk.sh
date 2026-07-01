#!/usr/bin/env bash

set -euo pipefail

KIOSK_COMPOSE_FILE="${1:?kiosk compose file required}"
DASHBOARD_COMPOSE_FILE="${2:?dashboard compose file required}"
DEFAULT_DASHBOARD_URL="${3:?dashboard url required}"
LOG_FILE="${HOME}/.cache/dashboard-kiosk-launch.log"

mkdir -p "$(dirname "$LOG_FILE")"
exec >>"$LOG_FILE" 2>&1

echo "==== $(date --iso-8601=seconds) dashboard-kiosk launcher start ===="

detect_display() {
    if [[ -n "${DISPLAY:-}" ]]; then
        echo "$DISPLAY"
        return 0
    fi

    local display_socket
    for display_socket in /tmp/.X11-unix/X*; do
        [[ -e "$display_socket" ]] || continue
        echo ":$(basename "$display_socket" | tr -d 'X')"
        return 0
    done

    echo ":0"
}

detect_xauthority() {
    local candidate

    candidate=$(find "/run/user/$(id -u)" -maxdepth 1 -type f \( -name '.mutter-Xwaylandauth.*' -o -name '.Xauthority' \) -size +0c -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
    if [[ -n "$candidate" && -f "$candidate" ]]; then
        echo "$candidate"
        return 0
    fi

    if [[ -n "${XAUTHORITY:-}" && -f "${XAUTHORITY}" && -s "${XAUTHORITY}" ]]; then
        echo "$XAUTHORITY"
        return 0
    fi

    for candidate in "$HOME/.Xauthority" "/run/user/$(id -u)/gdm/Xauthority"; do
        [[ -f "$candidate" && -s "$candidate" ]] || continue
        echo "$candidate"
        return 0
    done

    echo "$HOME/.Xauthority"
}

DISPLAY_VALUE="$(detect_display)"
XAUTHORITY_VALUE="$(detect_xauthority)"

echo "Launching kiosk with DISPLAY=${DISPLAY_VALUE} XAUTHORITY=${XAUTHORITY_VALUE}"
if [[ ! -f "$XAUTHORITY_VALUE" ]]; then
    echo "Warning: selected XAUTHORITY file does not exist yet"
elif [[ ! -s "$XAUTHORITY_VALUE" ]]; then
    echo "Warning: selected XAUTHORITY file is empty"
fi

until [[ -S "/tmp/.X11-unix/X${DISPLAY_VALUE#:}" ]]; do
    echo "Waiting for X11 socket for ${DISPLAY_VALUE}..."
    sleep 2
done

until xdpyinfo -display "$DISPLAY_VALUE" >/dev/null 2>&1; do
    echo "Waiting for display ${DISPLAY_VALUE} to accept connections..."
    sleep 2
done

/usr/bin/docker compose -f "$DASHBOARD_COMPOSE_FILE" up -d dashboard
DISPLAY="$DISPLAY_VALUE" \
XAUTHORITY="$XAUTHORITY_VALUE" \
DASHBOARD_URL="$DEFAULT_DASHBOARD_URL" \
/usr/bin/docker compose -f "$KIOSK_COMPOSE_FILE" up -d --pull always

echo "==== $(date --iso-8601=seconds) dashboard-kiosk launcher done ===="