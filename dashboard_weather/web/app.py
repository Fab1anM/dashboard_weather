from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from dashboard_weather.config import Settings, load_settings
from dashboard_weather.models import DashboardData
from dashboard_weather.services.dashboard import DashboardService

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Disable caching for all static file responses."""

    async def dispatch(self, request: Request, call_next):
        # Remove conditional request headers to prevent 304 responses
        if request.url.path.startswith("/static/"):
            # Remove headers that cause browser to send 304 requests
            if "if-modified-since" in request.headers:
                del request.headers["if-modified-since"]
            if "if-none-match" in request.headers:
                del request.headers["if-none-match"]
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    service = DashboardService(settings)

    app = FastAPI(
        title="Dashboard Weather",
        description="Weather and drone operations dashboard for Trier, Germany",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.service = service

    app.add_middleware(NoCacheMiddleware)
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/dashboard")
    async def api_dashboard(refresh: bool = False) -> JSONResponse:
        data = await service.get_dashboard(force_refresh=refresh)
        return JSONResponse(_serialize_dashboard(data))

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, refresh: bool = False) -> HTMLResponse:
        data = await service.get_dashboard(force_refresh=refresh)
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "data": data,
                "settings": settings,
                "timezone": settings.timezone,
            },
        )

    return app


def _serialize_dashboard(data: DashboardData) -> dict:
    payload = asdict(data)
    payload["fetched_at"] = data.fetched_at.isoformat()
    payload["current"]["observed_at"] = data.current.observed_at.isoformat()
    payload["hourly"] = [
        {**item, "time": snapshot.time.isoformat()}
        for item, snapshot in zip(payload["hourly"], data.hourly, strict=True)
    ]
    return payload
