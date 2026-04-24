from datetime import datetime

from playwright.async_api import async_playwright

from app.parsers.base import BaseSourceParser
from app.schemas.parsed import ParsedMockDraft


class GenericDynamicHtmlParser(BaseSourceParser):
    def __init__(self, source_slug: str):
        self.source_slug = source_slug

    async def discover(self) -> list[str]:
        return []

    async def fetch(self, url: str) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            html = await page.content()
            await browser.close()
            return html

    def parse_metadata(self, payload: str, url: str) -> dict[str, object]:
        return {
            "source_slug": self.source_slug,
            "article_url": url,
            "title": url,
            "author_name": None,
            "published_at": None,
            "updated_at": None,
            "draft_year": datetime.utcnow().year,
        }

    def parse_picks(self, payload: str) -> list[dict[str, object]]:
        return []

    def validate(self, parsed: ParsedMockDraft) -> None:
        if not parsed.picks:
            raise ValueError("No picks parsed from dynamic page")
