#!/bin/bash
# entrypoint.sh - Kiosk startup for Firefox on Raspberry Pi
set -e

# Configuration with defaults
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000}"
CURSOR_TIMEOUT="${CURSOR_TIMEOUT:-5}"

echo "============================================"
echo " Dashboard Kiosk Starting"
echo " URL:        ${DASHBOARD_URL}"
echo " Resolution: ${RESOLUTION:-1920x1080x24}"
echo " Cursor:     Hide after ${CURSOR_TIMEOUT}s idle"
echo "============================================"

# Step 1: Verify X11 socket exists
if [ ! -S "/tmp/.X11-unix/X0" ]; then
    echo "ERROR: X11 socket /tmp/.X11-unix/X0 not found!"
    echo "  Make sure the container is run with:"
    echo "    -v /tmp/.X11-unix:/tmp/.X11-unix"
    exit 1
fi

echo "[1/3] X11 socket found"

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

# Step 4: Launch Firefox in kiosk mode
echo "Launching Firefox in kiosk mode..."
firefox --kiosk "$DASHBOARD_URL" &
FIREFOX_PID=$!

# Step 5: Keep container alive, auto-restart Firefox if it crashes
echo "Kiosk running. PID Firefox=$FIREFOX_PID Unclutter=$UNCLUTTER_PID"
while true; do
    # Wait 30 seconds before checking
    sleep 30
    
    # If Firefox is dead, restart it
    if ! kill -0 $FIREFOX_PID 2>/dev/null; then
        echo "Firefox crashed (exit code $?). Restarting in 3s..."
        sleep 3
        firefox --kiosk "$DASHBOARD_URL" &
        FIREFOX_PID=$!
    fi
done