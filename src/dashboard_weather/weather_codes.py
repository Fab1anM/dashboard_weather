WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Klarer Himmel",
    1: "Meist klar",
    2: "Teilweise bewölkt",
    3: "Bewölkt",
    45: "Nebel",
    48: "Reifnebel",
    51: "Leichter Nieseln",
    53: "Mäßiges Nieseln",
    55: "Dichtes Nieseln",
    61: "Leichter Regen",
    63: "Mäßiger Regen",
    65: "Starker Regen",
    71: "Leichter Schneefall",
    73: "Mäßiger Schneefall",
    75: "Starker Schneefall",
    80: "Leichte Regenschauer",
    81: "Mäßige Regenschauer",
    82: "Starke Regenschauer",
    95: "Gewitter",
    96: "Gewitter mit leichtem Hagel",
    99: "Gewitter mit starkem Hagel",
    200: "Gewitter mit Hagel",
}


def describe_weather_code(code: int) -> str:
    return WMO_DESCRIPTIONS.get(code, "Unbekannte Bedingungen")
