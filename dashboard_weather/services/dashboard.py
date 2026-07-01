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
from dashboard_weather.clients.mosel_stage import MoselStageClient
from dashboard_weather.clients.open_meteo import OpenMeteoClient
from dashboard_weather.clients.water_portal import WaterPortalClient, WaterQualityAssessment
from dashboard_weather.config import Settings
from dashboard_weather.models import (
    CurrentWeather,
    DailyForecast,
    DashboardData,
    DroneConditions,
    HourlySnapshot,
)


class DashboardService:
    CACHE_KEY = "dashboard"
    WEATHER_CACHE_KEY = "weather"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._cache: TTLCache[DashboardData] = TTLCache(settings.cache_ttl_seconds)
        self._weather_cache: TTLCache[
            tuple[CurrentWeather, list[DailyForecast], list[HourlySnapshot], DroneConditions]
        ] = TTLCache(settings.weather_cache_ttl_seconds)

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

        # Each data source gets its own httpx.AsyncClient with its own timeout,
        # so one source failure never cascades to others.
        weather_client = OpenMeteoClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        news_client = DipulNewsClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        wms_client = DipulWmsClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        water_client = WaterPortalClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        mosel_client = MoselStageClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        hiorg_client = HiOrgEventsClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )
        notam_client = LaminarNotamClient(
            self._settings,
            httpx.AsyncClient(
                timeout=self._settings.request_timeout_seconds,
                headers={
                    "User-Agent": "dashboard-weather/0.1 (+https://github.com/local/dashboard-weather)"
                },
            ),
        )

        # Weather is fetched with its own 12h cache.
        # All other sources run in parallel with individual clients.
        tasks: list[Any] = [
            self._safe_fetch_weather(weather_client, errors),
            self._safe_fetch_news(news_client, errors),
            self._safe_fetch_airspace(wms_client, errors),
            self._safe_fetch_notams(notam_client, errors),
            self._safe_fetch_water_quality(water_client, errors),
            self._safe_fetch_mosel_stage(mosel_client, errors),
        ]
        if self._hiorg_enabled:
            tasks.append(self._safe_fetch_hiorg(hiorg_client, errors))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        weather_result = results[0]
        # _safe_fetch_weather returns (None, None, None, None) on failure,
        # or the actual tuple on success.
        if isinstance(weather_result, BaseException):
            errors.append(f"Weather data unavailable: {weather_result}")
            current, daily, hourly, drone = self._build_weather_placeholder()
        elif weather_result[0] is None:
            # All-NONE tuple from _safe_fetch_weather - error already added there
            current, daily, hourly, drone = self._build_weather_placeholder()
        else:
            current, daily, hourly, drone = weather_result

        # Unpack results (index 1 = news, 2 = airspace, 3 = notams, etc.)
        dipul_news: Any = results[1]
        airspace: Any = results[2]
        laminar_notams: Any = results[3]
        water_quality: Any = results[4]
        mosel_stage: Any = results[5]
        hiorg_events: Any = results[6] if self._hiorg_enabled else []

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

        # Bewerte Wasserqualität (Chlorophyll a / Blaualgen)
        # nur Fankel hat Chlorophyll-Daten
        water_quality_assessments: list[WaterQualityAssessment] = []
        if water_quality:
            try:
                fankel_measurements = [m for m in water_quality if m.station == "fankel"]
                if fankel_measurements:
                    water_quality_assessments = water_client.assess_water_quality(
                        fankel_measurements
                    )
            except Exception as exc:
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

    async def _safe_fetch_weather(
        self, client: OpenMeteoClient, errors: list[str]
    ) -> tuple[
        CurrentWeather | None,
        list[DailyForecast] | None,
        list[HourlySnapshot] | None,
        DroneConditions | None,
    ]:
        cached = self._weather_cache.get(self.WEATHER_CACHE_KEY)
        if cached is not None:
            return cached

        try:
            result = await client.fetch()
            self._weather_cache.set(self.WEATHER_CACHE_KEY, result)
            return result
        except Exception as exc:
            errors.append(f"Weather data unavailable: {exc}")
            return None, None, None, None
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_news(client: DipulNewsClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:
            errors.append(f"dipul news unavailable: {exc}")
            return []
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_airspace(client: DipulWmsClient, errors: list[str]):
        try:
            return await client.fetch_nearby_restrictions()
        except Exception as exc:
            errors.append(f"dipul airspace lookup unavailable: {exc}")
            return []
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_notams(client: LaminarNotamClient, errors: list[str]):
        try:
            return await client.fetch_notams()
        except Exception as exc:
            errors.append(f"laminar NOTAM data unavailable: {exc}")
            return []
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_water_quality(client: WaterPortalClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:
            errors.append(f"Water quality data unavailable: {exc}")
            return []
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_mosel_stage(client: MoselStageClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:
            errors.append(f"Mosel stage data unavailable: {exc}")
            return None
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    async def _safe_fetch_hiorg(client: HiOrgEventsClient, errors: list[str]):
        try:
            return await client.fetch()
        except Exception as exc:
            errors.append(f"HiOrg events unavailable: {exc}")
            return []
        finally:
            if hasattr(client, "_client"):
                await client._client.aclose()

    @staticmethod
    def _build_weather_placeholder() -> (
        tuple[
            CurrentWeather,
            list[DailyForecast],
            list[HourlySnapshot],
            DroneConditions,
        ]
    ):
        """Build placeholder weather data for when the weather API is down.

        Returns a full set of zeroed-out models so the rest of the
        dashboard can still render with other available data sources
        (Moselpegel, WasserqualitÃ¤t, NINA, etc.).
        """
        now = datetime.now(ZoneInfo("Europe/Berlin"))
        placeholder = CurrentWeather(
            temperature_c=0.0,
            apparent_temperature_c=0.0,
            humidity_percent=0,
            precipitation_mm=0.0,
            wind_speed_kmh=0.0,
            wind_direction_deg=0,
            wind_gusts_kmh=0.0,
            cloud_cover_percent=0,
            weather_code=0,
            description="Weather data unavailable",
            observed_at=now,
        )
        drone = DroneConditions(
            wind_10m_kmh=0.0,
            wind_80m_kmh=0.0,
            wind_120m_kmh=0.0,
            wind_gusts_kmh=0.0,
            cloud_cover_total_percent=0,
            cloud_cover_low_percent=0,
            suitability="unknown",
            suitability_detail="Weather data could not be loaded.",
            notes=["Wetterdaten sind nicht verfÃ¼gbar. Andere Quellen werden trotzdem angezeigt."],
        )
        return placeholder, [], [], drone
