#!/usr/bin/env bash
#
# setup-kiosk.sh
# Interactive setup for Docker-based Firefox kiosk on any Linux machine
# Designed for pre-login kiosk mode (starts before login screen)
#
# Usage:
#   sudo bash setup-kiosk.sh
#
# This script detects the OS/distro and configures accordingly.
# No assumptions about Raspberry Pi or any specific hardware.
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
echo " Dashboard Kiosk Setup"
echo "============================================"

KIOSK_USER=$(read_default "   Kiosk username (runs Firefox)" "kiosk")
DASHBOARD_HOST=$(read_default "   Dashboard hostname/IP" "localhost")
DASHBOARD_PORT=$(read_default "   Dashboard port" "8000")
DASHBOARD_URL="http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
REPO_DIR=$(read_default "   Installation directory" "/opt/dashboard-kiosk")
AUTO_START=$(read_default "   Enable auto-start on boot? (y/n)" "y")
CURSOR_TIMEOUT=$(read_default "   Hide cursor after idle (seconds)" "5")
RESOLUTION=$(read_default "   Display resolution (e.g. 1920x1080x24)" "1920x1080x24")
DISABLE_DISPLAY_MANAGER=$(read_default "   Disable display manager (for pre-login kiosk)? (y/n)" "y")
DISPLAY_MODE=$(read_default "   Display mode: xvfb (virtual), host (existing X11)" "xvfb")

echo ""
echo "============================================"
echo " Summary"
echo "============================================"
echo " User       : ${KIOSK_USER}"
echo " Dashboard  : ${DASHBOARD_URL}"
echo " Install dir: ${REPO_DIR}"
echo " Cursor hide: ${CURSOR_TIMEOUT}s"
echo " Resolution : ${RESOLUTION}"
echo " Display    : ${DISPLAY_MODE}"
echo " Auto-start : ${AUTO_START}"
echo " No-login   : ${DISABLE_DISPLAY_MANAGER}"
echo "============================================"

# ── Step 0: Detect OS/distro ──────────────────────────────────────
echo ""
echo "[0/8] Detecting OS/distro..."

if [[ -f /etc/os-release ]]; then
    source /etc/os-release
    DISTRO_ID="$ID"
    DISTRO_VERSION="$VERSION_ID"
    DISTRO_PRETTY_NAME="$PRETTY_NAME"
else
    DISTRO_ID="unknown"
    DISTRO_VERSION="unknown"
    DISTRO_PRETTY_NAME="Unknown"
fi

DISTRO_ARCH=$(uname -m)

echo "  OS: ${DISTRO_PRETTY_NAME} (${DISTRO_ID} ${DISTRO_VERSION})"
echo "  Arch: ${DISTRO_ARCH}"

# ── Step 1: Install Docker (if missing) ───────────────────────────
echo ""
echo "[1/8] Checking Docker installation..."
if ! command -v docker &>/dev/null; then
    echo "  Docker not found. Installing..."
    
    case "$DISTRO_ID" in
        ubuntu|debian)
            apt-get update
            apt-get install -y ca-certificates curl gnupg
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io
            ;;
        fedora|centos|rhel)
            dnf install -y dnf-plugins-core
            dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
            dnf install -y docker-ce docker-ce-cli containerd.io
            ;;
        arch)
            pacman -S --noconfirm docker
            ;;
        *)
            echo "  Unsupported distro for Docker install. Please install Docker manually first."
            echo "  https://docs.docker.com/engine/install/"
            exit 1
            ;;
    esac
    
    sudo usermod -aG docker "${KIOSK_USER}" 2>/dev/null || true
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

# Always copy kiosk files from script directory (fresh copy every time)
echo "  Copying kiosk files from ${SCRIPT_DIR}..."
cp -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/docker-compose.yml" \
   "${SCRIPT_DIR}/entrypoint.sh" .

# ── Step 3: Configure docker-compose ──────────────────────────────
echo ""
echo "[3/8] Configuring docker-compose.yml..."

# Update docker-compose with user and URL
sed -i "s|__DASHBOARD_URL__|${DASHBOARD_URL}|g" docker-compose.yml
sed -i "s|__CURSOR_TIMEOUT__|${CURSOR_TIMEOUT}|g" docker-compose.yml
sed -i "s|__RESOLUTION__|${RESOLUTION}|g" docker-compose.yml

# ── Step 4: Build the kiosk image ─────────────────────────────────
echo ""
echo "[4/8] Building kiosk image (this may take a few minutes)..."
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
    
    # Detect and disable common display managers
    for dm in lightdm gdm3 sddm lxdm mdm xdm; do
        if systemctl is-active --quiet "$dm" 2>/dev/null; then
            echo "  Stopping and disabling ${dm}..."
            sudo systemctl stop "$dm"
            sudo systemctl disable "$dm"
        fi
    done
    
    # Add kiosk user to relevant groups for display access
    sudo usermod -aG video "${KIOSK_USER}" 2>/dev/null || true
    sudo usermod -aG input "${KIOSK_USER}" 2>/dev/null || true
    echo "  Added ${KIOSK_USER} to video/input groups"
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

# ── Step 8: GPU memory configuration (if applicable) ──────────────
echo ""
echo "[8/8] Checking GPU configuration..."

GPU_CONFIGURED=false

# Check for Raspberry Pi specific config
if [[ -f /boot/config.txt ]]; then
    CURRENT_GPU_MEM=$(grep -E "^gpu_mem=" /boot/config.txt | cut -d= -f2 | tr -d '[:space:]')
    if [[ -z "$CURRENT_GPU_MEM" ]]; then
        echo "  Setting gpu_mem=256 (was not configured)"
        echo "gpu_mem=256" >> /boot/config.txt
        GPU_CONFIGURED=true
    elif [[ "$CURRENT_GPU_MEM" -lt 256 ]]; then
        echo "  Updating gpu_mem from ${CURRENT_GPU_MEM} to 256"
        sudo sed -i 's/^gpu_mem=.*/gpu_mem=256/' /boot/config.txt
        GPU_CONFIGURED=true
    else
        echo "  gpu_mem=${CURRENT_GPU_MEM} (already sufficient)"
    fi
fi

# Check for NVIDIA GPU
if command -v nvidia-smi &>/dev/null; then
    echo "  NVIDIA GPU detected. Ensure adequate memory allocation."
    echo "  No config changes needed for NVIDIA."
elif [[ -f /sys/class/drm/card0/device/gpu_mem ]]; then
    echo "  Generic GPU detected. Memory configured via container limits."
fi

if [[ "$GPU_CONFIGURED" == "true" ]]; then
    echo "  GPU memory configured. Reboot for changes to take effect."
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
if [[ "$GPU_CONFIGURED" == "true" ]]; then
    echo " NOTE: Reboot to apply GPU memory changes and start kiosk!"
    echo "   sudo reboot"
else
    echo " Run 'sudo shutdown -r now' to reboot and start the kiosk!"
fi