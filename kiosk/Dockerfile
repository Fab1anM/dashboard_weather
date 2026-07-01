# Dockerfile for Firefox kiosk on ARM64 (Jetson, Raspberry Pi 4/5)
# Designed for pre-login kiosk mode (starts before desktop login)

FROM ubuntu:24.04

# Avoid interactive prompts during install
ENV DEBIAN_FRONTEND=noninteractive

# Install Firefox from Mozilla APT repo, plus kiosk dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    && install -d -m 0755 /etc/apt/keyrings \
    && curl -fsSL https://packages.mozilla.org/apt/repo-signing-key.gpg | gpg --dearmor -o /etc/apt/keyrings/packages.mozilla.org.gpg \
    && chmod 644 /etc/apt/keyrings/packages.mozilla.org.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/packages.mozilla.org.gpg] https://packages.mozilla.org/apt mozilla main" > /etc/apt/sources.list.d/mozilla.list \
    && printf 'Package: *\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n' > /etc/apt/preferences.d/mozilla \
    && apt-get update && apt-get install -y --no-install-recommends \
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