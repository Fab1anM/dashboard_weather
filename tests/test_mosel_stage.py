"""Tests for the Mosel Stage Client (hochwasser.rlp.de API)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from dashboard_weather.clients.mosel_stage import MoselStageClient
from dashboard_weather.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def mock_httpx_client() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def client(settings: Settings, mock_httpx_client: AsyncMock) -> MoselStageClient:
    return MoselStageClient(settings, mock_httpx_client)


class TestMoselStageClientFetch:
    """Tests for MoselStageClient.fetch()."""

    @pytest.mark.anyio
    async def test_fetch_returns_data_on_success(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """When the API returns valid data, fetch() should return MoselStageData."""
        # Use MagicMock for response — httpx.Response.json() is synchronous
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "W": {
                "xLast": "2026-06-30T06:15:00Z",
                "yLast": 237,
                "legendColor": "#f0f0f0",
                "measurements": [
                    {"y": 240, "x": "2026-06-30T06:00:00Z"},
                    {"y": 238, "x": "2026-06-30T06:05:00Z"},
                    {"y": 237, "x": "2026-06-30T06:15:00Z"},
                ],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 235},
                        {"x": "2026-07-01T01:00:00Z", "y": 233},
                        {"x": "2026-07-01T02:00:00Z", "y": 232},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {
                "xLast": "",
                "yLast": 0,
                "legendColor": "",
                "measurements": [],
                "predictions": {},
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 0,
            },
            "hint": {"type": "info", "text": "Stauregulierung aktiv", "updatedAt": ""},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await client.fetch()

        assert result is not None
        assert result.station == "Trier / Mosel"
        assert abs(result.current_stage_m - 2.37) < 0.001
        assert result.trend == "fallend"
        assert len(result.forecast) == 3
        assert result.forecast[0].hour == "2026-07-01T00:00:00Z"
        assert result.description == "Stauregulierung aktiv"

    @pytest.mark.anyio
    async def test_fetch_returns_none_on_http_error(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """When both httpx and requests fail, fetch() should return None."""
        from unittest.mock import patch

        mock_httpx_client.get.side_effect = Exception("Connection refused")

        with patch.object(
            MoselStageClient, "_fetch_with_requests", return_value=None
        ):
            with patch.object(
                client, "_fetch_from_html", return_value=None
            ):
                result = await client.fetch()

        assert result is None

    @pytest.mark.anyio
    async def test_fetch_returns_none_on_no_w_data(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """When the API returns no W (water level) data, fetch() should return None."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"Q": {}, "hint": {}}
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await client.fetch()

        assert result is None

    @pytest.mark.anyio
    async def test_fetch_skips_null_measurements(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """Measurements with null y values should be skipped."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 200,
                "legendColor": "",
                "measurements": [
                    {"y": None, "x": "2026-06-30T05:50:00Z"},
                    {"y": 200, "x": "2026-06-30T06:00:00Z"},
                ],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {},
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.get.return_value = mock_response

        result = await client.fetch()

        assert result is not None
        assert len(result.forecast) == 0
        assert abs(result.current_stage_m - 2.0) < 0.001


class TestMoselStageClientParseResponse:
    """Tests for MoselStageClient._parse_response()."""

    def test_parse_response_basic(self):
        """Basic parsing should convert cm to m and extract all fields."""
        data = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 250,
                "legendColor": "",
                "measurements": [{"y": 250, "x": "2026-06-30T06:00:00Z"}],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 255},
                        {"x": "2026-07-01T01:00:00Z", "y": 258},
                        {"x": "2026-07-01T02:00:00Z", "y": 262},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {},
        }

        result = MoselStageClient._parse_response(data)

        assert result is not None
        assert result.station == "Trier / Mosel"
        assert abs(result.current_stage_m - 2.50) < 0.001
        assert result.trend == "steigend"
        assert result.threshold_warning_m == 5.0
        assert result.threshold_high_m == 6.0

    def test_parse_response_trend_falling(self):
        """Predictions showing a decline should set trend to 'fallend'."""
        data = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 500,
                "legendColor": "",
                "measurements": [{"y": 500, "x": "2026-06-30T06:00:00Z"}],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 500},
                        {"x": "2026-07-01T01:00:00Z", "y": 498},
                        {"x": "2026-07-01T02:00:00Z", "y": 495},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 600,
            },
            "Q": {},
            "hint": {},
        }

        result = MoselStageClient._parse_response(data)

        assert result.trend == "fallend"

    def test_parse_response_trend_constant(self):
        """Predictions showing little change should set trend to 'gleichbleibend'."""
        data = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 300,
                "legendColor": "",
                "measurements": [{"y": 300, "x": "2026-06-30T06:00:00Z"}],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 300},
                        {"x": "2026-07-01T01:00:00Z", "y": 300},
                        {"x": "2026-07-01T02:00:00Z", "y": 300},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {},
        }

        result = MoselStageClient._parse_response(data)

        assert result.trend == "gleichbleibend"

    def test_parse_response_no_predictions(self):
        """No predictions should result in no forecast entries."""
        data = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 200,
                "legendColor": "",
                "measurements": [{"y": 200, "x": "2026-06-30T06:00:00Z"}],
                "predictions": {},
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {},
        }

        result = MoselStageClient._parse_response(data)

        assert result is not None
        assert len(result.forecast) == 0
        assert result.trend == "gleichbleibend"

    def test_parse_response_empty_measurements(self):
        """No measurements should result in current_stage_m of 0."""
        data = {
            "W": {
                "xLast": "",
                "yLast": 0,
                "legendColor": "",
                "measurements": [],
                "predictions": {},
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 0,
            },
            "Q": {},
            "hint": {},
        }

        result = MoselStageClient._parse_response(data)

        assert result is not None
        assert result.current_stage_m == 0.0
        assert result.timestamp is None


class TestMoselStageClientRequestsFallback:
    """Tests for MoselStageClient._fetch_with_requests() and HTTP fallback chain."""

    def test_fetch_with_requests_success(self):
        """When requests can reach the API, it should return parsed data."""
        from unittest.mock import MagicMock, patch

        # Mock requests.get to return valid API data
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "W": {
                "xLast": "2026-06-30T06:00:00Z",
                "yLast": 245,
                "legendColor": "",
                "measurements": [{"y": 245, "x": "2026-06-30T06:00:00Z"}],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 250},
                        {"x": "2026-07-01T01:00:00Z", "y": 255},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {"type": "info", "text": "Test hint", "updatedAt": ""},
        }
        mock_response.raise_for_status = MagicMock()

        from dashboard_weather.clients.mosel_stage import MoselStageClient

        with patch(
            "dashboard_weather.clients.mosel_stage.requests.get",
            return_value=mock_response,
        ):
            result = MoselStageClient._fetch_with_requests(
                "https://www.hochwasser.rlp.de/api/v1/measurement-site/26500100"
            )

        assert result is not None
        assert result["W"]["yLast"] == 245

    def test_fetch_with_requests_timeout(self):
        """When requests times out, it should return None."""
        import requests

        from dashboard_weather.clients.mosel_stage import MoselStageClient

        # Mock requests.get to raise a timeout
        with __import__("unittest.mock").mock.patch.object(
            requests, "get", side_effect=requests.exceptions.Timeout("Connection timed out")
        ):
            result = MoselStageClient._fetch_with_requests(
                "https://www.hochwasser.rlp.de/api/v1/measurement-site/26500100"
            )
            assert result is None

    @pytest.mark.anyio
    async def test_fetch_httpx_fails_requests_succeeds(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """When httpx fails but requests succeeds, fetch() should use requests."""
        from unittest.mock import MagicMock, patch

        # Make httpx fail
        mock_httpx_client.get.side_effect = Exception("Connection refused")

        # Mock requests.get to return valid data
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "W": {
                "xLast": "2026-06-30T07:00:00Z",
                "yLast": 250,
                "legendColor": "",
                "measurements": [{"y": 250, "x": "2026-06-30T07:00:00Z"}],
                "predictions": {
                    "p10": [],
                    "p20": [],
                    "p30": [],
                    "p40": [],
                    "p50": [
                        {"x": "2026-07-01T00:00:00Z", "y": 255},
                        {"x": "2026-07-01T01:00:00Z", "y": 260},
                    ],
                    "p60": [],
                    "p70": [],
                    "p80": [],
                    "p90": [],
                    "time": "",
                    "nextUpdateTime": "",
                },
                "xMin": "",
                "xMax": "",
                "yMin": 0,
                "yMax": 300,
            },
            "Q": {},
            "hint": {"type": "info", "text": "Stauregulierung", "updatedAt": ""},
        }
        mock_response.raise_for_status = MagicMock()

        with patch(
            "dashboard_weather.clients.mosel_stage.requests.get",
            return_value=mock_response,
        ):
            result = await client.fetch()

        assert result is not None
        assert result.station == "Trier / Mosel"
        assert abs(result.current_stage_m - 2.50) < 0.001
        assert len(result.forecast) == 2
        assert result.trend == "steigend"
        assert result.description == "Stauregulierung"

    @pytest.mark.anyio
    async def test_fetch_httpx_fails_requests_fails_html_fallback(
        self, client: MoselStageClient, mock_httpx_client: AsyncMock
    ):
        """When both httpx and requests fail, it should fall back to HTML parsing."""
        from unittest.mock import patch

        # Make httpx fail
        mock_httpx_client.get.side_effect = Exception("Connection refused")

        # Make requests also fail
        from dashboard_weather.clients.mosel_stage import MoselStageClient

        with patch.object(
            MoselStageClient, "_fetch_with_requests", return_value=None
        ):
            # Mock the HTML fallback to return None (no data)
            with patch.object(
                client, "_fetch_from_html", return_value=None
            ):
                result = await client.fetch()

        assert result is None
