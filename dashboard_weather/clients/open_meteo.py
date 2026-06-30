from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import (
    CurrentWeather,
    DailyForecast,
    DroneConditions,
    HourlySnapshot,
)
from dashboard_weather.weather_codes import describe_weather_code

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(
        self,
    ) -> tuple[CurrentWeather, list[DailyForecast], list[HourlySnapshot], DroneConditions]:
        params = {
            "latitude": self._settings.latitude,
            "longitude": self._settings.longitude,
            "timezone": self._settings.timezone,
            "forecast_days": 3,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "apparent_temperature",
                    "precipitation",
                    "weather_code",
                    "wind_speed_10m",
                    "wind_direction_10m",
                    "wind_gusts_10m",
                    "cloud_cover",
                ]
            ),
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "precipitation_probability",
                    "wind_speed_10m",
                    "wind_gusts_10m",
                    "wind_speed_80m",
                    "wind_speed_120m",
                    "cloud_cover",
                    "cloud_cover_low",
                ]
            ),
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                ]
            ),
        }
        response = await self._client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        payload = response.json()

        current_payload = payload["current"]
        weather_code = int(current_payload["weather_code"])
        current = CurrentWeather(
            temperature_c=float(current_payload["temperature_2m"]),
            apparent_temperature_c=float(current_payload["apparent_temperature"]),
            humidity_percent=int(current_payload["relative_humidity_2m"]),
            precipitation_mm=float(current_payload["precipitation"]),
            wind_speed_kmh=float(current_payload["wind_speed_10m"]),
            wind_direction_deg=int(current_payload["wind_direction_10m"]),
            wind_gusts_kmh=float(current_payload["wind_gusts_10m"]),
            cloud_cover_percent=int(current_payload.get("cloud_cover") or 0),
            weather_code=weather_code,
            description=describe_weather_code(weather_code),
            observed_at=datetime.fromisoformat(current_payload["time"]),
        )

        daily: list[DailyForecast] = []
        daily_payload = payload["daily"]
        for index, date in enumerate(daily_payload["time"]):
            code = int(daily_payload["weather_code"][index])
            daily.append(
                DailyForecast(
                    date=date,
                    weather_code=code,
                    description=describe_weather_code(code),
                    temp_min_c=float(daily_payload["temperature_2m_min"][index]),
                    temp_max_c=float(daily_payload["temperature_2m_max"][index]),
                    precipitation_sum_mm=float(daily_payload["precipitation_sum"][index]),
                    wind_max_kmh=float(daily_payload["wind_speed_10m_max"][index]),
                )
            )

        hourly: list[HourlySnapshot] = []
        hourly_payload = payload["hourly"]
        berlin = ZoneInfo(self._settings.timezone)
        now = datetime.now(berlin)
        for index, time_value in enumerate(hourly_payload["time"]):
            snapshot_time = datetime.fromisoformat(time_value).replace(tzinfo=berlin)
            if snapshot_time < now.replace(minute=0, second=0, microsecond=0):
                continue
            if len(hourly) >= 12:
                break
            probability = hourly_payload.get("precipitation_probability")
            hourly.append(
                HourlySnapshot(
                    time=snapshot_time,
                    temperature_c=float(hourly_payload["temperature_2m"][index]),
                    precipitation_probability_percent=(
                        int(probability[index]) if probability else None
                    ),
                    wind_speed_kmh=float(hourly_payload["wind_speed_10m"][index]),
                    wind_gusts_kmh=float(hourly_payload["wind_gusts_10m"][index]),
                )
            )

        current_index = self._current_hour_index(hourly_payload["time"])
        wind_80m = float(hourly_payload["wind_speed_80m"][current_index])
        wind_120m = float(hourly_payload["wind_speed_120m"][current_index])
        cloud_low = int(hourly_payload["cloud_cover_low"][current_index])
        drone = self._build_drone_conditions(current, wind_80m, wind_120m, cloud_low)
        return current, daily, hourly, drone

    def _current_hour_index(self, times: list[str]) -> int:
        berlin = ZoneInfo(self._settings.timezone)
        now = datetime.now(berlin)
        for index, time_value in enumerate(times):
            snapshot_time = datetime.fromisoformat(time_value).replace(tzinfo=berlin)
            if snapshot_time.hour == now.hour and snapshot_time.date() == now.date():
                return index
        return 0

    @staticmethod
    def _build_drone_conditions(
        current: CurrentWeather,
        wind_80m_kmh: float,
        wind_120m_kmh: float,
        cloud_low_percent: int,
    ) -> DroneConditions:
        notes: list[str] = []
        score = 100

        if current.wind_speed_kmh > 25:
            score -= 35
            notes.append("Böenwind über 25 km/h.")
        elif current.wind_speed_kmh > 18:
            score -= 15
            notes.append("Erhöhter Wind — mit Vorsicht fliegen.")

        if current.wind_gusts_kmh > 35:
            score -= 30
            notes.append("Starke Böen.")
        elif current.wind_gusts_kmh > 25:
            score -= 10

        if current.precipitation_mm > 0:
            score -= 25
            notes.append("Aktiver Niederschlag.")

        if current.weather_code >= 95:
            score -= 40
            notes.append("Gewittergefahr — nicht fliegen.")

        if cloud_low_percent > 70:
            score -= 10
            notes.append("Bewölkung kann Sichtbarkeit einschränken.")

        if score >= 80:
            suitability = "good"
            detail = "Gute Bedingungen für UAV."
        elif score >= 55:
            suitability = "caution"
            detail = "Fliegbar mit Vorsicht — Wind und Sicht prüfen."
        else:
            suitability = "poor"
            detail = "Flugverschiebung empfohlen."

        if not notes:
            notes.append("Keine Wetterblocker für Freifluggeschäfte mit UAV erkannt.")

        return DroneConditions(
            wind_10m_kmh=current.wind_speed_kmh,
            wind_80m_kmh=wind_80m_kmh,
            wind_120m_kmh=wind_120m_kmh,
            wind_gusts_kmh=current.wind_gusts_kmh,
            cloud_cover_total_percent=current.cloud_cover_percent,
            cloud_cover_low_percent=cloud_low_percent,
            suitability=suitability,
            suitability_detail=detail,
            notes=notes,
        )
