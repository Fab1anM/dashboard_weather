#!/bin/bash
# entrypoint.sh - Kiosk startup for Firefox on Raspberry Pi
# Designed for pre-login kiosk mode (no desktop session)
set -e

# Configuration with defaults
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000}"
CURSOR_TIMEOUT="${CURSOR_TIMEOUT:-5}"
RESOLUTION="${RESOLUTION:-1920x1080x24}"
MODE="${MODE:-xvfb}"  # auto, host, xvfb

echo "============================================"
echo " Dashboard Kiosk Starting"
echo " URL:        ${DASHBOARD_URL}"
echo " Mode:       ${MODE}"
echo " Resolution: ${RESOLUTION}"
echo " Cursor:     Hide after ${CURSOR_TIMEOUT}s idle"
echo "============================================"

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

# Step 4: Launch Firefox in kiosk mode
echo "Launching Firefox in kiosk mode..."
firefox --kiosk "$DASHBOARD_URL" &
FIREFOX_PID=$!

# Step 5: Keep container alive, auto-restart Firefox if it crashes
echo "Kiosk running. PID Firefox=$FIREFOX_PID Unclutter=$UNCLUTTER_PID Xvfb=$XVFB_PID"
echo "To stop: kill $FIREFOX_PID"
while true; do
    sleep 30
    
    # If Firefox is dead, restart it
    if ! kill -0 $FIREFOX_PID 2>/dev/null; then
        echo "Firefox crashed (exit code $?). Restarting in 3s..."
        sleep 3
        firefox --kiosk "$DASHBOARD_URL" &
        FIREFOX_PID=$!
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