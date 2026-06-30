#!/bin/bash
set -e

# D-Bus Systembus starten
dbus-daemon --system --fork

# Xvfb starten auf Display :99
Xvfb :99 -screen 0 1920x1080x24 &
XVFB_PID=$!
sleep 2

# FastAPI Backend starten auf Port 8000
dashboard-weather &
APP_PID=$!

# Auf den Server warten (max. 10 Sekunden)
for i in $(seq 1 10); do
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo "Dashboard API ist bereit"
        break
    fi
    sleep 1
done

# Chromium im Kiosk-Modus (Software-Rendering)
DISPLAY=:99 chromium \
    --kiosk \
    --no-sandbox \
    --disable-gpu \
    --disable-gpu-compositing \
    --disable-software-rasterizer \
    --disable-infobars \
    --disable-features=TranslateUI \
    --disable-session-crashed-bubble \
    --disable-pinch \
    --disable-restore-session-state \
    --no-first-run \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --disable-extensions \
    --disable-default-apps \
    --disable-sync \
    --disable-translate \
    --disable-features=VizDisplayCompositor \
    --disable-features=UseSkiaRenderer \
    --kiosk http://localhost:8000 &
BROWSER_PID=$!

# Auf alle Prozesse warten
wait $APP_PID
wait $XVFB_PID
wait $BROWSER_PID