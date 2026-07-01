# Dashboard Kiosk - Raspberry Pi

Docker-based kiosk for Raspberry Pi with Firefox fullscreen on HDMI display.

## Quick Setup

### 1. On Raspberry Pi

```bash
# Clone the repo (if not already)
cd /opt
sudo git clone https://github.com/youruser/dashboard_weather.git
sudo chown -R pi:pi dashboard_weather
cd dashboard_weather/kiosk

# Run setup script
sudo bash setup-pi-kiosk.sh
```

### 2. After Setup

```bash
# Verify kiosk is running
docker ps | grep kiosk
docker logs dashboard-kiosk

# View dashboard on the monitor
# (It should auto-start fullscreen on the HDMI display)
```

## How It Works

```
┌──────────────────────────────────────────────┐
│         Raspberry Pi with HDMI Display       │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  X Server (Wayland/X11 on Pi)          │  │
│  │  • Renders to HDMI output              │  │
│  └────────────────┬───────────────────────┘  │
│                   │ X11 socket (/tmp/.X11)   │
│  ┌────────────────▼───────────────────────┐  │
│  │  Docker: dashboard-kiosk container     │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  Firefox --kiosk                 │  │  │
│  │  │  • Fullscreen, no decorations    │  │  │
│  │  │  • Auto-restart on crash         │  │  │
│  │  │  • Hidden cursor when idle       │  │  │
│  │  └──────────────────────────────────┘  │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  • localhost:8000 → Dashboard app on Pi      │
│  • network_mode: host → shares network ns    │
│  • Volume mount: X11 socket access           │
└──────────────────────────────────────────────┘
```

## Architecture

| Component | What It Does |
|-----------|-------------|
| `linuxserver/firefox:armv8` | Official Firefox for ARM64 (Pi) |
| `unclutter` | Hides cursor after N seconds idle |
| X11 socket mount | Lets container render to Pi display |
| `network_mode: host` | `localhost` = Pi's IP |
| `docker-compose` | Manages container lifecycle |
| `setup-pi-kiosk.sh` | One-command setup script |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_URL` | `http://localhost:8000` | Dashboard app URL |
| `CURSOR_TIMEOUT` | `5` | Seconds before cursor hides |

### Change Dashboard URL

```bash
# Edit docker-compose.yml
sed -i 's|http://localhost:8000|http://your-pi-ip:8000|' docker-compose.yml

# Restart
docker compose down && docker compose up -d
```

### Change Resolution

Add to `docker-compose.yml` environment:

```yaml
environment:
  - RESOLUTION=1920x1080x24
```

Supported resolutions:
- `1920x1080x24` (1080p)
- `1280x720x24` (720p)
- `2560x1440x24` (1440p - for 4K Pi 4/5)

## Troubleshooting

### Container won't start

```bash
# Check X11 socket is mounted
docker exec kiosk ls -la /tmp/.X11-unix/

# Check Docker logs
docker logs dashboard-kiosk

# Check if Pi's X server is running
systemctl status lightdm  # or gdm3
```

### Black screen or no display

1. Verify X11 socket exists:
   ```bash
   ls -la /tmp/.X11-unix/X0
   ```

2. Check permissions:
   ```bash
   # Ensure Docker can access X11
   sudo chmod 777 /tmp/.X11-unix/X0
   ```

3. Test manually:
   ```bash
   docker run --rm -it \
     -v /tmp/.X11-unix:/tmp/.X11-unix \
     -e DISPLAY=:0 \
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

### Performance issues (laggy rendering)

1. Add GPU memory split in `/boot/config.txt`:
   ```
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

The setup script creates a systemd service. Verify it's enabled:

```bash
# Check status
systemctl is-enabled dashboard-kiosk

# Enable (if not already)
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
├── Dockerfile              # Firefox ARM64 + kiosk tools
├── entrypoint.sh           # Container startup script
├── docker-compose.yml      # Service definition
├── setup-pi-kiosk.sh       # Pi setup script
└── README.md               # This file
```

## License

MIT