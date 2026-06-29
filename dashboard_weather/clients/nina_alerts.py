import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import WarningAlert

# NINA API v3.1 server (new format, replaces the old warnung.bund.de/api/entry.json)
NINA_API_BASE = "https://warnung.bund.de/api31"

# ARS (Amtlicher Regionalschlüssel) for Trier districts
# Format: 5-digit district code + 6 zeros
TRIER_DISTRICT_ARS = "072110000000"       # Trier-Stadt
TRIER_SAARBURG_ARS = "072340000000"      # Trier-Saarburg
RLP_STATE_ARS = "120000000000"           # Rheinland-Pfalz

# Sources to aggregate warnings from (order = priority)
WARNING_SOURCES = ["katwarn", "mowas", "dwd", "police", "lhp", "biwapp"]


class NinaAlertClient:
    """Fetches emergency warnings from the NINA API v3.1."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(self, limit: int = 10) -> list[WarningAlert]:
        """Fetch current warnings for the configured location.

        Strategy:
          1. Try the dashboard endpoint for the district (fastest, most specific).
          2. If the dashboard returns empty or errors, aggregate from all
             mapData sources (katwarn, mowas, dwd, police, etc.).
        """
        alerts: list[WarningAlert] = []

        # Try dashboard endpoint first (district-specific)
        district_alerts = await self._fetch_dashboard(TRIER_DISTRICT_ARS)
        if district_alerts:
            alerts.extend(district_alerts)
        else:
            # Fallback: aggregate from all mapData sources
            for source in WARNING_SOURCES:
                source_alerts = await self._fetch_source(source)
                alerts.extend(source_alerts)

        # Sort by start date descending, limit results
        alerts.sort(key=lambda a: a.start, reverse=True)
        return alerts[:limit]

    async def _fetch_dashboard(self, ars: str) -> list[WarningAlert]:
        """Fetch warnings from the dashboard endpoint for a specific region."""
        url = f"{NINA_API_BASE}/dashboard/{ars}.json"
        try:
            resp = await self._client.get(url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, list):
                return []

            return [alert for entry in data if (alert := self._parse_dashboard_entry(entry)) is not None]
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

    async def _fetch_source(self, source: str) -> list[WarningAlert]:
        """Fetch warnings from a specific mapData source."""
        url = f"{NINA_API_BASE}/{source}/mapData.json"
        try:
            resp = await self._client.get(url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, list):
                return []

            return [alert for entry in data if (alert := self._parse_map_data_entry(entry)) is not None]
        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

    @staticmethod
    def _is_valid_entry(entry: dict) -> bool:
        """Check if an entry is a valid alert (not an Update of a removed warning)."""
        if not isinstance(entry, dict):
            return False
        # Filter out Update entries with no real content
        entry_type = entry.get("type", "")
        # Exclude "Update" entries that are just version bumps without new info
        if entry_type == "Update":
            # Keep if there's a startDate in the future or not too far past
            start = entry.get("startDate", "")
            if start:
                return True  # Keep it; the frontend can handle it
        return True

    @staticmethod
    def _parse_dashboard_entry(entry: dict) -> WarningAlert | None:
        """Parse an entry from the dashboard endpoint.

        Dashboard entries have a different structure than mapData entries.
        They may contain nested warning objects.
        """
        # Dashboard entries can be either direct Warning objects or
        # contain a 'warnings' key with an array
        warnings = entry.get("warnings", [])
        if isinstance(warnings, list) and warnings:
            # Combine all warnings from this dashboard entry
            result: list[WarningAlert] = []
            for w in warnings:
                alert = NinaAlertClient._parse_map_data_entry(w)
                if alert:
                    result.append(alert)
            if result:
                return result[0]

        # Fall back to treating the entry itself as a warning
        return NinaAlertClient._parse_map_data_entry(entry)

    @staticmethod
    def _parse_map_data_entry(entry: dict) -> WarningAlert | None:
        """Parse a warning entry from a mapData endpoint."""
        if not isinstance(entry, dict):
            return None

        # Extract i18n title (prefer German)
        i18n_title = entry.get("i18nTitle", {})
        if isinstance(i18n_title, dict):
            headline = i18n_title.get("de", "")
            if not headline:
                # Fall back to first available language
                headline = next(iter(i18n_title.values()), "Warnung")
        else:
            headline = str(i18n_title)

        # Extract sender from the ID (format varies by source)
        warning_id = entry.get("id", "")
        sender = NinaAlertClient._extract_sender(warning_id, entry.get("type", ""))

        # Extract event type from transKeys or ID
        trans_keys = entry.get("transKeys", {})
        event = ""
        if isinstance(trans_keys, dict):
            event = trans_keys.get("event", "")
        if not event:
            # Derive event type from the ID prefix or source
            if "dwd" in warning_id:
                event = "DWD Warnung"
            elif "kat" in warning_id:
                event = "KATWARN"
            elif "mow" in warning_id:
                event = "MoWaS"
            else:
                event = "Warnung"

        # Parse severity
        severity_raw = entry.get("severity", "Unbekannt")
        severity = NinaAlertClient._map_severity(severity_raw)

        # Parse urgency as certainty
        urgency_raw = entry.get("urgency", "Unknown")
        certainty = NinaAlertClient._map_urgency(urgency_raw)

        # Parse time fields
        start_str = entry.get("startDate", "")
        end_str = entry.get("expiresDate", "")

        # Parse description from transKeys or use headline as description
        description = ""
        if isinstance(trans_keys, dict):
            description = trans_keys.get("description", trans_keys.get("instruction", ""))
        if not description and i18n_title:
            # Use the English title as a secondary description
            if isinstance(i18n_title, dict):
                description = i18n_title.get("en", "")

        return WarningAlert(
            event=event,
            headline=headline,
            description=description,
            severity=severity,
            certainty=certainty,
            sender=sender,
            start=start_str,
            end=end_str,
        )

    @staticmethod
    def _extract_sender(warning_id: str, entry_type: str) -> str:
        """Extract the sender/origin from the warning ID."""
        # ID formats:
        #   kat.xxx → KATWARN
        #   mow.DE-XX-XXX → MoWaS (state prefix indicates source)
        #   dwdmap.xxx → DWD
        if "kat" in warning_id:
            return "KATWARN"
        if "dwd" in warning_id:
            return "DWD"
        if "mow" in warning_id:
            return "MoWaS"
        if "police" in warning_id or "pol" in warning_id:
            return "Polizei"
        if "lhp" in warning_id:
            return "LHP"
        if "biwapp" in warning_id:
            return "BIWAPP"

        # Try to extract from transKeys sender field
        return "BfBBK"  # Default: Bundesamt für Bevölkerungsschutz und Katastrophenhilfe

    @staticmethod
    def _map_severity(raw: str) -> str:
        """Map API severity strings to German display values."""
        severity_map: dict[str, str] = {
            "Green": "grün",
            "Blue": "blau",
            "Yellow": "gelb",
            "Orange": "orange",
            "Red": "rot",
            "Extreme": "extrem",
            "Severe": "schwerwiegend",
            "Minor": "geringfügig",
            "Moderate": "mäßig",
            "Unknown": "unbekannt",
            "no_alert": "keine Warnung",
        }
        return severity_map.get(raw, raw.lower() if raw else "unbekannt")

    @staticmethod
    def _map_urgency(raw: str) -> str:
        """Map API urgency strings to German certainty-like labels."""
        urgency_map: dict[str, str] = {
            "Immediate": "sofort",
            "Expected": "zu erwarten",
            "Future": "zukünftig",
            "Past": "vergangen",
            "Unknown": "unbekannt",
        }
        return urgency_map.get(raw, raw.lower() if raw else "unbekannt")
