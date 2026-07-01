#!/bin/bash
# entrypoint.sh - Kiosk startup for Firefox on a real host X display
set -e

# Configuration with defaults
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000}"
if [[ "$DASHBOARD_URL" =~ ^https?://([^/:]+)(:([0-9]+))? ]]; then
    DASHBOARD_HOST="${DASHBOARD_HOST:-${BASH_REMATCH[1]}}"
    DASHBOARD_PORT="${DASHBOARD_PORT:-${BASH_REMATCH[3]:-80}}"
else
    DASHBOARD_HOST="${DASHBOARD_HOST:-localhost}"
    DASHBOARD_PORT="${DASHBOARD_PORT:-8000}"
fi

MODE="${MODE:-host}"

CURSOR_TIMEOUT="${CURSOR_TIMEOUT:-5}"
RESOLUTION="${RESOLUTION:-1920x1080x24}"
FIREFOX_ARGS="${FIREFOX_ARGS:---kiosk --private-window}"
HOST_XAUTHORITY="${HOST_XAUTHORITY:-}"

detect_host_resolution() {
    if ! command -v xdpyinfo >/dev/null 2>&1; then
        return 1
    fi

    local display_id
    local result
    for display_id in $(ls /tmp/.X11-unix/ 2>/dev/null | tr -d 'X'); do
        result=$(DISPLAY=:"${display_id}" xdpyinfo 2>/dev/null | grep -oP 'dimensions:\s+\K[0-9]+x[0-9]+' | head -1)
        if [[ -n "$result" ]]; then
            echo "${result}x24"
            return 0
        fi
    done

    return 1
}

HOST_RESOLUTION="$(detect_host_resolution || true)"
if [[ -n "$HOST_RESOLUTION" ]]; then
    echo "Detected host X11 resolution: ${HOST_RESOLUTION}"
    RESOLUTION="$HOST_RESOLUTION"
else
    echo "Using configured display resolution: ${RESOLUTION}"
fi

echo "============================================"
echo " Dashboard Kiosk Starting"
echo " URL:        ${DASHBOARD_URL}"
echo " Host:       ${DASHBOARD_HOST}:${DASHBOARD_PORT}"
echo " Mode:       ${MODE}"
echo " Resolution: ${RESOLUTION}"
echo " Cursor:     Hide after ${CURSOR_TIMEOUT}s idle"
echo "============================================"

wait_for_dashboard() {
    echo "Waiting for dashboard server at ${DASHBOARD_HOST}:${DASHBOARD_PORT}..."
    until bash -c "exec 3<>/dev/tcp/${DASHBOARD_HOST}/${DASHBOARD_PORT}" 2>/dev/null; do
        echo "  Dashboard not reachable yet, retrying in 2s..."
        sleep 2
    done
    exec 3>&-
    echo "  Dashboard server is reachable"
}

launch_firefox() {
    echo "Launching Firefox in kiosk mode..."
    # shellcheck disable=SC2206
    local firefox_args=( $FIREFOX_ARGS )
    firefox "${firefox_args[@]}" "$DASHBOARD_URL" &
    FIREFOX_PID=$!
}

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/tmp/kiosk.Xauthority}"

if [[ -n "$HOST_XAUTHORITY" && -f "$HOST_XAUTHORITY" ]]; then
    cp "$HOST_XAUTHORITY" "$XAUTHORITY"
    chmod 600 "$XAUTHORITY"
fi

echo "[1/2] Waiting for host X display ${DISPLAY}..."
DISPLAY_SOCKET="/tmp/.X11-unix/X${DISPLAY#:}"
echo "  Expecting X11 socket at ${DISPLAY_SOCKET}"
until [[ -S "$DISPLAY_SOCKET" ]]; do
    echo "  Host X display socket not ready yet, retrying in 2s..."
    sleep 2
done

until xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; do
    echo "  Host X display not accepting connections yet, retrying in 2s..."
    sleep 2
done

echo "[2/2] Starting unclutter..."
unclutter -display "$DISPLAY" -idle "$CURSOR_TIMEOUT" -root &
UNCLUTTER_PID=$!

# Step 3: Wait for dashboard and launch Firefox in kiosk mode
wait_for_dashboard
launch_firefox

# Step 4: Keep container alive, auto-restart Firefox if it crashes
echo "Kiosk running. PID Firefox=$FIREFOX_PID Unclutter=$UNCLUTTER_PID"
echo "To stop: kill $FIREFOX_PID"
while true; do
    sleep 30
    
    # If Firefox is dead, restart it
    if ! kill -0 $FIREFOX_PID 2>/dev/null; then
        echo "Firefox crashed (exit code $?). Restarting in 3s..."
        sleep 3
        wait_for_dashboard
        launch_firefox
    fi
done