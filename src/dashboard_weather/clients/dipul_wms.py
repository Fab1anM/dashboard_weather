from html.parser import HTMLParser

import httpx

from dashboard_weather.config import Settings
from dashboard_weather.models import AirspaceRestriction

LAYER_CATALOG: dict[str, str] = {
    "temporaere_betriebseinschraenkungen": "Temporary operational restrictions",
    "flughaefen": "Airports",
    "flugplaetze": "Airfields",
    "flugbeschraenkungsgebiete": "Restricted areas (ED-R)",
    "wohngrundstuecke": "Residential properties",
    "naturschutzgebiete": "Nature reserves",
    "vogelschutzgebiete": "Bird protection areas",
    "windkraftanlagen": "Wind turbines",
    "bahnanlagen": "Railway facilities",
    "bundesautobahnen": "Motorways",
}


class _FeatureInfoParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell_index = 0
        self._current_key = ""
        self._current_value = ""
        self._rows: list[tuple[str, str]] = []

    @property
    def rows(self) -> list[tuple[str, str]]:
        return self._rows

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._cell_index = 0
            self._current_key = ""
            self._current_value = ""
        elif self._in_row and tag in {"td", "th"}:
            self._in_cell = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._in_cell:
            value = self._current_value.strip()
            if self._cell_index == 0:
                self._current_key = value
            else:
                self._current_value = value
                if self._current_key:
                    self._rows.append((self._current_key, value))
            self._in_cell = False
            self._cell_index += 1
        elif tag == "tr" and self._in_row:
            self._in_row = False
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_value += data


class DipulWmsClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch_nearby_restrictions(self) -> list[AirspaceRestriction]:
        layers = list(LAYER_CATALOG.keys())
        bbox = self._bbox_around_point(
            self._settings.latitude,
            self._settings.longitude,
            delta=0.01,
        )

        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetFeatureInfo",
            "layers": ",".join(layers),
            "query_layers": ",".join(layers),
            "info_format": "text/html",
            "i": 50,
            "j": 50,
            "width": 101,
            "height": 101,
            "crs": "EPSG:4326",
            "bbox": bbox,
        }
        response = await self._client.get(self._settings.dipul_wms_url, params=params)
        response.raise_for_status()

        parser = _FeatureInfoParser()
        parser.feed(response.text)
        if not parser.rows:
            return []

        details = {key: value for key, value in parser.rows if value}
        layer_hint = details.get("layer", details.get("Layer", "unknown"))
        matched_layer = next(
            (name for name in layers if name in layer_hint.lower()),
            layers[0],
        )
        title = LAYER_CATALOG.get(matched_layer, matched_layer.replace("_", " ").title())
        return [
            AirspaceRestriction(
                layer=matched_layer,
                title=title,
                details=details,
            )
        ]

    @staticmethod
    def _bbox_around_point(latitude: float, longitude: float, delta: float) -> str:
        min_lon = longitude - delta
        max_lon = longitude + delta
        min_lat = latitude - delta
        max_lat = latitude + delta
        return f"{min_lon},{min_lat},{max_lon},{max_lat}"
