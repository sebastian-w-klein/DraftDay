from dataclasses import dataclass

from app.models.entities import ParserType, SourceType


@dataclass
class SourceRegistryRecord:
    source_id: str
    source_name: str
    base_url: str
    source_type: SourceType
    parser_type: ParserType
    allowed_for_automation: bool
    paywalled: bool
    default_weight: float
    recency_half_life_days: int
    national_or_team_specific: str
    active: bool
    notes: str = ""


SOURCE_REGISTRY: dict[str, SourceRegistryRecord] = {}


def register_source(record: SourceRegistryRecord) -> None:
    SOURCE_REGISTRY[record.source_id] = record


def list_active_sources() -> list[SourceRegistryRecord]:
    return [source for source in SOURCE_REGISTRY.values() if source.active]
