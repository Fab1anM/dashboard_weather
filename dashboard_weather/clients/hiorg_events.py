import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import HiOrgEvent

# HiOrg Server API endpoint for events
# This uses the same API that the Event-Exporter Python scripts use
HIORG_API_BASE = "https://hiorg-server.de/api"


class HiOrgEventsClient:
    """Fetches events and appointments from HiOrg-Server."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(self, limit: int = 10) -> list[HiOrgEvent]:
        """Fetch upcoming events from HiOrg-Server.

        Tries multiple endpoints in order:
        1. /api/events.json - Direct event API
        2. /appdata/eventListings.json - Listing endpoint

        Falls back to empty list if API is unavailable.
        """
        events: list[HiOrgEvent] = []

        # Try primary endpoint first
        events = await self._fetch_events()
        if events:
            return events[:limit]

        # Fallback to listing endpoint
        events = await self._fetch_listings()
        return events[:limit]

    async def _fetch_events(self) -> list[HiOrgEvent]:
        """Fetch events from the events API endpoint."""
        url = f"{HIORG_API_BASE}/events.json"
        try:
            resp = await self._client.get(url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, dict):
                return []

            events_data = data.get("data", [])
            if not isinstance(events_data, list):
                return []

            return [
                event for entry in events_data if (event := self._parse_event(entry)) is not None
            ]

        except (httpx.RequestError, httpx.HTTPStatusError):
            return []

    async def _fetch_listings(self) -> list[HiOrgEvent]:
        """Fallback: fetch events from the event listings endpoint."""
        # Try without district filter first
        urls = [
            f"{HIORG_API_BASE}/appdata/eventListings.json",
            # District-specific endpoints as additional fallbacks
            "https://hiorg-server.de/appdata/eventListings/DE/07211.json",
        ]

        for url in urls:
            try:
                resp = await self._client.get(url, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()

                # Handle different response structures
                if isinstance(data, list):
                    return [
                        event for entry in data if (event := self._parse_event(entry)) is not None
                    ]
                elif isinstance(data, dict):
                    events = data.get("events", data.get("data", data.get("items", [])))
                    if isinstance(events, list):
                        return [
                            event
                            for entry in events
                            if (event := self._parse_event(entry)) is not None
                        ]

            except (httpx.RequestError, httpx.HTTPStatusError):
                continue

        return []

    @staticmethod
    def _is_valid_event(entry: dict) -> bool:
        """Check if an entry is a valid event."""
        if not isinstance(entry, dict):
            return False

        # Must have at least a title or ID
        title = entry.get("verbez") or entry.get("title") or entry.get("id")
        return bool(title)

    @staticmethod
    def _parse_event(entry: dict | None) -> HiOrgEvent | None:
        """Parse an event entry from HiOrg-Server API."""
        if not isinstance(entry, dict):
            return None

        # Must have at least verbez (title) or id to be valid
        title = entry.get("verbez") or entry.get("title") or entry.get("id")
        if not title:
            return None

        # Extract title (German field name from HiOrg API)
        title_str = str(title)

        # Extract location
        location = entry.get("verort") or entry.get("location") or ""

        # Extract date as Unix timestamp
        sortdate = entry.get("sortdate")
        if sortdate:
            try:
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(sortdate, tz=timezone.utc)
                start = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError, OSError):
                start = str(sortdate)
        else:
            # Try ISO format date
            start = entry.get("start") or entry.get("date") or ""

        # Extract end time
        end = entry.get("end") or entry.get("enddate") or None
        if end and isinstance(end, (int, float)):
            try:
                from datetime import datetime, timezone

                dt = datetime.fromtimestamp(end, tz=timezone.utc)
                end = dt.strftime("%d.%m.%Y %H:%M")
            except (ValueError, TypeError, OSError):
                end = None

        # Extract description
        description = entry.get("beschreibung") or entry.get("description") or ""

        # Extract category/type
        category = entry.get("kategorie") or entry.get("category") or ""

        return HiOrgEvent(
            title=title_str,
            location=location,
            start=start,
            end=end,
            description=description,
            category=category,
        )
