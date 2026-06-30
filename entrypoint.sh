#!/bin/bash
set -e

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

# Chromium im Kiosk-Modus (direkt über DRM/KMS)
chromium \
    --kiosk \
    --no-sandbox \
    --use-gl=egl \
    --disable-gpu-compositing \
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
    --disable-gpu \
    --in-process-gpu \
    --enable-features=VaapiVideoDecoder \
    --ignore-gpu-blocklist \
    --gpu-device-index=0 \
    --kiosk http://localhost:8000 &
BROWSER_PID=$!

# Auf alle Prozesse warten
wait $APP_PID
wait $BROWSER_PID