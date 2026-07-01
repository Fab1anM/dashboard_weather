#!/bin/bash
set -euo pipefail

REPO="/Users/fabianmirz/Documents/git-projects/dashboard_weather"
cd "$REPO"

echo "=== Forcing Docker rebuild with invalidation ==="

# Step 1: Down container
echo "Stopping container..."
docker compose down dashboard 2>&1

# Step 2: Remove all Docker images for this project
echo "Removing all dashboard images..."
docker rmi $(docker images --filter "reference=dashboard_weather-dashboard" -q) 2>/dev/null || true

# Step 3: Force cache invalidation by modifying Dockerfile ARG
# Add a BUILD_DATE timestamp to force cache bust
BUILD_DATE=$(date +%s)
echo "Using build date: $BUILD_DATE"

# Step 4: Build with no cache for all layers
echo "Building with cache disabled..."
docker compose build --no-cache dashboard 2>&1 || {
    echo "Fallback: building with manual no-cache flag..."
    docker build --no-cache -t dashboard_weather-dashboard . 2>&1
}

# Step 5: Start container
echo "Starting container..."
docker compose up -d dashboard 2>&1

# Step 6: Wait for health
echo "Waiting for container to become healthy..."
for i in {1..30}; do
    STATUS=$(docker inspect --format='{{.State.Health.Status}}' dashboard-server 2>/dev/null || echo "not_found")
    if [ "$STATUS" = "healthy" ]; then
        echo "Container is healthy!"
        break
    fi
    if [ "$STATUS" = "not_found" ]; then
        echo "Container not found, waiting..."
        sleep 2
        continue
    fi
    echo "Waiting... ($i/30) - Status: $STATUS"
    sleep 2
done

echo "=== Build complete ==="
echo "Container status: $(docker inspect --format='{{.State.Status}}' dashboard-server 2>/dev/null || echo 'unknown')"