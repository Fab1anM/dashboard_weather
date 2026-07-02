"""Ad-hoc verification: README reflects all architecture changes."""

from pathlib import Path


def test_readme_has_weather_cache_feature():
    """README features table should mention 12h cache for weather."""
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text()
    assert "12h Cache)" in content, "Features should mention 12h cache for weather data"


def test_readme_has_individual_clients_architecture():
    """README architecture diagram should show individual clients."""
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text()
    assert "Individual Clients" in content, "Architecture should mention individual clients"
    assert "no shared connection pool" in content, "Should explain no shared connection pool"


def test_readme_has_isolation_section():
    """README should have dedicated isolation architecture section."""
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text()
    assert "Isolierte Datenquellen-Architektur" in content, "Should have isolation section"
    assert "Kein Kaskadierender Ausfall" in content, "Should mention no cascade failure"
    assert (
        "Jeder Datenquellen-Client verwendet einen **eigenen httpx.AsyncClient**" in content
    ), "Should explain individual clients"


def test_readme_has_weather_cache_ttl_config():
    """README config table should include DASHBOARD_WEATHER_CACHE_TTL."""
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text()
    assert "DASHBOARD_WEATHER_CACHE_TTL" in content, "Should document weather cache TTL"
    assert "43200" in content, "Should show 43200 seconds value"


def test_readme_has_parallel_fetch_description():
    """README should describe 2-step fetch pattern."""
    readme = Path(__file__).resolve().parent.parent / "README.md"
    content = readme.read_text()
    assert "Alle anderen Quellen parallel" in content, "Should describe parallel fetch"
    assert "Wetter (12h Cache)" in content, "Should describe weather 12h cache step"
