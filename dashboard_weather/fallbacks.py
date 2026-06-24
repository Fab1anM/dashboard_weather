from datetime import datetime

from dashboard_weather.config import Settings
from dashboard_weather.models import (
    CurrentWeather,
    DashboardData,
    DroneConditions,
)


def empty_dashboard(settings: Settings, errors: list[str]) -> DashboardData:
    now = datetime.now().astimezone()
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
        description="Unavailable",
        observed_at=now,
    )
    return DashboardData(
        location=settings.location_name,
        latitude=settings.latitude,
        longitude=settings.longitude,
        fetched_at=now,
        current=placeholder,
        daily=[],
        hourly=[],
        drone=DroneConditions(
            wind_10m_kmh=0.0,
            wind_80m_kmh=0.0,
            wind_120m_kmh=0.0,
            wind_gusts_kmh=0.0,
            cloud_cover_total_percent=0,
            cloud_cover_low_percent=0,
            suitability="unknown",
            suitability_detail="Weather data could not be loaded.",
            notes=errors,
        ),
        dipul_news=[],
        airspace=[],
        errors=errors,
    )
