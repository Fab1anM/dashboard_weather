# Dockerfile for Firefox kiosk on ARM64 (Jetson, Raspberry Pi 4/5)
# Designed for pre-login kiosk mode (starts before desktop login)

FROM ubuntu:24.04

# Avoid interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install Firefox, Xvfb, unclutter, dbus, and other kiosk dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    firefox \
    xvfb \
    unclutter \
    dbus-x11 \
    dbus \
    x11-xserver-utils \
    xauth \
    x11-utils \
    xterm \
    wget \
    ca-certificates \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Set up dbus directory
RUN mkdir -p /run/dbus

# Set Xvfb as the default display
ENV DISPLAY=:99

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set user to root for kiosk mode (needed for pre-login)
USER root

ENTRYPOINT ["/entrypoint.sh"]
CMD ["firefox", "--kiosk", "http://localhost:8000"]