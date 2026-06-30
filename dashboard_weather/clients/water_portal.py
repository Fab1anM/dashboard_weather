"""Client for the Rheinland-Pfalz Water Portal (geodaten-wasser.rlp-umwelt.de).

Fetches current water quality measurements from the GUS (Gewasser-Untersuchungsstation)
endpoints. Supports algae (Chlorophyll a) measurements for Fankel, Palzem, and Kanzem.
"""

import logging

import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import (
    WaterQualityAssessment,
    WaterQualityMeasurement,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://geodaten-wasser.rlp-umwelt.de"

STATION_IDS: dict[str, int] = {
    "fankel": 2691510700,
    "palzem": 2619521210,
    "kanzem": 2649525000,
}

REQUIRED_HEADERS = {
    "User-Agent": "dashboard-weather/0.1",
    "Referer": f"{BASE_URL}/gus/{STATION_IDS['fankel']}",
    "Origin": BASE_URL,
}


# EU-Badewasserrichtlinie (2006/7/EG) Grenzwerte für Chlorophyll a (µg/L)
# Quelle: EU Badegewässerrichtlinie & Deutsche Gewässerschutzrichtlinien
CHLOROPHYLL_THRESHOLDS = {
    "gut": (0, 20),  # < 20 µg/L: Gut
    "maessig": (20, 40),  # 20-40 µg/L: Mäßig
    "schlecht": (40, float("inf")),  # > 40 µg/L: Schlecht
}


class WaterPortalClient:
    """Fetches water quality data from the RLP Water Portal API."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(self, *, stations: list[str] | None = None) -> list[WaterQualityMeasurement]:
        """Fetch water quality measurements for specified stations.

        Args:
            stations: List of station keys ('fankel', 'palzem', 'kanzem').
                      Defaults to all configured stations.

        Returns:
            List of WaterQualityMeasurement objects.
        """
        if stations is None:
            stations = list(STATION_IDS.keys())

        station_ids = {name: STATION_IDS[name] for name in stations if name in STATION_IDS}
        if not station_ids:
            return []

        # Use zip to pair station names with coroutines for error messages
        tasks_with_names = [
            (name, self._fetch_station_data(station_id, name))
            for name, station_id in station_ids.items()
        ]

        results: list[WaterQualityMeasurement] = []
        for station_name, task in tasks_with_names:
            try:
                measurements = await task
                results.extend(measurements)
            except Exception as exc:
                logger.warning("Failed to fetch water data for %s: %s", station_name, exc)

        return results

    async def _fetch_station_data(
        self, station_id: int, station_name: str
    ) -> list[WaterQualityMeasurement]:
        """Fetch current measurements for a single station."""
        params = {"w": f"MESSST_NR=number:{station_id}"}

        url = f"{BASE_URL}/api/data/gus_messwerte_messwerteaktuell"

        response = await self._client.get(url, params=params, headers=REQUIRED_HEADERS)
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, list):
            return []

        measurements: list[WaterQualityMeasurement] = []
        for record in data:
            station_key = record.get("messst_nr")
            if station_key != station_id:
                continue

            parameter = record.get("stoff_bezeichnung", "")
            if not parameter:
                continue

            value_raw = record.get("messwert")
            if value_raw is None:
                continue

            try:
                value = float(value_raw)
            except (TypeError, ValueError):
                continue

            unit = record.get("stoff_einheit")
            timestamp = record.get("str_datum")
            if timestamp and record.get("uhrzeit"):
                timestamp = f"{timestamp} {record['uhrzeit']} Uhr"

            measurements.append(
                WaterQualityMeasurement(
                    station=station_name,
                    parameter=parameter,
                    value=value,
                    unit=unit,
                    timestamp=timestamp,
                )
            )

        return measurements

    @staticmethod
    def classify_chlorophyll_a(chlorophyll_a_ug_per_l: float) -> str:
        """Klassifiziere Chlorophyll a nach EU-Badewasserrichtlinie.

        Grenzwerte (µg/L):
          < 20  → "gut"
          20-40 → "maessig"
          > 40  → "schlecht"

        Quelle: EU Badegewässerrichtlinie 2006/7/EG
        """
        if chlorophyll_a_ug_per_l < 20:
            return "gut"
        elif chlorophyll_a_ug_per_l < 40:
            return "maessig"
        else:
            return "schlecht"

    @staticmethod
    def describe_water_quality(
        chlorophyll_a_ug_per_l: float, classification: str
    ) -> tuple[str, list[str]]:
        """Generiere Beschreibung und Hinweise basierend auf der Klassifizierung.

        Returns:
            Tuple von (Hauptbeschreibung, Liste mit zusätzlichen Hinweisen)
        """
        notes: list[str] = []
        description = "Unbekannte Wasserqualität"

        if classification == "gut":
            description = "Gute Wasserqualität — geringer Algenbefall"
            if chlorophyll_a_ug_per_l < 5:
                notes.append("Sehr geringer Hintergrundwert")
            elif chlorophyll_a_ug_per_l < 10:
                notes.append("Leichter Algenbefall innerhalb des Grenzwerts")
            elif chlorophyll_a_ug_per_l < 20:
                notes.append("Grenzwert noch eingehalten, aber Wachstumsneigung sichtbar")

        elif classification == "maessig":
            description = "Mäßige Wasserqualität — mäßiger Algenbefall"
            if chlorophyll_a_ug_per_l < 30:
                notes.append("Vorsicht geboten — Algenwachstum beginnend")
            else:
                notes.append("Algenkonzentration nahe dem Grenzwert")
            notes.append("Kontakt mit dem Wasser vermeiden, wenn möglich")

        elif classification == "schlecht":
            description = "Schlechte Wasserqualität — starker Algenbefall"
            if chlorophyll_a_ug_per_l > 100:
                notes.append("Massenhaftes Blaualgenwachstum (Algenblüte) — Gesundheitsrisiko!")
                notes.append("Baden dringend abzuraten")
            elif chlorophyll_a_ug_per_l > 60:
                notes.append("Starkes Algenwachstum — Baden nicht empfohlen")
            else:
                notes.append("Grenzwert überschritten — Kontakt mit Wasser vermeiden")
            notes.append("Ggf. lokale Badegewässer-Information einsehen")

        return description, notes

    def assess_water_quality(
        self, measurements: list[WaterQualityMeasurement]
    ) -> list[WaterQualityAssessment]:
        """Bewerte Wasserqualität basierend auf Chlorophyll a Messungen.

        Filtert nur Chlorophyll a (Blaualgen) Messungen und klassifiziert
        jede Station nach der EU-Badewasserrichtlinie.
        """
        # Filter für Chlorophyll a Messungen
        chlorophyll_measurements = [
            m
            for m in measurements
            if "chlorophyll" in m.parameter.lower() or "blaualgen" in m.parameter.lower()
        ]

        if not chlorophyll_measurements:
            # Keine Chlorophyll a Daten verfügbar
            assessments = []
            for station_name in STATION_IDS:
                assessments.append(
                    WaterQualityAssessment(
                        station=station_name,
                        chlorophyll_a_ug_per_l=0.0,
                        classification="unbekannt",
                        description="Keine aktuellen Chlorophyll a Messdaten verfügbar",
                        notes=["Werte werden regelmäßig vom RLP-Umweltamt gemessen"],
                    )
                )
            return assessments

        # Pro Station die aktuellste Chlorophyll a Messung verwenden
        station_measurements: dict[str, list[WaterQualityMeasurement]] = {}
        for m in chlorophyll_measurements:
            if m.station not in station_measurements:
                station_measurements[m.station] = []
            station_measurements[m.station].append(m)

        assessments = []
        for station_name, ms in station_measurements.items():
            # Nimm den neuesten Messwert
            latest = max(ms, key=lambda x: x.timestamp or "")

            classification = self.classify_chlorophyll_a(latest.value)
            description, notes = self.describe_water_quality(latest.value, classification)

            assessments.append(
                WaterQualityAssessment(
                    station=station_name,
                    chlorophyll_a_ug_per_l=latest.value,
                    classification=classification,
                    description=description,
                    notes=notes,
                    observed_at=latest.timestamp,
                )
            )

        return assessments
