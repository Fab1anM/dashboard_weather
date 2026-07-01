#!/usr/bin/env bash
#
# setup-pi-kiosk.sh
# One-command setup for Docker-based Firefox kiosk on Raspberry Pi
#
# Usage:
#   sudo bash setup-pi-kiosk.sh [--url http://localhost:8000]
#
# Prerequisites:
#   - Raspberry Pi with Docker installed
#   - Pi connected to HDMI monitor
#   - Dashboard running on Pi (port 8000)
#

set -euo pipefail

# Configuration
REPO_DIR="${KIOSK_DIR:-/opt/dashboard-kiosk}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000}"

echo "============================================"
echo " Dashboard Kiosk Setup for Raspberry Pi"
echo "============================================"
echo " Target URL : ${DASHBOARD_URL}"
echo " Install dir: ${REPO_DIR}"
echo "============================================"

# Step 1: Install Docker (if missing)
echo ""
echo "[1/6] Checking Docker installation..."
if ! command -v docker &>/dev/null; then
    echo "  Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "${SUDO_USER:-pi}"
    echo "  Docker installed. Please log out and back in, then re-run."
    exit 0
else
    echo "  Docker is installed"
fi

# Step 2: Prepare kiosk directory
# Copy files from this script's directory (where the kiosk/ folder lives)
echo ""
echo "[2/6] Setting up kiosk directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${REPO_DIR}"
cd "${REPO_DIR}"

# Copy kiosk files from script directory (where this script lives in the repo)
if [ ! -f "Dockerfile" ] || [ ! -f "docker-compose.yml" ]; then
    echo "  Copying kiosk files from ${SCRIPT_DIR}..."
    cp "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/docker-compose.yml" \
       "${SCRIPT_DIR}/entrypoint.sh" .
fi

# Step 3: Update docker-compose with correct URL
echo ""
echo "[3/6] Configuring dashboard URL..."
sed -i "s|http://localhost:8000|${DASHBOARD_URL}|g" docker-compose.yml

# Step 4: Build the kiosk image
echo ""
echo "[4/6] Building kiosk image (this may take a few minutes on Pi)..."
docker compose build --no-cache

# Step 5: Start the kiosk container
echo ""
echo "[5/6] Starting kiosk container..."
docker compose up -d

# Step 6: Enable on-boot auto-start
echo ""
echo "[6/6] Enabling auto-start on boot..."
sudo systemctl enable docker
sudo systemctl start docker

# Create a systemd service for the kiosk container
cat > /etc/systemd/system/dashboard-kiosk.service <<EOF
[Unit]
Description=Dashboard Kiosk (Docker)
After=docker.service
Requires=docker.service

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

echo ""
echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo " Kiosk URL : ${DASHBOARD_URL}"
echo " Log files : journalctl -u dashboard-kiosk -f"
echo " Logs      : docker logs -f dashboard-kiosk"
echo ""
echo " To view dashboard:"
echo "   docker logs -f dashboard-kiosk"
echo ""
echo " To restart:"
echo "   sudo systemctl restart dashboard-kiosk"
echo ""
echo " To disable auto-start:"
echo "   sudo systemctl disable dashboard-kiosk"
echo ""
echo "============================================"