import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from dashboard_weather.cache import TTLCache
from dashboard_weather.clients.dipul_news import DipulNewsClient
from dashboard_weather.clients.dipul_wms import DipulWmsClient
from dashboard_weather.clients.open_meteo import OpenMeteoClient
from dashboard_weather.config import Settings
from dashboard_weather.fallbacks import empty_dashboard
from dashboard_weather.models import DashboardData


class DashboardService:
    CACHE_KEY = "dashboard"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: TTLCache[DashboardData] = TTLCache(settings.cache_ttl_seconds)

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

            weather_result, dipul_news, airspace = await asyncio.gather(
                self._safe_fetch_weather(weather_client, errors),
                self._safe_fetch_news(news_client, errors),
                self._safe_fetch_airspace(wms_client, errors),
                return_exceptions=True,
            )

        if isinstance(weather_result, Exception):
            return empty_dashboard(self._settings, errors)

        current, daily, hourly, drone = weather_result
        if isinstance(dipul_news, Exception):
            errors.append(f"dipul news unavailable: {dipul_news}")
            dipul_news = []
        if isinstance(airspace, Exception):
            errors.append(f"dipul airspace lookup unavailable: {airspace}")
            airspace = []

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
            errors=errors,
        )

    @staticmethod
    async def _safe_fetch_weather(client: OpenMeteoClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:  # noqa: BLE001 - surface upstream failures in UI
            errors.append(f"Weather data unavailable: {exc}")
            raise

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
