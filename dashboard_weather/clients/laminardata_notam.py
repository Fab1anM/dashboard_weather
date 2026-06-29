"""Laminar Data NOTAM API client — Cirium Laminar Data Hub (v2).

Provides NOTAM data for drone pilots operating around Trier, Germany.
Queries NOTAMs for nearby aerodromes and the Munich FIR (EDGG).
"""

from __future__ import annotations

import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import LaminarNotam


# Aerodromes near Trier that matter for drone operations
_NEARBY_AERODROMES: list[str] = [
    "EDGT",  # Trier-Föhren (closest, drone-relevant)
    "EDSB",  # Bitburg
    "EDFR",  # Frankfurt-Hahn
]

# FIR covering Trier / Germany
_FIR_icao: str = "EDGG"  # Munich FIR (covers all Germany)


class LaminarNotamClient:
    """Client for the Cirium Laminar Data NOTAM API v2."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client
        # API key from environment variable
        self._api_key = settings.laminar_notam_api_key or ""

    async def fetch_notams(self) -> list[LaminarNotam]:
        """Fetch NOTAMs for Trier area from Laminar Data API.

        Queries:
        1. NOTAMs for nearby aerodromes (EDGT, EDSB, EDFR)
        2. NOTAMs for the Munich FIR (EDGG) which covers all of Germany

        Returns a deduplicated list of LaminarNotam objects.
        """
        if not self._api_key:
            return [
                LaminarNotam(
                    notam_id="INFO",
                    text="NOTAM-Daten sind aktuell nicht verfügbar. Um Echtzeit-Fluginformationen für den Drohnenbetrieb zu erhalten, registriere dich unter https://developer.laminardata.aero/signup und trage den API-Key in die Umgebungsvariable LAMINAR_NOTAM_API_KEY ein.",
                    aerodrome_icao=None,
                    q_code=None,
                )
            ]

        headers = {
            "X-UserKey": self._api_key,
            "Accept-Encoding": "gzip",
        }

        all_notams: dict[str, LaminarNotam] = {}

        # Query aerodrome-specific NOTAMs
        for icao in _NEARBY_AERODROMES:
            try:
                notams = await self._fetch_aerodrome_notams(icao, headers)
                for n in notams:
                    key = n.notam_id
                    if key and key not in all_notams:
                        all_notams[key] = n
            except Exception:  # noqa: BLE001 — degrade gracefully
                continue

        # Query FIR-wide NOTAMs (Germany-wide)
        try:
            fir_notams = await self._fetch_fir_notams(_FIR_icao, headers)
            for n in fir_notams:
                key = n.notam_id
                if key and key not in all_notams:
                    all_notams[key] = n
        except Exception:  # noqa: BLE001 — degrade gracefully
            pass

        return list(all_notams.values())

    async def _fetch_aerodrome_notams(
        self, icao: str, headers: dict[str, str]
    ) -> list[LaminarNotam]:
        """Fetch NOTAMs for a specific aerodrome."""
        url = f"https://api.laminardata.aero/notamdata/v2/aerodromes/{icao}/notams"
        response = await self._client.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return self._parse_notams(response.json())

    async def _fetch_fir_notams(
        self, fir_icao: str, headers: dict[str, str]
    ) -> list[LaminarNotam]:
        """Fetch NOTAMs for a specific Flight Information Region."""
        url = f"https://api.laminardata.aero/notamdata/v2/icao-prefixes/ED/firs/{fir_icao}/notams"
        response = await self._client.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        return self._parse_notams(response.json())

    @staticmethod
    def _parse_notams(data: dict) -> list[LaminarNotam]:
        """Parse JSON response from the Laminar Data API into LaminarNotam objects.

        The NOTAM API v2 response structure varies; we handle the most common patterns.
        """
        notams: list[LaminarNotam] = []

        # The response can be a list of notam objects or a dict with a "notams" key
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Try common keys
            items = data.get("notams") or data.get("results") or []
            if isinstance(items, dict):
                # Nested structure — try deeper
                items = items.get("notams") or []
        else:
            return []

        for item in items:
            if not isinstance(item, dict):
                continue

            notam_id = item.get("notamId") or item.get("id") or item.get("notamNumber") or ""
            text = item.get("text", "") or item.get("rawNotamText", "")

            if not text and notam_id:
                # Use notamId as fallback text if no message text
                text = f"NOTAM {notam_id}"

            aerodrome_icao = item.get("aerodromeIcao") or item.get("aerodrome")
            fir_icao = item.get("firIcao") or item.get("fir")
            issued_at = item.get("issuedAt") or item.get("issuedDate")
            valid_from = item.get("validFrom") or item.get("startTime") or item.get("effectiveFrom")
            valid_to = item.get("validTo") or item.get("endTime") or item.get("effectiveTo")
            q_code = item.get("qCode") or item.get("qCodeLine")

            notams.append(
                LaminarNotam(
                    notam_id=notam_id,
                    text=text,
                    aerodrome_icao=aerodrome_icao,
                    fir_icao=fir_icao,
                    issued_at=issued_at,
                    valid_from=valid_from,
                    valid_to=valid_to,
                    q_code=q_code,
                )
            )

        return notams
