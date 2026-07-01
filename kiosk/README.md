# Dashboard Kiosk - Linux

Docker-based kiosk for Linux with Firefox fullscreen on HDMI display.
Designed for pre-login kiosk mode (starts before login screen, fullscreen).

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
# Verify kiosk is running
docker ps | grep kiosk
docker logs dashboard-kiosk

# Reboot to apply changes and start kiosk
sudo reboot
```

## How It Works

```
┌──────────────────────────────────────────────┐
│         Linux Machine with HDMI Display      │
│                                              │
│  Boot → Docker starts → Xvfb → Firefox       │
│                  ↑                          │
│         No login screen shown               │
│         Fullscreen kiosk mode                │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Xvfb Virtual Display (:99)            │  │
│  │  • Creates virtual X11 display         │  │
│  │  • Renders to framebuffer              │  │
│  └────────────────┬───────────────────────┘  │
│                   │                           │
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
│  • localhost:8000 → Dashboard app on machine │
│  • network_mode: host → shares network ns    │
│  • privileged: true → framebuffer access     │
└──────────────────────────────────────────────┘
```

## Architecture

| Component | What It Does |
|-----------|-------------|
| `linuxserver/firefox:armv8` | Firefox for ARM64 (Linux) |
| `unclutter` | Hides cursor after N seconds idle |
| `xvfb` | Virtual X11 display (pre-login kiosk) |
| privileged mode | Access to /dev/fb0 and framebuffer |
| `network_mode: host` | `localhost` = machine's IP |
| `docker-compose` | Manages container lifecycle |
| `setup-kiosk.sh` | Interactive setup script |
| `dashboard-kiosk.service` | systemd service for auto-start |

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DASHBOARD_URL` | `http://localhost:8000` | Dashboard app URL |
| `CURSOR_TIMEOUT` | `5` | Seconds before cursor hides |
| `MODE` | `xvfb` | Display mode: `xvfb` (recommended) |
| `RESOLUTION` | `1920x1080x24` | Xvfb resolution |

### Key Differences from Regular Mode

| Feature | Regular Mode | Pre-Login Kiosk Mode |
|---------|-------------|---------------------|
| Display mode | `host` (uses existing X server) | `xvfb` (creates Xvfb) |
| Privileged | No | Yes |
| User | Kiosk user | Root |
| Display manager | Kept running | Disabled |
| Auto-start | At GUI login | At multi-user.target |

### Change Dashboard URL

```bash
# Edit docker-compose.yml
sed -i 's|http://localhost:8000|http://your-machine-ip:8000|' docker-compose.yml

# Restart
docker compose down && docker compose up -d
```

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

The setup script creates a systemd service that starts at `multi-user.target` (before GUI login).

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
├── Dockerfile              # Firefox + kiosk tools
├── entrypoint.sh           # Container startup script
├── docker-compose.yml      # Service definition
├── setup-kiosk.sh          # Interactive setup script
└── README.md               # This file
```

## License

MIT