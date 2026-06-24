from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class CurrentWeather:
    temperature_c: float
    apparent_temperature_c: float
    humidity_percent: int
    precipitation_mm: float
    wind_speed_kmh: float
    wind_direction_deg: int
    wind_gusts_kmh: float
    cloud_cover_percent: int
    weather_code: int
    description: str
    observed_at: datetime


@dataclass(slots=True)
class DailyForecast:
    date: str
    weather_code: int
    description: str
    temp_min_c: float
    temp_max_c: float
    precipitation_sum_mm: float
    wind_max_kmh: float


@dataclass(slots=True)
class HourlySnapshot:
    time: datetime
    temperature_c: float
    precipitation_probability_percent: int | None
    wind_speed_kmh: float
    wind_gusts_kmh: float


@dataclass(slots=True)
class DroneConditions:
    wind_10m_kmh: float
    wind_80m_kmh: float
    wind_120m_kmh: float
    wind_gusts_kmh: float
    cloud_cover_total_percent: int
    cloud_cover_low_percent: int
    suitability: str
    suitability_detail: str
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DipulNewsItem:
    title: str
    date: str
    summary: str
    url: str


@dataclass(slots=True)
class AirspaceRestriction:
    layer: str
    title: str
    details: dict[str, str]


@dataclass(slots=True)
class DashboardData:
    location: str
    latitude: float
    longitude: float
    fetched_at: datetime
    current: CurrentWeather
    daily: list[DailyForecast]
    hourly: list[HourlySnapshot]
    drone: DroneConditions
    dipul_news: list[DipulNewsItem]
    airspace: list[AirspaceRestriction]
    errors: list[str] = field(default_factory=list)
