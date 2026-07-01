# Dashboard Kiosk - Linux

Native Firefox kiosk for Linux with the dashboard backend running in Docker.
Designed for kiosk mode so Firefox starts directly on the host desktop in fullscreen while the FastAPI dashboard backend runs in Docker on the same machine.

On Ubuntu/Debian, the setup installs Firefox from Mozilla's APT repository to avoid the snap-based Ubuntu package.

## Quick Setup

### 1. On Target Machine

```bash
# Clone the repo (if not already)
cd /opt
sudo git clone https://github.com/youruser/dashboard_weather.git
cd dashboard_weather/kiosk

# Run setup script
sudo bash setup-kiosk.sh
```

### 2. After Setup

```bash
# Verify dashboard is running
docker ps | grep dashboard-server
docker logs dashboard-server

# Reboot to apply changes and start kiosk
sudo reboot
```

If automatic graphical login is enabled during setup, the kiosk user is logged in automatically and the dashboard should appear directly after boot.

The setup also creates a dedicated Firefox kiosk profile with first-run, telemetry, and default-browser prompts disabled.
It also installs and starts `unclutter` to hide the mouse cursor after the configured idle timeout.

## How It Works

```
┌──────────────────────────────────────────────┐
│         Linux Machine with HDMI Display      │
│                                              │
│  Login → Docker starts → Native Firefox      │
│                  ↑                          │
│         No login screen shown               │
│         Fullscreen kiosk mode                │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Native Firefox --kiosk               │  │
│  │  • Runs in the logged-in desktop      │  │
│  │  • Fullscreen, no decorations         │  │
│  │  • Avoids container X11 issues        │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  • localhost:8000 → Dashboard app on machine │
│  • network_mode: host → shares network ns    │
│  • privileged: true → framebuffer access     │
└──────────────────────────────────────────────┘
```

## Architecture

| Component | What It Does |
|-----------|-------------|
| Native Firefox | Fullscreen browser on the host desktop |
| main `docker-compose.yml` | Runs the dashboard app |
| `setup-kiosk.sh` | Interactive setup script |
| desktop autostart entry | Starts dashboard and kiosk after graphical login |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_URL` | `http://<host-ip>:8000` | Dashboard app URL |
| `DASHBOARD_HOST` | `<host-ip>` | Host used for startup readiness checks |
| `DASHBOARD_PORT` | `8000` | Port used for startup readiness checks |
| `CURSOR_TIMEOUT` | `5` | Reserved for future cursor handling |

### Key Differences from Regular Mode

| Feature | Current Kiosk Mode | Notes |
|---------|-------------|---------------------|
| Display mode | Native desktop session | No X11 container forwarding |
| Privileged | No | Browser runs on host |
| User | Kiosk user | Auto-login recommended |
| Display manager | Kept running | Required |
| Auto-start | User autostart desktop entry | After graphical login |

### Change Dashboard URL

```bash
# Edit docker-compose.yml
sed -i 's|http://localhost:8000|http://your-machine-ip:8000|' docker-compose.yml

# Restart
docker compose down && docker compose up -d
```

When running the dashboard separately from the kiosk container, prefer the machine IP shown by `hostname -I` instead of `localhost`.

## Troubleshooting

### Dashboard backend won't start

```bash
# Check Docker logs
docker logs dashboard-server
```

### Black screen or no display

1. Verify Firefox autostart entry exists:
   ```bash
   ls -la ~/.config/autostart/dashboard-kiosk.desktop
   ```

2. Test Firefox manually:
   ```bash
   firefox --kiosk http://127.0.0.1:8000
   ```

3. Check desktop session:
   ```bash
   echo "$DISPLAY"
   ps aux | grep -E 'gnome-shell|Xorg|Xwayland|wayland' | grep -v grep
   ```

### Firefox crashes on startup

```bash
# Run Firefox manually to see errors
firefox --kiosk http://localhost:8000
```

### Performance issues (laggy rendering)

1. Ensure GPU memory is allocated (Raspberry Pi):
   ```bash
   # /boot/config.txt
   gpu_mem=256
   ```

2. Reboot:
   ```bash
   sudo reboot
   ```

3. Increase container memory limit in `docker-compose.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         memory: 3G
   ```

### No audio

```bash
# Add audio support to docker-compose.yml
devices:
  - /dev/snd:/dev/snd
```

## Auto-start

The setup script creates a desktop autostart entry in the kiosk user's graphical session.

If older `dashboard-kiosk.service` or `dashboard-app.service` units exist, the setup script removes them automatically.
The default setup does not disable the display manager, because that can leave some systems stuck during boot.

If you already disabled the display manager and the machine no longer boots cleanly, recover from a console or recovery shell and re-enable the correct service, for example:

```bash
sudo systemctl enable --now gdm3
# or: lightdm / sddm / lxdm
```

```bash
# Check autostart entry
ls -la ~/.config/autostart/dashboard-kiosk.desktop
```

## Manual Control

```bash
# Start backend
docker compose -f /path/to/dashboard_weather/docker-compose.yml up -d dashboard

# Launch kiosk manually
firefox --kiosk http://127.0.0.1:8000

# Restart after code changes
docker compose build --no-cache
docker compose -f /path/to/dashboard_weather/docker-compose.yml up -d dashboard
```

## Files

```
kiosk/
├── setup-kiosk.sh          # Interactive setup script
└── README.md               # This file
```

## License

MIT