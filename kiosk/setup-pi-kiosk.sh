#!/usr/bin/env bash
#
# setup-pi-kiosk.sh
# Interactive setup for Docker-based Firefox kiosk on Raspberry Pi
# Designed for pre-login kiosk mode (starts before login screen)
#
# Usage:
#   sudo bash setup-pi-kiosk.sh
#
# Prerequisites:
#   - Raspberry Pi with Docker installed
#   - Pi connected to HDMI monitor
#   - Dashboard running on Pi (port 8000)
#

set -euo pipefail

# ── Helper: read a line with a default value ──────────────────────
read_default() {
    local prompt="$1"
    local default="$2"
    local input
    if [[ -n "$default" ]]; then
        read -p "${prompt} [${default}]: " input
        input="${input:-$default}"
    else
        read -p "${prompt}: " input
    fi
    echo "$input"
}

# ── Configuration: prompt the user ────────────────────────────────
echo ""
echo "============================================"
echo " Dashboard Kiosk Setup for Raspberry Pi"
echo "============================================"

KIOSK_USER=$(read_default "   Kiosk username (runs Firefox)" "pi")
DASHBOARD_HOST=$(read_default "   Dashboard hostname/IP" "localhost")
DASHBOARD_PORT=$(read_default "   Dashboard port" "8000")
DASHBOARD_URL="http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
REPO_DIR=$(read_default "   Installation directory" "/opt/dashboard-kiosk")
AUTO_START=$(read_default "   Enable auto-start on boot? (y/n)" "y")
CURSOR_TIMEOUT=$(read_default "   Hide cursor after idle (seconds)" "5")
RESOLUTION=$(read_default "   Display resolution (e.g. 1920x1080x24)" "1920x1080x24")
DISABLE_DISPLAY_MANAGER=$(read_default "   Disable display manager (for pre-login kiosk)? (y/n)" "y")

echo ""
echo "============================================"
echo " Summary"
echo "============================================"
echo " User       : ${KIOSK_USER}"
echo " Dashboard  : ${DASHBOARD_URL}"
echo " Install dir: ${REPO_DIR}"
echo " Cursor hide: ${CURSOR_TIMEOUT}s"
echo " Resolution : ${RESOLUTION}"
echo " Auto-start : ${AUTO_START}"
echo " No-login   : ${DISABLE_DISPLAY_MANAGER}"
echo "============================================"

# ── Step 1: Install Docker (if missing) ───────────────────────────
echo ""
echo "[1/8] Checking Docker installation..."
if ! command -v docker &>/dev/null; then
    echo "  Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "${KIOSK_USER}"
    echo "  Docker installed. Please log out and back in, then re-run."
    exit 0
else
    echo "  Docker is installed"
fi

# ── Step 2: Prepare kiosk directory ───────────────────────────────
echo ""
echo "[2/8] Setting up kiosk directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${REPO_DIR}"
cd "${REPO_DIR}"

# Copy kiosk files from script directory
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    echo "  Copying kiosk files from ${SCRIPT_DIR}..."
    cp "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/docker-compose.yml" \
       "${SCRIPT_DIR}/entrypoint.sh" .
fi

# ── Step 3: Configure docker-compose ──────────────────────────────
echo ""
echo "[3/8] Configuring docker-compose.yml..."

# Update docker-compose with user and URL
sed -i "s|__DASHBOARD_URL__|${DASHBOARD_URL}|g" docker-compose.yml
sed -i "s|__CURSOR_TIMEOUT__|${CURSOR_TIMEOUT}|g" docker-compose.yml
sed -i "s|__RESOLUTION__|${RESOLUTION}|g" docker-compose.yml

# ── Step 4: Build the kiosk image ─────────────────────────────────
echo ""
echo "[4/8] Building kiosk image (this may take a few minutes on Pi)..."
docker compose build --no-cache

