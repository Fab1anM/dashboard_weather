"""Client for the Hochwasservorhersagezentrale Rheinland-Pfalz (hochwasser.rlp.de).

Fetches current water level and flow data for the Mosel at Trier.
Provides measurements and probabilistic forecasts (p10-p90).

Uses the REST API when available, with a requests fallback for when
the httpx client cannot reach the API (e.g. Docker network issues),
and a BeautifulSoup HTML fallback for when both HTTP methods fail.
"""

import contextlib
import logging

import httpx
import requests  # type: ignore[import-untyped]
from bs4 import BeautifulSoup

from dashboard_weather.config import Settings
from dashboard_weather.models import (
    MoselStageData,
    MoselStageForecast,
    MoselStageMeasurement,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.hochwasser.rlp.de/api/v1"

# Pegel Trier / Mosel
MEASUREMENT_SITE_ID = "26500100"

# Fallback page for parsing when the API is unreachable
DETAIL_PAGE_URL = "https://www.hochwasser.rlp.de/flussgebiet/mosel/trier"


class MoselStageClient:
    """Fetches water level and flow data from the RLP flood forecasting center API."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(self) -> MoselStageData | None:
        """Fetch current water level and forecast for Mosel Trier.

        Returns:
            MoselStageData with measurements and forecasts, or None on failure.
        """
        # Try the REST API first
        url = f"{BASE_URL}/measurement-site/{MEASUREMENT_SITE_ID}"

        try:
            resp = await self._client.get(url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            logger.warning("Mosel stage httpx API unavailable, trying requests fallback: %s", exc)
            data = self._fetch_with_requests(url)
            if data is not None:
                return self._parse_response(data)

            logger.warning("Mosel stage requests API also unavailable, falling back to HTML")
            return await self._fetch_from_html()

        return self._parse_response(data)

    @staticmethod
    def _fetch_with_requests(url: str) -> dict | None:
        """Synchronous requests fallback for when httpx cannot reach the API.

        Useful when the async httpx client has DNS/network issues but the
        synchronous requests library succeeds (e.g. different network stack).
        """
        try:
            resp = requests.get(url, timeout=15.0)  # type: ignore[no-untyped-call]
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.warning("Mosel stage requests fallback also failed: %s", exc)
            return None

    async def _fetch_from_html(self) -> MoselStageData | None:
        """Fallback: parse the Mosel Trier detail page for current water level.

        The API may be unreachable from Docker, so we scrape the detail page
        which displays "Letzter Messwert" (last measurement) and other info.
        """
        try:
            resp = await self._client.get(DETAIL_PAGE_URL, timeout=15.0)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Mosel stage HTML fallback also failed: %s", exc)
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        return self._parse_html(soup)

    @staticmethod
    def _parse_html(soup: BeautifulSoup) -> MoselStageData | None:
        """Parse the detail page for current water level and timestamp.

        Expected structure on the page:
          - "Letzter Messwert: <strong>XXX</strong>" (value in cm)
          - "Vorhersage der HVZ Rheinland-Pfalz vom <strong>...</strong>"
          - "Nächste Aktualisierung planmäßig am <strong>...</strong>"
          - A hint paragraph about Stauregulierung
        """
        # Extract current water level from "Letzter Messwert" line
        current_stage_m = None
        timestamp = None

        for p in soup.find_all("p"):
            text = p.get_text(separator="\n", strip=True)
            if "Letzter Messwert:" in text:
                # Extract the numeric value from the strong tag
                strong = p.find("strong")
                if strong:
                    value_str = strong.get_text(strip=True)
                    with contextlib.suppress(ValueError):
                        current_stage_m = float(value_str) / 100.0

            if "Vorhersage der HVZ Rheinland-Pfalz vom" in text:
                strong = p.find("strong")
                if strong:
                    timestamp = strong.get_text(strip=True)

            if "Hinweis zur Hochwassersituation" in text:
                pass  # Skip the link text itself

        # Extract Stauregulierung hint from the first paragraph after the heading
        hint_text = ""
        main = soup.find("main")
        if main:
            # Look for the hint paragraph that mentions Stauregulierung
            for p in main.find_all("p"):
                text = p.get_text(strip=True)
                if "Stauregulierung" in text or "Wasserstand von" in text:
                    hint_text = text
                    break

        if current_stage_m is None:
            return None

        # The HTML fallback gives us the current stage and timestamp only.
        # Build a minimal MoselStageData with what we have.
        # We cannot reliably get forecasts from the page (they are in a chart),
        # so we set an empty forecast list and a "unknown" trend.
        return MoselStageData(
            station="Trier / Mosel",
            current_stage_m=current_stage_m,
            timestamp=timestamp,
            forecast=[],
            trend="gleichbleibend",
            description=hint_text,
        )

    @staticmethod
    def _parse_response(data: dict) -> MoselStageData:
        """Parse the API response into MoselStageData.

        The API returns:
          - W (Wasserstand): water level in cm
          - Q (Abfluss): flow in m³/s
          - hint: contextual information
        """
        # Extract water level data (W = Wasserstand in cm)
        w_data = data.get("W")
        if not w_data or not isinstance(w_data, dict):
            return None

        measurements_raw = w_data.get("measurements", [])
        predictions_raw = w_data.get("predictions", {})

        # Build measurement list from raw data
        measurements: list[MoselStageMeasurement] = []
        for raw in measurements_raw:
            y = raw.get("y")
            if y is None:
                continue
            x = raw.get("x", "")
            measurements.append(
                MoselStageMeasurement(
                    station="Trier / Mosel",
                    stage_m=y / 100.0,  # Convert cm to m
                    timestamp=x,
                )
            )

        # Get last measurement
        last_measurement = measurements[-1] if measurements else None
        current_stage = last_measurement.stage_m if last_measurement else 0.0
        current_timestamp = last_measurement.timestamp if last_measurement else None

        # Parse forecasts
        forecasts: list[MoselStageForecast] = []
        p50 = predictions_raw.get("p50", [])  # Median forecast
        for pred in p50:
            y = pred.get("y")
            x = pred.get("x", "")
            if y is None:
                continue
            hour_str = x  # ISO datetime string
            stage_m = y / 100.0  # Convert cm to m

            # Determine trend from consecutive values
            trend = "gleichbleibend"
            if forecasts:
                prev_stage = forecasts[-1].stage_m
                if stage_m > prev_stage + 0.01:
                    trend = "steigend"
                elif stage_m < prev_stage - 0.01:
                    trend = "fallend"

            forecasts.append(
                MoselStageForecast(
                    hour=hour_str,
                    stage_m=stage_m,
                    trend=trend,
                )
            )

        # Determine overall trend
        trend = "gleichbleibend"
        if len(forecasts) >= 2:
            first = forecasts[0].stage_m
            last_f = forecasts[-1].stage_m
            if last_f > first + 0.01:
                trend = "steigend"
            elif last_f < first - 0.01:
                trend = "fallend"

        # Parse hint text
        hint_data = data.get("hint", {})
        hint_text = ""
        if isinstance(hint_data, dict):
            hint_text = hint_data.get("text", "")

        return MoselStageData(
            station="Trier / Mosel",
            current_stage_m=current_stage,
            timestamp=current_timestamp,
            forecast=forecasts,
            trend=trend,
            description=hint_text,
        )
