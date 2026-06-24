from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    location_name: str = "Trier, Germany"
    latitude: float = 49.7596
    longitude: float = 6.6442
    timezone: str = "Europe/Berlin"
    cache_ttl_seconds: int = 300
    dipul_news_url: str = "https://www.dipul.de/homepage/de/aktuelle-meldungen/"
    dipul_wms_url: str = "https://uas-betrieb.de/geoservices/dipul/wms"
    dipul_map_url: str = "https://www.dipul.de/homepage/de/information/geografische-gebiete/kartentool/"
    request_timeout_seconds: float = 15.0


def load_settings() -> Settings:
    return Settings(
        host=os.getenv("DASHBOARD_HOST", "0.0.0.0"),
        port=int(os.getenv("DASHBOARD_PORT", "8000")),
        location_name=os.getenv("DASHBOARD_LOCATION", "Trier, Germany"),
        latitude=float(os.getenv("DASHBOARD_LATITUDE", "49.7596")),
        longitude=float(os.getenv("DASHBOARD_LONGITUDE", "6.6442")),
        timezone=os.getenv("DASHBOARD_TIMEZONE", "Europe/Berlin"),
        cache_ttl_seconds=int(os.getenv("DASHBOARD_CACHE_TTL", "300")),
    )
