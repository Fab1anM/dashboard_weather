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
class LaminarNotam:
    notam_id: str
    text: str
    aerodrome_icao: str | None = None
    fir_icao: str | None = None
    issued_at: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    q_code: str | None = None


@dataclass(slots=True)
class WarningAlert:
    event: str
    headline: str
    description: str
    severity: str
    certainty: str
    sender: str
    start: str
    end: str
    UTM_Lat: int | None = None
    UTM_Lon: int | None = None


@dataclass(slots=True)
class WaterQualityMeasurement:
    station: str
    parameter: str
    value: float
    unit: str | None
    timestamp: str | None


@dataclass(slots=True)
class WaterQualityAssessment:
    station: str
    chlorophyll_a_ug_per_l: float
    classification: str
    description: str
    notes: list[str] = field(default_factory=list)
    observed_at: str | None = None


@dataclass(slots=True)
class HiOrgEvent:
    title: str
    location: str
    start: str
    end: str | None = None
    description: str = ""
    category: str = ""


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
    laminar_notams: list[LaminarNotam] = field(default_factory=list)
    nina_alerts: list[WarningAlert] = field(default_factory=list)
    hiorg_events: list[HiOrgEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    water_quality: list[WaterQualityMeasurement] = field(default_factory=list)
    water_quality_assessments: list[WaterQualityAssessment] = field(default_factory=list)
