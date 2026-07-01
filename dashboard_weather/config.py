import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    location_name: str = "Trier"
    latitude: float = 49.7596
    longitude: float = 6.6442
    timezone: str = "Europe/Berlin"
    cache_ttl_seconds: int = 300
    dipul_news_url: str = "https://www.dipul.de/homepage/de/aktuelle-meldungen/"
    dipul_wms_url: str = "https://uas-betrieb.de/geoservices/dipul/wms"
    dipul_map_url: str = (
        "https://www.dipul.de/homepage/de/information/geografische-gebiete/kartentool/"
    )
    laminar_notam_api_key: str = ""
    request_timeout_seconds: float = 15.0
    hiorg_api_url: str = "https://hiorg-server.de/api"


# Default environment variable names
ENV_VARS = {
    "host": "DASHBOARD_HOST",
    "port": "DASHBOARD_PORT",
    "location_name": "DASHBOARD_LOCATION",
    "latitude": "DASHBOARD_LATITUDE",
    "longitude": "DASHBOARD_LONGITUDE",
    "timezone": "DASHBOARD_TIMEZONE",
    "cache_ttl_seconds": "DASHBOARD_CACHE_TTL",
    "hiorg_api_url": "HIORG_API_URL",
    "laminar_notam_api_key": "LAMINAR_NOTAM_API_KEY",
}


def load_settings() -> Settings:
    """Load settings from environment variables and .env file.

    Priority: .env file env vars > defaults.
    If .env doesn't exist, only defaults are used.
    """
    from pathlib import Path

    import dotenv

    # Find .env file in project root (one level above this file)
    project_root = Path(__file__).resolve().parent.parent
    env_file = project_root / ".env"

    if env_file.exists():
        dotenv.load_dotenv(dotenv_path=env_file, override=True)

    return Settings(
        host=os.getenv("DASHBOARD_HOST", "0.0.0.0"),
        port=int(os.getenv("DASHBOARD_PORT", "8000")),
        location_name=os.getenv("DASHBOARD_LOCATION", "Trier"),
        latitude=float(os.getenv("DASHBOARD_LATITUDE", "49.7596")),
        longitude=float(os.getenv("DASHBOARD_LONGITUDE", "6.6442")),
        timezone=os.getenv("DASHBOARD_TIMEZONE", "Europe/Berlin"),
        cache_ttl_seconds=int(os.getenv("DASHBOARD_CACHE_TTL", "300")),
        hiorg_api_url=os.getenv("HIORG_API_URL", "https://hiorg-server.de/api"),
        laminar_notam_api_key=os.getenv("LAMINAR_NOTAM_API_KEY", ""),
    )
