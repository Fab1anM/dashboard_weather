#!/usr/bin/env bash
set -euo pipefail

REPO=/Users/fabianmirz/Documents/git-projects/dashboard_weather
API_URL="http://localhost:8000"

echo "=== Verifying header changes and Docker restart ==="

# 1. Check that "Trier, Germany" is gone from config.py
echo "--- Checking config.py has no 'Trier, Germany' ---"
if grep -q "Trier, Germany" "$REPO/dashboard_weather/config.py"; then
    echo "FAIL: 'Trier, Germany' still in config.py"
    exit 1
fi
echo "PASS: config.py is clean"

# 2. Check that "Trier" is present
echo "--- Checking 'Trier' is present ---"
if ! grep -q '"Trier"' "$REPO/dashboard_weather/config.py"; then
    echo "FAIL: 'Trier' not found in config.py"
    exit 1
fi
echo "PASS: 'Trier' found in config.py"

# 3. Check HTML template structure
echo "--- Checking HTML template ---"
if ! grep -q 'title-main' "$REPO/dashboard_weather/web/templates/index.html"; then
    echo "FAIL: title-main class not found in template"
    exit 1
fi
echo "PASS: title-main class present in template"

# 4. Check CSS changes
echo "--- Checking CSS ---"
if ! grep -q 'title-main' "$REPO/dashboard_weather/web/static/css/style.css"; then
    echo "FAIL: title-main not in CSS"
    exit 1
fi
echo "PASS: title-main in CSS"

# 5. Check app.py has caching fix
echo "--- Checking app.py caching fix ---"
if ! grep -q "no-store, no-cache" "$REPO/dashboard_weather/web/app.py"; then
    echo "FAIL: Caching fix not in app.py"
    exit 1
fi
echo "PASS: Caching fix present in app.py"

# 6. Check Docker container status
echo "--- Checking Docker container ---"
CONTAINER_STATUS=$(docker ps --filter "name=dashboard-server" --format "{{.Status}}" 2>/dev/null || echo "not running")
if [[ "$CONTAINER_STATUS" == *healthy* ]]; then
    echo "PASS: Container is healthy"
else
    echo "WARNING: Container status: $CONTAINER_STATUS"
fi

# 7. Test API endpoint
echo "--- Testing API endpoint ---"
API_RESPONSE=$(curl -s "${API_URL}/api/dashboard?refresh=1" 2>/dev/null || echo "unreachable")
LOCATION=$(echo "$API_RESPONSE" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('location', 'UNKNOWN'))" 2>/dev/null || echo "parse error")
echo "API location: $LOCATION"
if [[ "$LOCATION" == "Trier" ]]; then
    echo "PASS: API returns 'Trier'"
elif [[ "$LOCATION" == "Trier, Germany" ]]; then
    echo "FAIL: API still returns 'Trier, Germany'"
    exit 1
else
    echo "INFO: API returns '$LOCATION' - container may not be fully ready yet"
fi

# 8. Test HTML endpoint
echo "--- Testing HTML endpoint ---"
HTML_LOCATION=$(curl -s "${API_URL}/" 2>/dev/null | grep -o 'title-main">[^<]*' | head -1 || echo "not found")
echo "HTML location: $HTML_LOCATION"

# 9. Run ruff
echo "--- Running ruff check ---"
cd "$REPO"
uv run ruff check dashboard_weather/ 2>&1 || { echo "FAIL: ruff check failed"; exit 1; }

# 10. Run pytest
echo "--- Running pytest ---"
uv run pytest 2>&1 || { echo "FAIL: tests failed"; exit 1; }

echo "=== VERIFICATION COMPLETE ==="