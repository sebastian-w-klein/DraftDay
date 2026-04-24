from decimal import Decimal
import sys
from pathlib import Path

from sqlalchemy import select

# Support running as `python scripts/seed_sources.py` in containers.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.entities import Source
from app.parsers.source_configs import SOURCE_PARSER_CONFIGS


def main() -> None:
    with SessionLocal() as db:
        for cfg in SOURCE_PARSER_CONFIGS.values():
            source = db.scalar(select(Source).where(Source.slug == cfg.slug))
            if source is None:
                source = Source(
                    slug=cfg.slug,
                    name=cfg.name,
                    base_url=cfg.base_url,
                    source_type=cfg.source_type,
                    parser_type=cfg.parser_type,
                    allowed_for_automation=cfg.allowed_for_automation,
                    paywalled=cfg.paywalled,
                    default_weight=Decimal(str(cfg.default_weight)),
                    recency_half_life_days=cfg.recency_half_life_days,
                    active=cfg.active,
                )
                db.add(source)
            else:
                source.name = cfg.name
                source.base_url = cfg.base_url
                source.source_type = cfg.source_type
                source.parser_type = cfg.parser_type
                source.allowed_for_automation = cfg.allowed_for_automation
                source.paywalled = cfg.paywalled
                source.default_weight = Decimal(str(cfg.default_weight))
                source.recency_half_life_days = cfg.recency_half_life_days
                source.active = cfg.active
        db.commit()
    print("Seeded source configuration rows.")


if __name__ == "__main__":
    main()
