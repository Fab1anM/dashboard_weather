import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from dashboard_weather.config import Settings
from dashboard_weather.models import DipulNewsItem

NEWS_LINK_PATTERN = re.compile(r"/homepage/de/aktuelle-meldungen/[^/]+/?$")
DATE_PATTERN = re.compile(r"\d{2}/\d{2}/\d{4}")


class DipulNewsClient:
    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def fetch(self, limit: int = 5) -> list[DipulNewsItem]:
        response = await self._client.get(self._settings.dipul_news_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        items: list[DipulNewsItem] = []
        seen_urls: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            href = anchor["href"]
            slug = href.rstrip("/").split("/")[-1]
            if slug == "aktuelle-meldungen" or not NEWS_LINK_PATTERN.search(href):
                continue

            url = urljoin(self._settings.dipul_news_url, href)
            if url in seen_urls:
                continue

            container = anchor.find_parent(["article", "div", "li"]) or anchor.parent
            title = self._extract_title(container)
            if not title:
                continue

            summary = self._extract_summary(container)
            date_text = self._extract_date(container)

            seen_urls.add(url)
            items.append(
                DipulNewsItem(
                    title=title,
                    date=date_text,
                    summary=summary,
                    url=url,
                )
            )
            if len(items) >= limit:
                break

        return items

    @staticmethod
    def _extract_title(container) -> str:
        time_tag = container.find("time")
        if time_tag:
            sibling = time_tag.find_next("span")
            if sibling:
                return sibling.get_text(" ", strip=True)[:180]

        for heading in container.find_all(["h2", "h3", "h4"]):
            text = heading.get_text(" ", strip=True)
            if text:
                return text[:180]
        return ""

    @staticmethod
    def _extract_summary(container) -> str:
        for paragraph in container.find_all("p"):
            text = paragraph.get_text(" ", strip=True)
            if text and not DATE_PATTERN.fullmatch(text):
                return text[:240]
        return ""

    @staticmethod
    def _extract_date(container) -> str:
        time_tag = container.find("time")
        if time_tag:
            return time_tag.get_text(" ", strip=True)
        match = DATE_PATTERN.search(container.get_text(" ", strip=True))
        return match.group(0) if match else ""
