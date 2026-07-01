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

if [[ ! -t 0 && ! -e /dev/tty ]]; then
    echo "Error: interactive terminal required for setup." >&2
    exit 1
fi

exec 3</dev/tty

detect_default_dashboard_host() {
    local candidate
    candidate=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [[ -n "$candidate" ]]; then
        echo "$candidate"
        return 0
    fi

    candidate=$(ip route get 1.1.1.1 2>/dev/null | awk '/src/ {for (i = 1; i <= NF; i++) if ($i == "src") {print $(i + 1); exit}}')
    if [[ -n "$candidate" ]]; then
        echo "$candidate"
        return 0
    fi

    echo "localhost"
}

# ── Helper: read a line with a default value ──────────────────────
read_default() {
    local prompt="$1"
    local default="$2"
    local __resultvar="$3"
    local input
    printf '%s\n' " Prompting: ${prompt}" >&2
    if [[ -n "$default" ]]; then
        read -r -u 3 -p "${prompt} [${default}]: " input
        input="${input:-$default}"
    else
        read -r -u 3 -p "${prompt}: " input
    fi
    printf -v "$__resultvar" '%s' "$input"
    printf '%s\n' " Selected: ${__resultvar}=${input}" >&2
}

# ── Helper: detect the current display resolution ─────────────────
detect_resolution() {
    local best_resolution=""
    
    # Try xdpyinfo first (needs an active X display)
    if command -v xdpyinfo &>/dev/null; then
        for d in $(ls /tmp/.X11-unix/ 2>/dev/null | tr -d 'X'); do
            local result
            result=$(DISPLAY=:"$d" xdpyinfo 2>/dev/null | grep -oP 'dimensions:\s+\K[\d]+x[\d]+')
            if [[ -n "$result" ]]; then
                local w h
                w=$(echo "$result" | cut -dx -f1)
                h=$(echo "$result" | cut -dx -f2)
                echo "${w}x${h}x24"
                return 0
            fi
        done
    fi
    
    # Try xrandr (also needs DISPLAY)
    if command -v xrandr &>/dev/null; then
        local result
        result=$(xrandr 2>/dev/null | grep -oP '\S+ connected\s+\K[\d]+x[\d]+')
        if [[ -n "$result" ]]; then
            echo "${result}x24"
            return 0
        fi
    fi
    
    # Try EDID from DRM kernel interfaces (works without X server)
    for edid_file in /sys/class/drm/*/edid; do
        if [[ -f "$edid_file" ]]; then
            local result
            result=$(edid-decode "$edid_file" 2>/dev/null | grep -oP 'default\s+active\s+mode\s+:\s+\K[\d]+x[\d]+@' | head -1 | sed 's/@.*//')
            if [[ -n "$result" ]]; then
                echo "${result}x24"
                return 0
            fi
            # Fallback: try to parse preferred mode from edid-decode
            local w h
            w=$(edid-decode "$edid_file" 2>/dev/null | grep -oP 'preferred\s+mode:\s+[\d]+' | head -1 | grep -oP '[\d]+$')
            h=$(edid-decode "$edid_file" 2>/dev/null | grep -oP 'preferred\s+mode:\s+[\d]+x[\d]+' | grep -oP 'x[\d]+$' | tr -d 'x')
            if [[ -n "$w" && -n "$h" ]]; then
                echo "${w}x${h}x24"
                return 0
            fi
        fi
    done
    
    # Final fallback
    echo "1920x1080x24"
    return 1
}
# ── Configuration: prompt the user ────────────────────────────────
echo ""
echo "============================================"
echo " Dashboard Kiosk Setup"
echo "============================================"

KIOSK_USER="${KIOSK_USER:-$SUDO_USER}"
echo " Using kiosk user: ${KIOSK_USER}"
DEFAULT_DASHBOARD_HOST="$(detect_default_dashboard_host)"
echo " Suggested dashboard host: ${DEFAULT_DASHBOARD_HOST}"
read_default "   Dashboard hostname/IP" "$DEFAULT_DASHBOARD_HOST" DASHBOARD_HOST
read_default "   Dashboard port" "8000" DASHBOARD_PORT
DASHBOARD_URL="http://${DASHBOARD_HOST}:${DASHBOARD_PORT}"
read_default "   Installation directory" "/opt/dashboard-kiosk" REPO_DIR
read_default "   Dashboard app directory" "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)" DASHBOARD_APP_DIR
read_default "   Enable automatic graphical login for kiosk user? (y/n)" "y" AUTO_LOGIN
read_default "   Enable auto-start on boot? (y/n)" "y" AUTO_START
read_default "   Hide cursor after idle (seconds)" "5" CURSOR_TIMEOUT

