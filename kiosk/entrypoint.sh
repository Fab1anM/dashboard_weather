#!/bin/bash
# entrypoint.sh - Kiosk startup for Firefox on Raspberry Pi
# Designed for pre-login kiosk mode (no desktop session)
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
CURSOR_TIMEOUT="${CURSOR_TIMEOUT:-5}"
RESOLUTION="${RESOLUTION:-1920x1080x24}"
MODE="${MODE:-xvfb}"  # auto, host, xvfb
FIREFOX_ARGS="${FIREFOX_ARGS:---kiosk --private-window}"

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
    echo "Using configured Xvfb resolution: ${RESOLUTION}"
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

# Step 1: Set up X display
# For pre-login kiosk, we ALWAYS use Xvfb since no X server is running yet
echo "[1/3] Starting Xvfb virtual display..."
Xvfb :99 -screen 0 $RESOLUTION -ac &
XVFB_PID=$!
sleep 2
export DISPLAY=:99
echo "  Xvfb running on :99 (PID $XVFB_PID)"

# Step 2: Start dbus if not running (Firefox sometimes needs it)
if ! pgrep -x dbus-daemon > /dev/null 2>&1; then
    echo "[2/3] Starting dbus..."
    mkdir -p /run/dbus
    dbus-daemon --system --fork 2>/dev/null || true
fi

# Step 3: Launch unclutter to hide cursor when idle
echo "[3/3] Starting unclutter..."
unclutter -root -idle "$CURSOR_TIMEOUT" -noreset &
UNCLUTTER_PID=$!

# Step 4: Wait for dashboard and launch Firefox in kiosk mode
wait_for_dashboard
launch_firefox

# Step 5: Keep container alive, auto-restart Firefox if it crashes
echo "Kiosk running. PID Firefox=$FIREFOX_PID Unclutter=$UNCLUTTER_PID Xvfb=$XVFB_PID"
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
    
    # If Xvfb is dead, restart it too
    if ! kill -0 $XVFB_PID 2>/dev/null; then
        echo "Xvfb crashed. Restarting in 3s..."
        sleep 3
        Xvfb :99 -screen 0 $RESOLUTION -ac &
        XVFB_PID=$!
        export DISPLAY=:99
    fi
done