# ── Step 5: Start the kiosk container ─────────────────────────────
echo ""
echo "[5/8] Starting kiosk container..."
docker compose up -d

# ── Step 6: Disable display manager (for pre-login kiosk) ─────────
echo ""
echo "[6/8] Configuring display manager..."

if [[ "${DISABLE_DISPLAY_MANAGER,,}" == "y" || "${DISABLE_DISPLAY_MANAGER,,}" == "yes" ]]; then
    echo "  Disabling display manager..."
    
    # Disable lightdm (most common on Raspberry Pi OS)
    if command -v lightdm &>/dev/null; then
        sudo systemctl disable lightdm
        echo "  lightdm disabled"
    fi
    
    # Disable gdm3 (if installed)
    if command -v gdm3 &>/dev/null; then
        sudo systemctl disable gdm3
        echo "  gdm3 disabled"
    fi
    
    # Disable display manager that might be running
    for dm in lightdm gdm3 sddm lxdm; do
        if systemctl is-active --quiet "$dm" 2>/dev/null; then
            echo "  Stopping ${dm}..."
            sudo systemctl stop "$dm"
        fi
    done
    
    # Add kiosk user to video group for framebuffer access
    sudo usermod -aG video "${KIOSK_USER}"
    echo "  Added ${KIOSK_USER} to video group"
else
    echo "  Skipping display manager disable (auto-start will wait for GUI)"
fi

# ── Step 7: Enable on-boot auto-start ─────────────────────────────
echo ""
echo "[7/8] Enabling on-boot auto-start..."
sudo systemctl enable docker
sudo systemctl start docker

if [[ "${AUTO_START,,}" == "y" || "${AUTO_START,,}" == "yes" ]]; then
    cat > /etc/systemd/system/dashboard-kiosk.service <<EOF
[Unit]
Description=Dashboard Kiosk (Docker)
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${REPO_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable dashboard-kiosk.service
    echo "  Auto-start enabled (starts at multi-user.target, before GUI)"
else
    echo "  Skipping auto-start (run 'sudo systemctl enable dashboard-kiosk' later)"
fi

# ── Step 8: Configure GPU memory (for Pi 4/5) ────────────────────
echo ""
echo "[8/8] GPU memory configuration..."

if [[ -f /boot/config.txt ]]; then
    # Check current gpu_mem
    CURRENT_GPU_MEM=$(grep -E "^gpu_mem=" /boot/config.txt | cut -d= -f2 | tr -d '[:space:]')
    if [[ -z "$CURRENT_GPU_MEM" ]]; then
        echo "  Setting gpu_mem=256 (was not configured)"
        echo "gpu_mem=256" >> /boot/config.txt
    elif [[ "$CURRENT_GPU_MEM" -lt 256 ]]; then
        echo "  Updating gpu_mem from ${CURRENT_GPU_MEM} to 256"
        sudo sed -i 's/^gpu_mem=.*/gpu_mem=256/' /boot/config.txt
    else
        echo "  gpu_mem=${CURRENT_GPU_MEM} (already sufficient)"
    fi
    
    echo "  GPU memory configured. Reboot for changes to take effect."
else
    echo "  No /boot/config.txt found (not a Raspberry Pi?)"
fi

echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo " User       : ${KIOSK_USER}"
echo " URL        : ${DASHBOARD_URL}"
echo " Install dir: ${REPO_DIR}"
echo " Resolution : ${RESOLUTION}"
echo ""
echo " To view logs:"
echo "   docker logs -f dashboard-kiosk"
echo ""
echo " To restart:"
echo "   docker compose restart"
echo ""
if [[ "${AUTO_START,,}" == "y" || "${AUTO_START,,}" == "yes" ]]; then
    echo " To disable auto-start:"
    echo "   sudo systemctl disable dashboard-kiosk"
fi
echo ""
echo "============================================"
echo ""
echo " NOTE: Reboot to apply GPU memory changes and start kiosk!"
echo "   sudo reboot"