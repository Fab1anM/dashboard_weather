# Dashboard Weather

> Live-Wetter- und Drohnenflug-Dashboard für den Einsatz am Boden.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![UV](https://img.shields.io/badge/uv-0.4+-blue)](https://docs.astral.sh/uv/)
[![Docker](https://img.shields.io/badge/docker-ready-blue?logo=docker)](Dockerfile)

## 📖 Überblick

**Dashboard Weather** ist ein webbasiertes Einsatz-Dashboard für Wetter- und Drohnenfluginformationen in **Trier, Deutschland**. Es kombiniert Echtzeit-Wetterdaten mit flugrelevanten Kontextinformationen von [dipul.de](https://www.dipul.de) – der offiziellen digitalen Plattform für unbemannte Luftfahrt in Deutschland.

Das Dashboard richtet sich an Einsatzkräfte, Drohnenpiloten und Einsatzstellen, die eine schnelle, übersichtliche Übersicht über Wetterbedingungen und Luftrauminformationen benötigen.

## ✨ Features

| Feature | Quelle | Beschreibung |
|---|---|---|
| 🌡️ **Aktuelles Wetter** | [Open-Meteo](https://open-meteo.com) | Live-Temperatur, Wind, Luftfeuchtigkeit, Bewölkung |
| 📅 **3-Tage-Vorschau** | [Open-Meteo](https://open-meteo.com) | Temperatur und Niederschlag für die nächsten 3 Tage |
| ⏱️ **Stundenübersicht** | [Open-Meteo](https://open-meteo.com) | 12-Stunden-Prognose mit Wind und Bewölkung |
| 🚁 **Drohnenflug-Suitability** | Eigenentwicklung | Heuristik für Wind, Böen, Niederschlag und Wolken |
| 🗺️ **Luftraum-Overlay** | [dipul WMS](https://www.dipul.de) | Grafische Darstellung von Luftraumrestriktionen |
| 📰 **dipul News** | [dipul](https://www.dipul.de) | Aktuelle Pressemitteilungen und Informationen |
| 🌙 **Nacht-Modus** | Eigenentwicklung | Automatischer Wechsel 18:00–07:00 |
| 📱 **Responsive Design** | Eigenentwicklung | Optimiert für 16:9-Displays und Mobilgeräte |

## 🚀 Schnellstart

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

# Server starten
uv run dashboard-weather
```

Die Anwendung ist unter [http://localhost:8000](http://localhost:8000) erreichbar.

### Docker

```bash
docker compose up --build
```

## ⚙️ Konfiguration

Alle Einstellungen werden über Umgebungsvariablen gesteuert:

| Variable | Standard | Beschreibung |
|---|---|---|
| `DASHBOARD_HOST` | `0.0.0.0` | Netzwerk-Adresse zum Binden |
| `DASHBOARD_PORT` | `8000` | HTTP-Port |
| `DASHBOARD_LOCATION` | `Trier, Germany` | Anzeigename des Standorts |
| `DASHBOARD_LATITUDE` | `49.7596` | Breitengrad |
| `DASHBOARD_LONGITUDE` | `6.6442` | Längengrad |
| `DASHBOARD_TIMEZONE` | `Europe/Berlin` | Zeitzone für Prognosen |
| `DASHBOARD_CACHE_TTL` | `300` | Cache-Lebensdauer in Sekunden |

### Beispiel

```bash
DASHBOARD_PORT=9000 DASHBOARD_LOCATION="Berlin, Germany" uv run dashboard-weather
```

## 📡 API

| Endpoint | Methode | Beschreibung |
|---|---|---|
| `/` | `GET` | HTML-Dashboard |
| `/api/dashboard` | `GET` | JSON-Daten (optional: `?refresh=true`) |
| `/health` | `GET` | Gesundheitsstatus |

### JSON-Response Struktur

```json
{
  "location": "Trier, Germany",
  "current": {
    "temperature": 24,
    "feels_like": 23,
    "wind_speed": 12.5,
    "wind_gusts": 22.0,
    "humidity": 45,
    "cloud_cover": 10,
    "condition": "partly_cloudy"
  },
  "hourly": [...],
  "forecast": [...],
  "drone_conditions": "good",
  "airspace_status": "clear",
  "news": [...]
}
```

## 📁 Projektstruktur

```
dashboard_weather/
├── dashboard_weather/
│   ├── clients/            # Externe Datenquellen (Open-Meteo, dipul WMS)
│   ├── services/           # Business Logic, Aggregation, Caching
│   ├── web/                # FastAPI-App
│   │   ├── templates/      # Jinja2 HTML-Templates
│   │   └── static/         # CSS, JS, Assets
│   ├── config.py           # Konfigurationsmanagement
│   ├── models.py           # Pydantic-Modelle
│   └── main.py             # Einstiegspunkt
├── tests/                  # Pytest-Suite
├── Dockerfile              # Docker-Build
├── docker-compose.yml      # Docker-Komposition
├── pyproject.toml          # Projektmetadaten und Abhängigkeiten
└── README.md               # Diese Datei
```

## 🧪 Entwicklung

### Tests ausführen

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check --fix .
uv run ruff format .
```

## 📄 Lizenz

Dieses Projekt ist lizenziert unter der [MIT License](LICENSE).

## ⚠️ Haftungsausschluss

Dieses Dashboard dient ausschließlich zu Informationszwecken. Überprüfen Sie immer Wetterbedingungen, Luftraumrestriktionen und rechtliche Anforderungen im offiziellen [dipul-Kartentool](https://www.dipul.de), bevor Sie eine Drohne starten.

Das Betreiben von unbemannten Luftfahrzeugen unterliegt gesetzlichen Bestimmungen. Die Verantwortung für die Einhaltung aller relevanten Vorschriften liegt beim Betreiber.

---

**Betreut von:** DLRG Trier-Stadt (Wasserrettung)
