#!/usr/bin/env bash
#
# setup-kiosk.sh -- Install Firefox and configure a kiosk systemd service
#                  for the Dashboard weather app.
#
# Usage:  sudo bash setup-kiosk.sh [--host <host>] [--port 8000]
#
# Defaults: host = localhost, port = 8000

set -euo pipefail

HOST="${1:-localhost}"
if [[ "${2:-}" == "--port" ]]; then
    PORT="${3:-8000}"
else
    PORT="${2:-8000}"
fi

DASH_URL="http://${HOST}:${PORT}"
KIOSK_USER="${KIOSK_USER:-pi}"   # change to the target user if different

echo "=== Dashboard Kiosk Setup ==="
echo "Target URL : ${DASH_URL}"
echo "Kiosk user : ${KIOSK_USER}"
echo "=============================="

# ── 1. Install Firefox ──────────────────────────────────────────────────────
echo ""
echo "[1/5] Installing Firefox..."
apt-get update
apt-get install -y firefox unclutter xserver-xorg-input-all \
                   xserver-xorg-video-fbdev dbus-x11

# ── 2. Configure autologin for the kiosk user ──────────────────────────────
echo ""
echo "[2/5] Configuring autologin for user '${KIOSK_USER}'..."

# Detect the display manager (lightdm vs gdm3)
DM=""
if command -v lightdm &>/dev/null; then
    DM="lightdm"
elif command -v gdm3 &>/dev/null; then
    DM="gdm3"
fi

if [[ -z "$DM" ]]; then
    echo "WARNING: No supported display manager detected. Skipping autologin."
    echo "Manual autologin configuration may be required."
else
    case "$DM" in
        lightdm)
            # Configure /etc/lightdm/lightdm.conf
            CFG="/etc/lightdm/lightdm.conf"
            [[ -f "$CFG" ]] || touch "$CFG"
            sed -i '/^\[autologin\]/d' "$CFG"
            sed -i '/^\[login\]/d' "$CFG"
            sed -i '/^autologin-user=/d' "$CFG"
            sed -i '/^autologin-session=/d' "$CFG"
            cat >> "$CFG" <<CONF
[Seat:*]
autologin-user=${KIOSK_USER}
autologin-session=console
CONF
            ;;
        gdm3)
            # gdm3 autologin via GNOME config
            AUTHDIR="/etc/gdm3"
            [[ -f "$AUTHDIR/custom.conf" ]] || touch "$AUTHDIR/custom.conf"
            sed -i '/^AutomaticLogin/d' "$AUTHDIR/custom.conf"
            sed -i '/^AutomaticLoginEnable/d' "$AUTHDIR/custom.conf"
            cat >> "$AUTHDIR/custom.conf" <<CONF
[daemon]
AutomaticLoginEnable=true
AutomaticLogin=${KIOSK_USER}
CONF
            ;;
    esac
    echo "  Display manager: ${DM} -- autologin configured."
fi

# ── 3. Create the kiosk desktop entry ──────────────────────────────────────
echo ""
echo "[3/5] Creating kiosk autostart desktop entry..."

XDG_AUTOSTART="$HOME/.config/autostart"
mkdir -p "$XDG_AUTOSTART"

cat > "$XDG_AUTOSTART/kiosk-dashboard.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=Dashboard Kiosk
Exec=/home/pi/.kiosk/run.sh
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=Launches Firefox in kiosk mode for the weather dashboard
DESKTOP

# ── 4. Create the kiosk launch script ──────────────────────────────────────
echo ""
echo "[4/5] Creating kiosk launch script..."

KIOSK_DIR="$HOME/.kiosk"
mkdir -p "$KIOSK_DIR"

cat > "$KIOSK_DIR/run.sh" <<SCRIPT
#!/usr/bin/env bash
set -euo pipefail

export DISPLAY=:0

# Wait for X to be ready
for i in \$(seq 1 30); do
    if xdpyinfo &>/dev/null; then
        break
    fi
    sleep 1
done

# Kill any running Xvfb first
pkill -f Xvfb || true

# Start Xvfb virtual display (HDMI or fallback)
Xvfb :0 -screen 0 1920x1080x24 &
XVFB_PID=\$!
sleep 2

# Unclutter removes the mouse cursor when idle
unclutter -idle 0.5 -root &

# Launch Firefox in kiosk mode
firefox --kiosk ${DASH_URL} &
FIREFOX_PID=\$!

# Wait for Firefox to exit
wait \$FIREFOX_PID

# Clean up
kill \$XVFB_PID 2>/dev/null || true
SCRIPT

chmod +x "$KIOSK_DIR/run.sh"

# ── 5. Create the systemd service ──────────────────────────────────────────
echo ""
echo "[5/5] Installing systemd service 'dashboard-kiosk.service'..."

# Determine the real path to the kiosk user's home
KIOSK_HOME=""
if [[ "$KIOSK_USER" == "pi" ]]; then
    KIOSK_HOME="/home/pi"
else
    KIOSK_HOME=$(eval echo "~${KIOSK_USER}")
fi

cat > /etc/systemd/system/dashboard-kiosk.service <<SERVICE
[Unit]
Description=Dashboard Kiosk Service
After=network-online.target multi-user.target
Wants=network-online.target

[Service]
Type=simple
User=${KIOSK_USER}
Group=${KIOSK_USER}
Environment=DISPLAY=:0
Environment=HOME=${KIOSK_HOME}
Restart=on-failure
RestartSec=5

# PreStart: ensure Xvfb is running before our script starts
ExecStartPre=/usr/bin/Xvfb :0 -screen 0 1920x1080x24
ExecStart=${KIOSK_HOME}/.kiosk/run.sh
ExecStop=/bin/kill -TERM \$MAINPID

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable dashboard-kiosk.service

echo ""
echo "==============================="
echo " Installation complete!"
echo "==============================="
echo ""
echo "  Service : dashboard-kiosk.service"
echo "  Status  : systemctl status dashboard-kiosk"
echo "  Logs    : journalctl -u dashboard-kiosk -f"
echo ""
echo "To start immediately:"
echo "  sudo systemctl start dashboard-kiosk"
echo ""
echo "To enable on boot (if not already):"
echo "  sudo systemctl enable dashboard-kiosk"