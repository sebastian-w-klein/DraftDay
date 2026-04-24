from app.models.entities import ParserType
from app.parsers.base import BaseSourceParser
from app.parsers.dynamic_html import GenericDynamicHtmlParser
from app.parsers.source_configs import SOURCE_PARSER_CONFIGS
from app.parsers.static_html import GenericStaticHtmlParser


def build_parser(source_slug: str, parser_type: ParserType, base_url: str) -> BaseSourceParser:
    cfg = SOURCE_PARSER_CONFIGS.get(source_slug)
    if parser_type == ParserType.html_static:
        return GenericStaticHtmlParser(
            source_slug=source_slug,
            list_url=cfg.discovery_url if cfg and cfg.discovery_url else base_url,
            article_link_keyword=cfg.article_link_keyword if cfg else "mock-draft",
            pick_row_selectors=cfg.pick_row_selectors if cfg else ("table tr",),
            pick_cell_selector=cfg.pick_cell_selector if cfg else "th,td",
            title_selectors=cfg.title_selectors if cfg else ("h1",),
            author_selectors=cfg.author_selectors if cfg else ("meta[name='author']", ".author"),
            published_at_selectors=cfg.published_at_selectors if cfg else ("time[datetime]",),
            updated_at_selectors=cfg.updated_at_selectors if cfg else ("time[datetime]",),
            body_selectors=cfg.body_selectors if cfg else ("article", "body"),
            date_patterns=cfg.date_patterns if cfg else (r"(20\d{2}-\d{2}-\d{2})",),
        )
    if parser_type == ParserType.html_dynamic:
        return GenericDynamicHtmlParser(source_slug=source_slug)
    raise ValueError(f"Unsupported parser type: {parser_type}")
