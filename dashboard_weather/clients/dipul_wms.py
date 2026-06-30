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
            delta=0.15,
        )

        params = {
            "service": "WMS",
            "version": "1.3.0",
            "request": "GetFeatureInfo",
            "layers": ",".join(layers),
            "query_layers": ",".join(layers),
            "info_format": "text/html",
            "i": 100,
            "j": 100,
            "width": 201,
            "height": 201,
            "crs": "EPSG:4326",
            "bbox": bbox,
        }

        # Query multiple points across the area to catch spatial restrictions
        query_points = self._generate_query_points(bbox, grid_size=5)
        all_restrictions: dict[str, AirspaceRestriction] = {}

        for x, y in query_points:
            query_params = {**params, "i": str(x), "j": str(y)}
            try:
                response = await self._client.get(self._settings.dipul_wms_url, params=query_params)
                if response.status_code != 200:
                    continue
                restrictions = self._parse_response(response.text)
                for r in restrictions:
                    # Deduplicate by title
                    key = r.details.get("title", r.details.get("Name", ""))
                    if key and key not in all_restrictions:
                        all_restrictions[key] = r
            except Exception:
                continue

        return list(all_restrictions.values())

    def _generate_query_points(self, bbox: str, grid_size: int = 5) -> list[tuple[int, int]]:
        """Generate a grid of query points across the bbox."""
        min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(","))
        step_lon = (max_lon - min_lon) / (grid_size - 1) if grid_size > 1 else 0
        step_lat = (max_lat - min_lat) / (grid_size - 1) if grid_size > 1 else 0

        points: list[tuple[int, int]] = []
        for i in range(grid_size):
            for j in range(grid_size):
                lon = min_lon + i * step_lon
                lat = min_lat + j * step_lat
                # Convert lon/lat to pixel coords (201x201 canvas)
                x = round((lon - min_lon) / (max_lon - min_lon) * 200)
                y = round((max_lat - lat) / (max_lat - min_lat) * 200)
                x = max(0, min(200, x))
                y = max(0, min(200, y))
                points.append((x, y))
        return points

    @staticmethod
    def _parse_response(html: str) -> list[AirspaceRestriction]:
        """Parse HTML response and extract restrictions."""
        parser = _FeatureInfoParser()
        parser.feed(html)
        if not parser.rows:
            return []

        details = {key: value for key, value in parser.rows if value}
        if not details:
            return []

        layer_hint = details.get("layer", details.get("Layer", "unknown"))
        layers = list(LAYER_CATALOG.keys())
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