# Auto-detect resolution for the prompt default
echo " Detecting screen resolution..."
DETECTED_RESOLUTION="$(detect_resolution 2>/dev/null || true)"
if [[ -z "$DETECTED_RESOLUTION" ]]; then
    DETECTED_RESOLUTION="1920x1080x24"
    echo " Resolution detection fallback: ${DETECTED_RESOLUTION}"
fi
echo " Detected screen resolution: ${DETECTED_RESOLUTION}"
if [[ -n "$DETECTED_RESOLUTION" ]]; then
    read_default "   Display resolution (auto-detected: ${DETECTED_RESOLUTION})" "$DETECTED_RESOLUTION" RESOLUTION
else
    read_default "   Display resolution (e.g. 1920x1080x24)" "1920x1080x24" RESOLUTION
fi

echo ""
echo "============================================"
echo " Summary"
echo "============================================"
echo " User       : ${KIOSK_USER}"
echo " Dashboard  : ${DASHBOARD_URL}"
echo " App dir    : ${DASHBOARD_APP_DIR}"
echo " Auto-login : ${AUTO_LOGIN}"
echo " Install dir: ${REPO_DIR}"
echo " Cursor hide: ${CURSOR_TIMEOUT}s"
echo " Resolution : ${RESOLUTION}"
echo " Auto-start : ${AUTO_START}"
echo " Display    : host X11 (runtime detected)"
echo "============================================"

# ── Step 0: Detect OS/distro ──────────────────────────────────────
echo ""
echo "[0/7] Detecting OS/distro..."

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
echo "[1/7] Checking Docker installation..."
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
echo "[2/7] Setting up kiosk directory..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "${REPO_DIR}"
cd "${REPO_DIR}"

# Always copy kiosk files from script directory (fresh copy every time)
echo "  Copying kiosk files from ${SCRIPT_DIR}..."
cp -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}/docker-compose.yml" \
    "${SCRIPT_DIR}/entrypoint.sh" "${SCRIPT_DIR}/launch-kiosk.sh" .
chmod +x ./entrypoint.sh ./launch-kiosk.sh

if [[ ! -f "${DASHBOARD_APP_DIR}/docker-compose.yml" ]]; then
    echo "  Dashboard compose file not found in ${DASHBOARD_APP_DIR}"
    exit 1
fi

# ── Step 3: Configure docker-compose ──────────────────────────────
echo ""
echo "[3/7] Configuring docker-compose.yml..."

# Update docker-compose with user and URL
sed -i "s|__DASHBOARD_URL__|${DASHBOARD_URL}|g" docker-compose.yml
sed -i "s|__DASHBOARD_HOST__|${DASHBOARD_HOST}|g" docker-compose.yml
sed -i "s|__DASHBOARD_PORT__|${DASHBOARD_PORT}|g" docker-compose.yml
sed -i "s|__CURSOR_TIMEOUT__|${CURSOR_TIMEOUT}|g" docker-compose.yml
sed -i "s|__RESOLUTION__|${RESOLUTION}|g" docker-compose.yml

if grep -q '__[A-Z0-9_][A-Z0-9_]*__' docker-compose.yml; then
    echo "  Error: unresolved placeholders remain in ${REPO_DIR}/docker-compose.yml"
    grep '__[A-Z0-9_][A-Z0-9_]*__' docker-compose.yml || true
    exit 1
fi

# ── Step 4: Start the dashboard service ───────────────────────────
echo ""
echo "[4/7] Starting dashboard service..."
docker compose -f "${DASHBOARD_APP_DIR}/docker-compose.yml" up -d dashboard

