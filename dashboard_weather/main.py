import uvicorn

from dashboard_weather.config import load_settings
from dashboard_weather.web.app import create_app


def main() -> None:
    settings = load_settings()
    app = create_app(settings)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
