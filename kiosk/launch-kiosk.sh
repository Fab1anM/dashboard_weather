#!/usr/bin/env bash

set -euo pipefail

KIOSK_COMPOSE_FILE="${1:?kiosk compose file required}"
DASHBOARD_COMPOSE_FILE="${2:?dashboard compose file required}"
DEFAULT_DASHBOARD_URL="${3:?dashboard url required}"

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
    if [[ -n "${XAUTHORITY:-}" && -f "${XAUTHORITY}" ]]; then
        echo "$XAUTHORITY"
        return 0
    fi

    local candidate
    for candidate in \
        "$HOME/.Xauthority" \
        "/run/user/$(id -u)/gdm/Xauthority" \
        "/run/user/$(id -u)/.mutter-Xwaylandauth."*; do
        [[ -f "$candidate" ]] || continue
        echo "$candidate"
        return 0
    done

    echo "$HOME/.Xauthority"
}

DISPLAY_VALUE="$(detect_display)"
XAUTHORITY_VALUE="$(detect_xauthority)"

echo "Launching kiosk with DISPLAY=${DISPLAY_VALUE} XAUTHORITY=${XAUTHORITY_VALUE}"

/usr/bin/docker compose -f "$DASHBOARD_COMPOSE_FILE" up -d dashboard
DISPLAY="$DISPLAY_VALUE" \
XAUTHORITY="$XAUTHORITY_VALUE" \
DASHBOARD_URL="$DEFAULT_DASHBOARD_URL" \
/usr/bin/docker compose -f "$KIOSK_COMPOSE_FILE" up -d --pull always