# ── Step 5: Start the kiosk container ─────────────────────────────
echo ""
echo "[5/7] Starting kiosk container..."
docker compose up -d --force-recreate --pull always

# ── Step 6: Configure graphical login ─────────────────────────────
echo ""
echo "[6/7] Configuring graphical login..."
echo "  Keeping display manager enabled"
sudo usermod -aG video "${KIOSK_USER}" 2>/dev/null || true
sudo usermod -aG input "${KIOSK_USER}" 2>/dev/null || true
echo "  Added ${KIOSK_USER} to video/input groups"

if [[ "${AUTO_LOGIN,,}" == "y" || "${AUTO_LOGIN,,}" == "yes" ]]; then
    echo "  Configuring GDM automatic login for ${KIOSK_USER}..."
    sudo mkdir -p /etc/gdm3
    sudo tee /etc/gdm3/custom.conf >/dev/null <<EOF
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=${KIOSK_USER}

[security]

[xdmcp]

[chooser]

[debug]
# Uncomment the line below to turn on debugging
#Enable=true
EOF
else
    echo "  Skipping automatic graphical login configuration"
fi

# ── Step 7: Enable graphical session auto-start ───────────────────
echo ""
echo "[7/7] Enabling graphical session auto-start..."
sudo systemctl enable docker
sudo systemctl start docker

if systemctl list-unit-files | grep -q '^dashboard-app\.service'; then
    echo "  Removing old dashboard-app.service boot unit..."
    sudo systemctl stop dashboard-app.service 2>/dev/null || true
    sudo systemctl disable dashboard-app.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/dashboard-app.service
    sudo systemctl daemon-reload
fi

if systemctl list-unit-files | grep -q '^dashboard-kiosk\.service'; then
    echo "  Removing old dashboard-kiosk.service boot unit..."
    sudo systemctl stop dashboard-kiosk.service 2>/dev/null || true
    sudo systemctl disable dashboard-kiosk.service 2>/dev/null || true
    sudo rm -f /etc/systemd/system/dashboard-kiosk.service
    sudo systemctl daemon-reload
fi

if [[ "${AUTO_START,,}" == "y" || "${AUTO_START,,}" == "yes" ]]; then
    sudo mkdir -p "/home/${KIOSK_USER}/.config/autostart"
    cat > "/home/${KIOSK_USER}/.config/autostart/dashboard-kiosk.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Dashboard Kiosk
Exec=${REPO_DIR}/launch-kiosk.sh ${REPO_DIR}/docker-compose.yml ${DASHBOARD_APP_DIR}/docker-compose.yml ${DASHBOARD_URL}
X-GNOME-Autostart-enabled=true
Terminal=false
EOF
    sudo chown -R "${KIOSK_USER}:${KIOSK_USER}" "/home/${KIOSK_USER}/.config"
    echo "  Graphical session autostart enabled for dashboard app and kiosk"
else
    rm -f "/home/${KIOSK_USER}/.config/autostart/dashboard-kiosk.desktop"
    echo "  Skipping auto-start"
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
echo " App dir    : ${DASHBOARD_APP_DIR}"
echo " Install dir: ${REPO_DIR}"
echo " Resolution : ${RESOLUTION}"
echo ""
echo " To view logs:"
echo "   docker logs -f dashboard-kiosk"
echo "   tail -f /home/${KIOSK_USER}/.cache/dashboard-kiosk-launch.log"
echo ""
echo " To restart:"
echo "   docker compose restart"
echo ""
if [[ "${AUTO_START,,}" == "y" || "${AUTO_START,,}" == "yes" ]]; then
    echo " To disable auto-start:"
    echo "   rm -f /home/${KIOSK_USER}/.config/autostart/dashboard-kiosk.desktop"
fi
echo ""
echo " If the graphical login stops working, re-enable GDM manually:"
echo "   sudo systemctl enable --now gdm3"
echo "   # or lightdm / sddm depending on the system"
echo ""
echo "============================================"
echo ""
if [[ "$GPU_CONFIGURED" == "true" ]]; then
    echo " NOTE: Reboot to apply GPU memory changes and start kiosk!"
    echo "   sudo reboot"
else
    echo " Run 'sudo shutdown -r now' to reboot and start the kiosk!"
fi