from dataclasses import dataclass

from app.models.entities import ParserType, SourceType


@dataclass(frozen=True)
class ParserConfig:
    slug: str
    name: str
    base_url: str
    source_type: SourceType
    parser_type: ParserType
    allowed_for_automation: bool
    paywalled: bool
    default_weight: float
    recency_half_life_days: int
    active: bool
    discovery_url: str | None = None
    article_link_keyword: str = "mock-draft"
    pick_row_selectors: tuple[str, ...] = ("table tr",)
    pick_cell_selector: str = "th,td"
    title_selectors: tuple[str, ...] = ("h1",)
    author_selectors: tuple[str, ...] = ("meta[name='author']", ".author", "[rel='author']")
    published_at_selectors: tuple[str, ...] = (
        "meta[property='article:published_time']",
        "meta[name='pubdate']",
        "time[datetime]",
    )
    updated_at_selectors: tuple[str, ...] = (
        "meta[property='article:modified_time']",
        "meta[name='lastmod']",
        "time[datetime]",
    )
    body_selectors: tuple[str, ...] = ("article", "main", "body")
    date_patterns: tuple[str, ...] = (r"(20\d{2}-\d{2}-\d{2})", r"([A-Z][a-z]{2,8}\s+\d{1,2},\s+20\d{2})")


SOURCE_PARSER_CONFIGS: dict[str, ParserConfig] = {
    "nfl-com": ParserConfig(
        slug="nfl-com",
        name="NFL.com",
        base_url="https://www.nfl.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.15,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.nfl.com/news/",
        article_link_keyword="mock-draft",
        pick_row_selectors=("table tr", ".nfl-c-listicle__item"),
        title_selectors=("h1", ".nfl-c-article__title"),
        author_selectors=("meta[name='author']", ".nfl-c-author__name"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", ".nfl-c-article__body", "main"),
    ),
    "espn": ParserConfig(
        slug="espn",
        name="ESPN",
        base_url="https://www.espn.com/nfl/draft",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.1,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.espn.com/nfl/draft/",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".headline"),
        author_selectors=("meta[name='author']", ".author-name"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", ".article-body", "main"),
    ),
    "cbssports": ParserConfig(
        slug="cbssports",
        name="CBS Sports",
        base_url="https://www.cbssports.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.08,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.cbssports.com/nfl/draft/news/",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".Article-headline", "[data-testid='headline']"),
        author_selectors=("meta[name='author']", ".Author-name", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main", ".Article-body"),
    ),
    "yahoo": ParserConfig(
        slug="yahoo",
        name="Yahoo Sports",
        base_url="https://sports.yahoo.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.0,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://sports.yahoo.com/nfl/draft/",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", "[data-test-locator='headline']"),
        author_selectors=("meta[name='author']", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main", "[role='article']"),
    ),
    "pfn": ParserConfig(
        slug="pfn",
        name="Pro Football Network",
        base_url="https://www.profootballnetwork.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.05,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.profootballnetwork.com/nfl/draft/",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".entry-title", "article header h1"),
        author_selectors=("meta[name='author']", ".author-name", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main", ".entry-content"),
    ),
    "si-com": ParserConfig(
        slug="si-com",
        name="Sports Illustrated",
        base_url="https://www.si.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.02,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.si.com/nfl/draft",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".headline", "[data-module='ArticleHeader'] h1"),
        author_selectors=("meta[name='author']", ".author-name", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main", ".article-body"),
    ),
    "fantasypros": ParserConfig(
        slug="fantasypros",
        name="FantasyPros",
        base_url="https://www.fantasypros.com",
        source_type=SourceType.aggregator,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=0.98,
        recency_half_life_days=7,
        active=True,
        discovery_url="https://www.fantasypros.com/nfl/",
        article_link_keyword="mock-draft",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".article-title"),
        author_selectors=("meta[name='author']", ".author", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main", ".article-content"),
    ),
    "sporting-news": ParserConfig(
        slug="sporting-news",
        name="Sporting News",
        base_url="https://www.sportingnews.com",
        source_type=SourceType.expert,
        parser_type=ParserType.html_static,
        allowed_for_automation=True,
        paywalled=False,
        default_weight=1.0,
        recency_half_life_days=10,
        active=True,
        discovery_url="https://www.sportingnews.com/us/nfl",
        article_link_keyword="mock",
        pick_row_selectors=("table tr", "ol li", "article p"),
        title_selectors=("h1", ".headline"),
        author_selectors=("meta[name='author']", ".author", "[rel='author']"),
        published_at_selectors=("meta[property='article:published_time']", "time[datetime]"),
        updated_at_selectors=("meta[property='article:modified_time']", "time[datetime]"),
        body_selectors=("article", "main"),
    ),
    "manual": ParserConfig(
        slug="manual",
        name="Manual",
        base_url="manual://local",
        source_type=SourceType.manual,
        parser_type=ParserType.manual_upload,
        allowed_for_automation=False,
        paywalled=False,
        default_weight=1.0,
        recency_half_life_days=14,
        active=True,
    ),
}
