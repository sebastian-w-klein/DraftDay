import asyncio
from datetime import datetime

from sqlalchemy import select

from app.db.session import SessionLocal
from app.ingestion.service import upsert_mock_draft
from app.models.entities import IngestionJob, ParserType, Source
from app.parsers.factory import build_parser


async def run_ingestion_for_source_id(source_id: int) -> None:
    with SessionLocal() as db:
        source = db.scalar(select(Source).where(Source.id == source_id))
        if source is None:
            return

        job = IngestionJob(source_id=source.id, status="running")
        db.add(job)
        db.commit()
        db.refresh(job)

        errors = 0
        discovered = 0
        parsed_count = 0
        fetched = 0

        try:
            if source.parser_type in (ParserType.manual_upload, ParserType.rss):
                job.status = "skipped"
                job.finished_at = datetime.utcnow()
                db.commit()
                return

            parser = build_parser(
                source_slug=source.slug,
                parser_type=source.parser_type,
                base_url=source.base_url,
            )
            urls = await parser.discover()
            discovered = len(urls)

            for url in urls[:10]:
                try:
                    parsed = await parser.parse_article(url)
                    upsert_mock_draft(db, parsed)
                    parsed_count += 1
                    fetched += 1
                except Exception:
                    errors += 1
                    continue

            job.status = "success" if errors == 0 else ("partial" if parsed_count > 0 else "failed")
        except Exception:
            errors += 1
            job.status = "failed"
        finally:
            job.items_discovered = discovered
            job.items_fetched = fetched
            job.items_parsed = parsed_count
            job.errors_count = errors
            job.finished_at = datetime.utcnow()
            db.commit()


def run_ingestion_for_source_sync(source_id: int) -> None:
    asyncio.run(run_ingestion_for_source_id(source_id))


def run_all_active_ingestion_sync() -> None:
    with SessionLocal() as db:
        source_ids = db.scalars(
            select(Source.id).where(Source.active.is_(True), Source.allowed_for_automation.is_(True))
        ).all()
    for source_id in source_ids:
        run_ingestion_for_source_sync(source_id)
