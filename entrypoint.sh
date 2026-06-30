#!/bin/bash
set -e

# Xvfb starten (virtueller Display :1, 1920x1080)
Xvfb :1 -screen 0 1920x1080x24 &
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

# Chromium im Kiosk-Modus
DISPLAY=:1 chromium \
    --kiosk \
    --no-sandbox \
    --disable-gpu \
    --disable-infobars \
    --disable-features=TranslateUI \
    --disable-session-crashed-bubble \
    --disable-pinch \
    --disable-restore-session-state \
    http://localhost:8000 &
BROWSER_PID=$!

# Auf Signale reagieren
wait $APP_PID
wait $XVFB_PID
wait $BROWSER_PID