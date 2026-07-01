# Dockerfile for Firefox kiosk on Raspberry Pi (ARM64/aarch64)
# Designed for pre-login kiosk mode (starts before desktop login)

FROM linuxserver/firefox:armv8-latest

USER root

# Install kiosk dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    unclutter \
    dbus-x11 \
    x11-utils \
    xauth \
    xvfb \
    x11vnc \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create kiosk entrypoint
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Default: start in kiosk mode
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]