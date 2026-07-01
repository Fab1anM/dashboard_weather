# Dashboard Kiosk - Linux

Docker-based kiosk for Linux with Firefox fullscreen on HDMI display.
Designed for kiosk mode so Firefox starts automatically on the real host display and opens the dashboard in fullscreen. The setup starts both the dashboard app and the kiosk on the same machine through the user's graphical session.

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
# Verify dashboard and kiosk are running
docker ps | grep dashboard-server
docker ps | grep kiosk
docker logs dashboard-server
docker logs dashboard-kiosk

# Reboot to apply changes and start kiosk
sudo reboot
```

## How It Works

```
┌──────────────────────────────────────────────┐
│         Linux Machine with HDMI Display      │
│                                              │
│  Login → Docker starts → Firefox on :0       │
│                  ↑                          │
│         No login screen shown               │
│         Fullscreen kiosk mode                │
│                                              │
│  ┌────────────────▼───────────────────────┐  │
│  │  Docker: dashboard-kiosk container     │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  Firefox --kiosk                 │  │  │
│  │  │  • Uses host X display           │  │  │
│  │  │  • Fullscreen, no decorations    │  │  │
│  │  │  • Auto-restart on crash         │  │  │
│  │  │  • Hidden cursor when idle       │  │  │
│  │  └──────────────────────────────────┘  │  │
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
| Mozilla APT Firefox | Real Firefox binary inside the container |
| `unclutter` | Hides cursor after N seconds idle |
| host X11 display | Real physical display used by Firefox |
| privileged mode | Access to /dev/fb0 and framebuffer |
| `network_mode: host` | `localhost` = machine's IP |
| main `docker-compose.yml` | Runs the dashboard app |
| kiosk `docker-compose.yml` | Runs the kiosk browser |
| `setup-kiosk.sh` | Interactive setup script |
| `dashboard-app.service` | systemd service for dashboard auto-start |
| `dashboard-kiosk.service` | systemd service for kiosk auto-start |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_URL` | `http://<host-ip>:8000` | Dashboard app URL |
| `DASHBOARD_HOST` | `<host-ip>` | Host used for startup readiness checks |
| `DASHBOARD_PORT` | `8000` | Port used for startup readiness checks |
| `CURSOR_TIMEOUT` | `5` | Seconds before cursor hides |
| `MODE` | `host` | Display mode: `host` |
| `RESOLUTION` | `1920x1080x24` | Xvfb resolution |
| `FIREFOX_ARGS` | `--kiosk --private-window` | Firefox launch flags for fullscreen kiosk |

### Key Differences from Regular Mode

| Feature | Regular Mode | Pre-Login Kiosk Mode |
|---------|-------------|---------------------|
| Display mode | `host` (uses existing X server) | `xvfb` (creates Xvfb) |
| Privileged | No | Yes |
| User | Kiosk user | Root |
| Display manager | Kept running | Optional, not recommended by default |
| Auto-start | At GUI login | User autostart desktop entry |

### Change Dashboard URL

```bash
# Edit docker-compose.yml
sed -i 's|http://localhost:8000|http://your-machine-ip:8000|' docker-compose.yml

# Restart
docker compose down && docker compose up -d
```

When running the dashboard separately from the kiosk container, prefer the machine IP shown by `hostname -I` instead of `localhost`.

### Change Resolution

```bash
# Edit docker-compose.yml
RESOLUTION=2560x1440x24
```

## Troubleshooting

### Container won't start

```bash
# Check X11 socket is mounted
docker exec kiosk ls -la /tmp/.X11-unix/

# Check Docker logs
docker logs dashboard-kiosk

# Check if Xvfb is running
docker exec kiosk ps aux | grep Xvfb
```

### Black screen or no display

1. Verify X11 socket exists:
   ```bash
   ls -la /tmp/.X11-unix/X99
   ```

2. Check permissions:
   ```bash
   # Ensure Docker can access X11
   sudo chmod 777 /tmp/.X11-unix/X99
   ```

3. Test manually:
   ```bash
   docker run --rm -it \
     -v /tmp/.X11-unix:/tmp/.X11-unix \
     -e DISPLAY=:99 \
     linuxserver/firefox:armv8-latest \
     firefox --version
   ```

### Firefox crashes on startup

```bash
# Enter container shell
docker exec -it dashboard-kiosk bash

# Run Firefox manually to see errors
firefox --kiosk http://localhost:8000
```

The image installs Firefox from Mozilla's APT repository because Ubuntu's default `firefox` package is a snap launcher and does not work inside this container.

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

## Auto-start on Boot

The setup script creates a desktop autostart entry in the kiosk user's graphical session.

The container now waits until the dashboard server is reachable before launching Firefox, which avoids a blank or error page during boot.
If an older `dashboard-kiosk.service` already exists, the setup script stops, disables, removes, and recreates it automatically.
If an older `dashboard-app.service` already exists, the setup script also recreates it automatically.
The default setup does not disable the display manager, because that can leave some systems stuck during boot.
The setup script now aborts if unresolved placeholders remain in the generated kiosk `docker-compose.yml`.

If you already disabled the display manager and the machine no longer boots cleanly, recover from a console or recovery shell and re-enable the correct service, for example:

```bash
sudo systemctl enable --now gdm3
# or: lightdm / sddm / lxdm
```

```bash
# Check status
systemctl is-enabled dashboard-app
systemctl is-enabled dashboard-kiosk

# Enable (if not already)
sudo systemctl enable dashboard-app
sudo systemctl enable dashboard-kiosk

# Check it starts on next reboot
sudo shutdown -r now
```

## Manual Control

```bash
# Stop the kiosk
docker compose down

# Start fresh
docker compose up -d

# View logs
docker logs -f dashboard-kiosk

# Enter container (debug)
docker exec -it dashboard-kiosk bash

# Restart after code changes
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Files

```
kiosk/
├── Dockerfile              # Firefox + kiosk tools
├── entrypoint.sh           # Container startup script
├── docker-compose.yml      # Service definition
├── setup-kiosk.sh          # Interactive setup script
└── README.md               # This file
```

## License

MIT