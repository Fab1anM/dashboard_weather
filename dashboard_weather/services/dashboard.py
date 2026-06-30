import asyncio
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from dashboard_weather.cache import TTLCache
from dashboard_weather.clients.dipul_news import DipulNewsClient
from dashboard_weather.clients.dipul_wms import DipulWmsClient
from dashboard_weather.clients.hiorg_events import HiOrgEventsClient
from dashboard_weather.clients.laminardata_notam import LaminarNotamClient
from dashboard_weather.clients.open_meteo import OpenMeteoClient
from dashboard_weather.clients.mosel_stage import MoselStageClient
from dashboard_weather.clients.water_portal import WaterPortalClient, WaterQualityAssessment
from dashboard_weather.config import Settings
from dashboard_weather.fallbacks import empty_dashboard
from dashboard_weather.models import DashboardData


class DashboardService:
    CACHE_KEY = "dashboard"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: TTLCache[DashboardData] = TTLCache(settings.cache_ttl_seconds)

        # Check if HiOrg integration is enabled via env var
        self._hiorg_enabled = bool(os.getenv("HIORG_API_URL"))

    async def get_dashboard(self, *, force_refresh: bool = False) -> DashboardData:
        if not force_refresh:
            cached = self._cache.get(self.CACHE_KEY)
            if cached is not None:
                return cached

        data = await self._fetch_dashboard()
        self._cache.set(self.CACHE_KEY, data)
        return data

    async def _fetch_dashboard(self) -> DashboardData:
        errors: list[str] = []
        headers = {"User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"}

        async with httpx.AsyncClient(
            timeout=self._settings.request_timeout_seconds,
            headers=headers,
            follow_redirects=True,
        ) as client:
            weather_client = OpenMeteoClient(self._settings, client)
            news_client = DipulNewsClient(self._settings, client)
            wms_client = DipulWmsClient(self._settings, client)
            water_client = WaterPortalClient(self._settings, client)
            mosel_client = MoselStageClient(self._settings, client)
            hiorg_client = HiOrgEventsClient(self._settings, client)
            notam_client = LaminarNotamClient(self._settings, client)

            # Build gather tasks: NINA disabled (API dead since 2024), hiorg optional
            fetch_tasks: list[Any] = [
                self._safe_fetch_weather(weather_client, errors),
                self._safe_fetch_news(news_client, errors),
                self._safe_fetch_airspace(wms_client, errors),
                self._safe_fetch_notams(notam_client, errors),
                self._safe_fetch_water_quality(water_client, errors),
                self._safe_fetch_mosel_stage(mosel_client, errors),
            ]
            if self._hiorg_enabled:
                fetch_tasks.append(self._safe_fetch_hiorg(hiorg_client, errors))

            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

        # Unpack results into typed variables
        weather_result: Any = results[0]
        dipul_news: Any = results[1]
        airspace: Any = results[2]
        laminar_notams: Any = results[3]
        water_quality: Any = results[4]
        mosel_stage: Any = results[5]

        # Optional hiorg result if enabled
        hiorg_events: Any = results[6] if self._hiorg_enabled else []

        current, daily, hourly, drone = weather_result
        if current is None:
            return empty_dashboard(self._settings, errors)
        if isinstance(dipul_news, Exception):
            errors.append(f"dipul news unavailable: {dipul_news}")
            dipul_news = []
        if isinstance(airspace, Exception):
            errors.append(f"dipul airspace lookup unavailable: {airspace}")
            airspace = []
        if isinstance(laminar_notams, Exception):
            errors.append(f"laminar NOTAM data unavailable: {laminar_notams}")
            laminar_notams = []
        if isinstance(hiorg_events, Exception):
            errors.append(f"HiOrg events unavailable: {hiorg_events}")
            hiorg_events = []
        if isinstance(water_quality, Exception):
            errors.append(f"Water quality data unavailable: {water_quality}")
            water_quality = []
        if isinstance(mosel_stage, Exception):
            errors.append(f"Mosel stage data unavailable: {mosel_stage}")
            mosel_stage = None

        # Bewerte Wasserqualität (Chlorophyll a / Blaualgen) — nur Fankel (andere Stationen haben keine Chlorophyll-Daten)
        water_quality_assessments: list[WaterQualityAssessment] = []
        if water_quality:
            try:
                fankel_measurements = [m for m in water_quality if m.station == "fankel"]
                if fankel_measurements:
                    water_quality_assessments = water_client.assess_water_quality(fankel_measurements)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Water quality assessment failed: {exc}")

        return DashboardData(
            location=self._settings.location_name,
            latitude=self._settings.latitude,
            longitude=self._settings.longitude,
            fetched_at=datetime.now(ZoneInfo(self._settings.timezone)),
            current=current,
            daily=daily,
            hourly=hourly,
            drone=drone,
            dipul_news=dipul_news,
            airspace=airspace,
            laminar_notams=laminar_notams,
            nina_alerts=[],
            hiorg_events=hiorg_events if self._hiorg_enabled else [],
            errors=errors,
            water_quality=water_quality,
            water_quality_assessments=water_quality_assessments,
            mosel_stage_data=mosel_stage,
        )

    @staticmethod
    async def _safe_fetch_weather(client: OpenMeteoClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001 — surface upstream failures in UI
            errors.append(f"Weather data unavailable: {exc}")
            return None, None, None, None

    @staticmethod
    async def _safe_fetch_news(client: DipulNewsClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"dipul news unavailable: {exc}")
            return []

    @staticmethod
    async def _safe_fetch_airspace(client: DipulWmsClient, errors: list[str]):
        try:
            return await client.fetch_nearby_restrictions()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"dipul airspace lookup unavailable: {exc}")
            return []

    @staticmethod
    async def _safe_fetch_notams(client: LaminarNotamClient, errors: list[str]):
        try:
            return await client.fetch_notams()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"laminar NOTAM data unavailable: {exc}")
            return []

    @staticmethod
    async def _safe_fetch_water_quality(client: WaterPortalClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Water quality data unavailable: {exc}")
            return []

    @staticmethod
    async def _safe_fetch_mosel_stage(client: MoselStageClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Mosel stage data unavailable: {exc}")
            return None

    @staticmethod
    async def _safe_fetch_hiorg(client: HiOrgEventsClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"HiOrg events unavailable: {exc}")
            return []
