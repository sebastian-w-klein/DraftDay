import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.parsers.base import BaseSourceParser
from app.schemas.parsed import ParsedMockDraft
from app.services.http_client import fetch_text


class GenericStaticHtmlParser(BaseSourceParser):
    def __init__(
        self,
        source_slug: str,
        list_url: str | None = None,
        article_link_keyword: str = "mock-draft",
        pick_row_selectors: tuple[str, ...] = ("table tr",),
        pick_cell_selector: str = "th,td",
        title_selectors: tuple[str, ...] = ("h1",),
        author_selectors: tuple[str, ...] = ("meta[name='author']", ".author", "[rel='author']"),
        published_at_selectors: tuple[str, ...] = (
            "meta[property='article:published_time']",
            "meta[name='pubdate']",
            "time[datetime]",
        ),
        updated_at_selectors: tuple[str, ...] = (
            "meta[property='article:modified_time']",
            "meta[name='lastmod']",
            "time[datetime]",
        ),
        body_selectors: tuple[str, ...] = ("article", "main", "body"),
        date_patterns: tuple[str, ...] = (r"(20\d{2}-\d{2}-\d{2})",),
        draft_year: int | None = None,
    ):
        self.source_slug = source_slug
        self.list_url = list_url
        self.article_link_keyword = article_link_keyword
        self.pick_row_selectors = pick_row_selectors
        self.pick_cell_selector = pick_cell_selector
        self.title_selectors = title_selectors
        self.author_selectors = author_selectors
        self.published_at_selectors = published_at_selectors
        self.updated_at_selectors = updated_at_selectors
        self.body_selectors = body_selectors
        self.date_patterns = date_patterns
        self.draft_year = draft_year

    async def discover(self) -> list[str]:
        if self.list_url is None:
            return []
        html = await self.fetch(self.list_url)
        soup = BeautifulSoup(html, "html.parser")
        urls: list[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            if self.article_link_keyword in href.lower():
                urls.append(urljoin(self.list_url, href))
        return list(dict.fromkeys(urls))

    async def fetch(self, url: str) -> str:
        return await fetch_text(url)

    def parse_metadata(self, payload: str, url: str) -> dict[str, object]:
        soup = BeautifulSoup(payload, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else url
        heading = _first_matching_text(soup, self.title_selectors) or title
        author = _first_matching_text(soup, self.author_selectors)
        published_at = _first_matching_datetime(soup, self.published_at_selectors, self.date_patterns)
        updated_at = _first_matching_datetime(soup, self.updated_at_selectors, self.date_patterns)
        inferred_year = _infer_draft_year_from_text(heading, self.date_patterns)
        return {
            "source_slug": self.source_slug,
            "article_url": url,
            "title": heading,
            "author_name": author,
            "published_at": published_at,
            "updated_at": updated_at,
            "draft_year": self.draft_year or inferred_year or datetime.utcnow().year,
        }

    def parse_picks(self, payload: str) -> list[dict[str, object]]:
        soup = BeautifulSoup(payload, "html.parser")
        for strategy in (_parse_table_picks, _parse_list_picks, _parse_text_picks):
            picks = strategy(
                soup=soup,
                pick_row_selectors=self.pick_row_selectors,
                pick_cell_selector=self.pick_cell_selector,
                body_selectors=self.body_selectors,
            )
            if picks:
                return picks
        return []

    def validate(self, parsed: ParsedMockDraft) -> None:
        if not parsed.picks:
            raise ValueError("No picks extracted")
        if any(p.overall_pick <= 0 for p in parsed.picks):
            raise ValueError("Invalid pick number found")


def _split_player_blob(player_text: str) -> tuple[str, str | None, str | None]:
    bits = [segment.strip() for segment in re.split(r"[-,|]", player_text) if segment.strip()]
    if len(bits) >= 3:
        return bits[0], bits[1], bits[2]
    if len(bits) == 2:
        return bits[0], bits[1], None
    return player_text, None, None


def _first_matching_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str | None:
    for selector in selectors:
        node = soup.select_one(selector)
        if node is None:
            continue
        if node.name == "meta":
            value = node.get("content")
            if value:
                return value.strip()
        text = node.get_text(strip=True)
        if text:
            return text
    return None


def _first_matching_datetime(
    soup: BeautifulSoup, selectors: tuple[str, ...], date_patterns: tuple[str, ...]
) -> datetime | None:
    raw = _first_matching_text(soup, selectors)
    if raw is None:
        return None
    parsed = _parse_datetime(raw)
    if parsed is not None:
        return parsed
    for pattern in date_patterns:
        match = re.search(pattern, raw)
        if match:
            parsed = _parse_datetime(match.group(1))
            if parsed is not None:
                return parsed
    return None


def _parse_datetime(raw: str) -> datetime | None:
    candidate = raw.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _infer_draft_year_from_text(text: str, date_patterns: tuple[str, ...]) -> int | None:
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match:
        return int(year_match.group(1))
    for pattern in date_patterns:
        date_match = re.search(pattern, text)
        if date_match:
            parsed = _parse_datetime(date_match.group(1))
            if parsed is not None:
                return parsed.year
    return None


def _parse_table_picks(
    soup: BeautifulSoup,
    pick_row_selectors: tuple[str, ...],
    pick_cell_selector: str,
    body_selectors: tuple[str, ...],
) -> list[dict[str, object]]:
    picks: list[dict[str, object]] = []
    for row_selector in pick_row_selectors:
        for row in soup.select(row_selector):
            cells = [c.get_text(strip=True) for c in row.select(pick_cell_selector)]
            if len(cells) < 3:
                continue
            if not cells[0].isdigit():
                continue
            overall_pick = int(cells[0])
            team = cells[1]
            player_name, position, school = _split_player_blob(cells[2])
            picks.append(_pick_payload(overall_pick, team, player_name, position, school))
        if picks:
            return picks
    return picks


def _parse_list_picks(
    soup: BeautifulSoup,
    pick_row_selectors: tuple[str, ...],
    pick_cell_selector: str,
    body_selectors: tuple[str, ...],
) -> list[dict[str, object]]:
    picks: list[dict[str, object]] = []
    selectors = ("ol li", "ul li")
    for selector in selectors:
        for node in soup.select(selector):
            text = node.get_text(" ", strip=True)
            parsed = _extract_pick_line(text)
            if parsed is None:
                continue
            overall_pick, team, player, position, school = parsed
            picks.append(_pick_payload(overall_pick, team, player, position, school))
        if len(picks) >= 8:
            return picks
    return []


def _parse_text_picks(
    soup: BeautifulSoup,
    pick_row_selectors: tuple[str, ...],
    pick_cell_selector: str,
    body_selectors: tuple[str, ...],
) -> list[dict[str, object]]:
    picks: list[dict[str, object]] = []
    bodies = []
    for selector in body_selectors:
        bodies = soup.select(selector)
        if bodies:
            break
    if not bodies:
        return []

    for body in bodies:
        text = body.get_text("\n", strip=True)
        for line in text.splitlines():
            parsed = _extract_pick_line(line.strip())
            if parsed is None:
                continue
            overall_pick, team, player, position, school = parsed
            picks.append(_pick_payload(overall_pick, team, player, position, school))
        if len(picks) >= 8:
            return picks
    return []


def _extract_pick_line(line: str) -> tuple[int, str, str, str | None, str | None] | None:
    line_match = re.match(
        r"^\s*(\d{1,2})[\.\):\-]?\s+([A-Za-z .&'-]+)\s*[-:]\s*([A-Za-z .'-]+)(?:,\s*([A-Za-z/]+))?(?:,\s*([A-Za-z .&'-]+))?\s*$",
        line,
    )
    if line_match is None:
        return None
    overall_pick = int(line_match.group(1))
    team = line_match.group(2).strip()
    player = line_match.group(3).strip()
    position = line_match.group(4).strip() if line_match.group(4) else None
    school = line_match.group(5).strip() if line_match.group(5) else None
    return overall_pick, team, player, position, school


def _pick_payload(
    overall_pick: int,
    team: str,
    player_name: str,
    position: str | None,
    school: str | None,
) -> dict[str, object]:
    return {
        "round_number": 1,
        "overall_pick": overall_pick,
        "original_team": team,
        "current_team": team,
        "traded": False,
        "player_name": player_name,
        "position": position,
        "school": school,
    }
