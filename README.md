# Dashboard Weather

> Live-Wetter-, Drohnenflug- und Einsatz-Dashboard für DLRG Wasserrettung in Trier, Deutschland.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UV](https://img.shields.io/badge/uv-0.4+-blue)](https://docs.astral.sh/uv/)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)](Dockerfile)

## Überblick

**Dashboard Weather** ist ein webbasiertes Einsatz-Dashboard für Wetter-, Drohnenflug- und Einsatzinformationen in **Trier, Deutschland**. Es richtet sich an Einsatzkräfte, Drohnenpiloten und Einsatzstellen der DLRG Wasserrettung und bietet eine schnelle, übersichtliche Dashboard-Ansicht auf einem 16:9-TV-Display.

Das Dashboard kombiniert Echtzeit-Wetterdaten mit flugrelevanten Kontextinformationen von [dipul.de](https://www.dipul.de) – der offiziellen digitalen Plattform für unbemannte Luftfahrt in Deutschland – sowie aktuellen Warnmeldungen und Terminen.

> **Hinweis:** Die NINA-API (`warnung.bund.de`) ist seit 2024 nicht mehr verfügbar. Der NINA-Client gibt leer zurück, ohne Fehlermeldungen zu erzeugen.

## Features

| Feature | Quelle | Beschreibung |
|---|---|---|
| 🌡️ **Aktuelles Wetter** | [Open-Meteo](https://open-meteo.com) | Live-Temperatur, Wind, Luftfeuchtigkeit, Bewölkung (12h Cache) |
| 📅 **3-Tage-Vorschau** | [Open-Meteo](https://open-meteo.com) | Temperatur und Niederschlag für die nächsten 3 Tage (12h Cache) |
| ⏱️ **Stundenübersicht** | [Open-Meteo](https://open-meteo.com) | 12-Stunden-Prognose mit Wind und Bewölkung (12h Cache) |
| 🚁 **Drohnenflug-Suitability** | Eigenentwicklung | Heuristik für Wind, Böen, Niederschlag und Wolken |
| 🗺️ **Luftraum-Overlay** | [dipul WMS](https://www.dipul.de) | Grafische Darstellung von Luftraumrestriktionen |
| 📰 **dipul News** | [dipul](https://www.dipul.de) | Aktuelle Pressemitteilungen und Informationen |
| 📅 **HiOrg Termine** | [HiOrg-Server](https://hiorg-server.de) | Optional: Veranstaltungen und Einsätze der DLRG (aktivierbar) |
| 🌊 **Wasserqualitätsdaten** | [Wasserportal RLP](https://geodaten-wasser.rlp-umwelt.de) | Blaualgen- und Sauerstoffmessungen in Trierer Gewässern |
| 🌊 **Mosel-Pegelstand** | [HVZ RLP](https://www.hochwasser.rlp.de) | Echtzeit-Wasserstand, Abfluss und 48h-Vorhersage des Moselpegels Trier |
| ✈️ **NOTAMs** | [Laminar NOTAM](https://notam.laminar.aero) | Flugsicherungs-meldungen für den Luftraum Trier |
| 🌙 **Nacht-Modus** | Eigenentwicklung | Automatischer Wechsel 18:00–07:00 |
| 📱 **Responsive Design** | Eigenentwicklung | Optimiert für 16:9-Displays und Mobilgeräte |

## Architektur & Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                      DashboardService                          │
│                                                                 │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │
│  │Weather  │  │  News   │  │  WMS    │  │ Water   │           │
│  │Client   │  │ Client  │  │ Client  │  │Client   │           │
│  │(12h)    │  │  (5m)   │  │  (5m)   │  │ (5m)    │           │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │
│       │             │            │            │                │
│  ┌────▼────┐ ┌────▼────┐ ┌────▼────┐ ┌────▼────┐              │
│  │  Mosel  │ │ Laminar │ │  HiOrg  │ │  Other  │              │
│  │ Client  │ │  NOTAM  │ │ Client  │ │ Sources │              │
│  │ (5m)    │ │  (5m)   │ │ (5m)    │ │ (5m)    │              │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘              │
│       │             │            │            │                │
│       ▼             ▼            ▼            ▼                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Individual Clients (no shared connection pool)          │   │
│  │  Each source has own timeout, own connection pool        │   │
│  │  Failure in one source does NOT cascade to others        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                           │                                    │
│                    ┌──────▼──────┐                            │
│                    │   FastAPI   │                            │
│                    │  /         │                            │
│                    │  /api/dash │                            │
│                    └─────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### Mosel-Pegel Fallback-Kette

Der MoselStageClient verwendet eine dreistufige Fallback-Kette, um Daten auch bei Netzwerkproblemen bereitzustellen:

1. **Primär: `httpx` (async)** – Direkter API-Zugriff auf `https://www.hochwasser.rlp.de/api/v1/measurement-site/26500100`
2. **Fallback 1: `requests` (sync)** – Gleicher API-Endpoint, aber synchroner Aufruf. Nützlich, wenn der async Client im Docker-Netzwerk blockiert wird.
3. **Fallback 2: `BeautifulSoup` (HTML)** – Scraping der Detailseite, wenn beide HTTP-Methoden scheitern. Liefert nur den aktuellen Pegel, keine Prognosen.

Alle drei Wege verwenden denselben API-Endpoint für Messwerte und Prognosen (p10-p90).

### Isolierte Datenquellen-Architektur

Jeder Datenquellen-Client verwendet einen **eigenen httpx.AsyncClient** mit eigenem Timeout und eigenem Connection-Pool. Dadurch:

- **Kein Kaskadierender Ausfall**: Wenn eine Quelle (z.B. Wasserportal) nicht erreichbar ist, blockiert das nicht die anderen Quellen
- **Unabhängige Timeouts**: Jeder Client hat ein eigenes Timeout, ein langsamer Client blockiert nicht den gesamten Request
- **Ressourcen-Isolation**: Connection-Lecks oder Pool-Exhaustion einer Quelle beeinflussen andere nicht
- **Automatisches Cleanup**: Jeder Client wird nach dem Fetch sauber mit `aclose()` geschlossen

Die Datenabfrage erfolgt in zwei Schritten:

1. **Wetter (12h Cache)** – wird separat abgerufen, da sich Wetterdaten nur langsam ändern und Rate-Limits (429) zu beachten sind
2. **Alle anderen Quellen parallel** – News, WMS, Wasser, Mosel, NOTAM, HiOrg werden parallel mit ihren jeweiligen 5-Minuten-Caches abgerufen

Fehler in einer Quelle werden abgefangen und im `errors`-Feld des Responses gelistet, ohne dass das gesamte Dashboard fehlschlägt.

## Schnellstart

### Voraussetzung

- [Python 3.12+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/) (Dependency Manager, >= 0.4.0)

### Lokal ausführen

```bash
# Repository klonen
git clone https://github.com/<your-username>/dashboard_weather.git
cd dashboard_weather

# Abhängigkeiten installieren
uv sync

# .env-Datei aus der Vorlage erstellen
cp .env.example .env
# .env nach Belieben bearbeiten

# Server starten
uv run python -m dashboard_weather.main
```

Die Anwendung ist unter [http://localhost:8000](http://localhost:8000) erreichbar.

### Docker

```bash
docker compose up --build
```

## Konfiguration

Alle Einstellungen werden über Umgebungsvariablen gesteuert, die aus einer `.env`-Datei im Projekt-Root gelesen werden.

### .env-Datei erstellen

```bash
cp .env.example .env
```

### Konfigurations-Übersicht

| Variable | Standard | Beschreibung |
|---|---|---|
| `DASHBOARD_HOST` | `0.0.0.0` | Netzwerk-Adresse zum Binden |
| `DASHBOARD_PORT` | `8000` | HTTP-Port |
| `DASHBOARD_LOCATION` | `Trier, Germany` | Anzeigename des Standorts |
| `DASHBOARD_LATITUDE` | `49.7596` | Breitengrad |
| `DASHBOARD_LONGITUDE` | `6.6442` | Längengrad |
| `DASHBOARD_TIMEZONE` | `Europe/Berlin` | Zeitzone für Prognosen |
| `DASHBOARD_CACHE_TTL` | `300` | Cache-Lebensdauer in Sekunden für Nicht-Wetter-Daten |
| `DASHBOARD_WEATHER_CACHE_TTL` | `43200` | Cache-Lebensdauer für Wetterdaten in Sekunden (12h) |
| `HIORG_API_URL` | (leer) | HiOrg-Server-URL aktivieren (optional) |

### Beispiel

```bash
DASHBOARD_PORT=9000 DASHBOARD_LOCATION="Berlin, Germany" uv run dashboard-weather
```

### HiOrg-Termine aktivieren

Die HiOrg-Termine sind standardmäßig deaktiviert. Um sie zu aktivieren, setze die Umgebungsvariable:

```bash
HIORG_API_URL="https://hiorg-server.de/api" uv run dashboard-weather
```

Der Client versucht, Events von der HiOrg-Server-API zu laden und blendet das Widget automatisch ein, wenn Daten verfügbar sind.

## API

| Endpoint | Methode | Beschreibung |
|---|---|---|
| `/` | `GET` | HTML-Dashboard |
| `/api/dashboard` | `GET` | JSON-Daten (optional: `?refresh=true`) |
| `/health` | `GET` | Gesundheitsstatus |
| `/docs` | `GET` | Interaktive API-Dokumentation (Swagger UI) |
| `/redoc` | `GET` | Alternative API-Dokumentation (ReDoc) |

### JSON-Response Struktur

```json
{
  "location": "Trier, Germany",
  "current": {
    "temperature_c": 24.0,
    "apparent_temperature_c": 23.0,
    "humidity_percent": 45,
    "wind_speed_kmh": 12.5,
    "wind_gusts_kmh": 22.0,
    "weather_code": 0,
    "description": "clear sky"
  },
  "daily": [...],
  "hourly": [...],
  "drone": {
    "suitability": "good",
    "wind_10m_kmh": 10.0,
    "wind_80m_kmh": 15.0,
    "suitability_detail": "Gut",
    "notes": []
  },
  "airspace": [...],
  "dipul_news": [...],
  "nina_alerts": [],
  "hiorg_events": [],
  "water_quality": [],
  "mosel_stage_data": {
    "station": "Trier / Mosel",
    "current_stage_m": 2.37,
    "timestamp": "2026-06-30T06:15:00Z",
    "trend": "fallend",
    "forecast": [...],
    "threshold_warning_m": 5.0,
    "threshold_high_m": 6.0,
    "description": "Stauregulierung aktiv"
  },
  "water_quality_assessments": [],
  "errors": []
}
```

## Projektstruktur

```
dashboard_weather/
├── dashboard_weather/
│   ├── clients/            # Externe Datenquellen
│   │   ├── open_meteo.py   # Wetterdaten (Open-Meteo)
│   │   ├── dipul_news.py   # dipul Pressemitteilungen
│   │   ├── dipul_wms.py    # Luftraum-Overlay (dipul WMS)
│   │   ├── nina_alerts.py  # NINA/KATWARN Warnmeldungen (disabled)
│   │   ├── hiorg_events.py # HiOrg-Server Termine (optional)
│   │   ├── water_portal.py # Wasserqualitätsdaten (RLP)
│   │   └── mosel_stage.py  # Mosel-Pegelstand (HVZ RLP)
│   ├── services/           # Business Logic, Aggregation, Caching
│   │   └── dashboard.py    # DashboardService
│   ├── web/                # FastAPI-App
│   │   ├── app.py          # FastAPI-App & Routing
│   │   ├── templates/      # Jinja2 HTML-Templates
│   │   └── static/         # CSS, JS, Assets
│   ├── config.py           # Konfigurationsmanagement (.env)
│   ├── models.py           # Dataclasses
│   ├── cache.py            # TTL-Cache
│   ├── fallbacks.py        # Fallback-Funktionen
│   ├── weather_codes.py    # WMO Weather Code Mapping
│   └── main.py             # Einstiegspunkt
├── tests/                  # Pytest-Suite
├── .env.example            # .env-Vorlage
├── Dockerfile              # Docker-Build
├── docker-compose.yml      # Docker-Komposition
├── pyproject.toml          # Projektmetadaten und Abhängigkeiten
└── README.md               # Diese Datei
```

## Entwicklung

### Tests ausführen

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check --fix .
uv run ruff format .
```

### Docker & Raspberry Pi

Die Anwendung kann als Docker-Container deployed werden. Der Container enthält Xvfb und Chromium für headless Browser-Unterstützung (z.B. für Selenium/Selenium-Tests).

Für den Raspberry Pi kann das Dashboard als **Kiosk-Modus** im Vollbild laufen – die FastAPI-API wird gestartet und Chromium öffnet automatisch die Dashboard-Seite im Kiosk-Modus.

```bash
# Image bauen
docker build -t dashboard-weather .

# Container starten
docker-compose up -d

# oder direkt mit docker
docker run -d \
  -p 8000:8000 \
  -e DASHBOARD_LOCATION="Trier, Germany" \
  -e DASHBOARD_LATITUDE="49.7596" \
  -e DASHBOARD_LONGITUDE="6.6442" \
  -e DASHBOARD_TIMEZONE="Europe/Berlin" \
  -e DASHBOARD_CACHE_TTL="300" \
  --name dashboard-weather \
  dashboard-weather
```

#### Raspberry Pi

Für den Raspberry Pi (ARM64/aarch64) das Docker-Image nativ bauen:

```bash
# Auf dem Raspberry Pi:
docker build -t dashboard-weather .
docker run -d -p 8000:8000 --restart unless-stopped dashboard-weather
```

Alternativ mit Docker Compose:

```bash
docker-compose up -d
```

Die Konfiguration erfolgt über Environment-Variablen (siehe `docker-compose.yml`) oder eine `.env`-Datei im Projektverzeichnis.

## Lizenz

Dieses Projekt ist lizenziert unter der [MIT License](LICENSE).

## Haftungsausschluss

Dieses Dashboard dient ausschließlich zu Informationszwecken. Überprüfen Sie immer Wetterbedingungen, Luftraumrestriktionen und rechtliche Anforderungen im offiziellen [dipul-Kartentool](https://www.dipul.de), bevor Sie eine Drohne starten.

Das Betreiben von unbemannten Luftfahrzeugen unterliegt gesetzlichen Bestimmungen. Die Verantwortung für die Einhaltung aller relevanten Vorschriften liegt beim Betreiber.

---

Made with ❤ in Trier