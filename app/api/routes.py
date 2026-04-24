# ruff: noqa: I001
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.backtest import run_source_backtest
from app.analytics.consensus import pick_consensus, player_landing_spots
from app.board_state import taken_normalized_names
from app.draft_order_context import compute_next_round1_overall_for_team
from app.db.session import get_db
from app.ingestion.draft_order_live import ingest_live_tankathon_draft_order
from app.ingestion.nfl_com_tracker_live import ingest_nfl_com_tracker_picks
from app.ingestion.prospects_live import ingest_live_tankathon_prospects
from app.ingestion.runner import (
    run_all_active_ingestion_sync,
    run_ingestion_for_source_sync,
)
from app.ingestion.service import upsert_mock_draft
from app.ingestion.team_staff_live import ingest_live_team_staff
from app.models.entities import ActualDraftPick, DraftCycle, DraftOrderPick, Source, Team
from app.normalization.normalizers import normalize_player_name
from app.parsers.factory import build_parser
from app.schemas.api import (
    LiveDraftBoardResponse,
    LiveDraftPickRow,
    PickConsensusResponse,
    PlayerLandingSpotsResponse,
)
from app.schemas.ingestion import (
    ActualPickInput,
    BacktestResult,
    DraftOrderIngestionRequest,
    IngestionResponse,
    ManualMockDraftRequest,
    ParseFromUrlRequest,
)
from app.schemas.parsed import ParsedMockDraft

router = APIRouter(prefix="/v1", tags=["draft"])
DB_SESSION = Depends(get_db)


def _consensus_rank_for_actual(
    actual_normalized: str | None,
    consensus: PickConsensusResponse,
    *,
    top_n: int = 8,
) -> int | None:
    if not actual_normalized:
        return None
    for idx, tp in enumerate(consensus.top_players[:top_n]):
        if tp.player_name == actual_normalized:
            return idx + 1
    return 0


@router.get("/consensus/picks/{draft_year}/{overall_pick}", response_model=PickConsensusResponse)
def get_pick_consensus(
    draft_year: int,
    overall_pick: int,
    top_n: int = Query(default=5, ge=1, le=50),
    board_aware: bool = Query(
        default=False,
        description="Exclude mock predictions for players already taken (actual_draft_picks).",
    ),
    db: Session = DB_SESSION,
) -> PickConsensusResponse:
    if overall_pick <= 0:
        raise HTTPException(status_code=400, detail="overall_pick must be > 0")
    taken = (
        taken_normalized_names(db, draft_year, before_overall=overall_pick) if board_aware else None
    )
    return pick_consensus(
        db,
        draft_year=draft_year,
        overall_pick=overall_pick,
        top_n=top_n,
        exclude_taken_normalized=taken,
    )


@router.get(
    "/consensus/players/{draft_year}/{player_name}", response_model=PlayerLandingSpotsResponse
)
def get_player_landing_spots(
    draft_year: int,
    player_name: str,
    top_n: int = Query(default=5, ge=1, le=50),
    context_overall_pick: int | None = Query(
        default=None,
        ge=1,
        le=400,
        description=(
            "Overall pick number for slot-level mock depth (see mock_rows_at_context_pick)."
        ),
    ),
    db: Session = DB_SESSION,
) -> PlayerLandingSpotsResponse:
    return player_landing_spots(
        db,
        draft_year=draft_year,
        player_name=player_name,
        top_n=top_n,
        context_overall_pick=context_overall_pick,
    )


@router.post("/ingestion/manual", response_model=IngestionResponse)
def ingest_manual_mock(
    payload: ManualMockDraftRequest, db: Session = DB_SESSION
) -> IngestionResponse:
    parsed = ParsedMockDraft(
        source_slug=payload.source_slug,
        article_url=(
            str(payload.article_url) if payload.article_url is not None else "manual://entry"
        ),
        title=payload.title,
        author_name=payload.author_name,
        published_at=payload.published_at,
        updated_at=payload.updated_at,
        draft_year=payload.draft_year,
        picks=payload.picks,
    )
    article = upsert_mock_draft(db, parsed)
    return IngestionResponse(
        article_id=article.id, status="success", picks_inserted=len(parsed.picks)
    )


@router.post("/ingestion/parse-url", response_model=IngestionResponse)
async def ingest_from_url(
    payload: ParseFromUrlRequest, db: Session = DB_SESSION
) -> IngestionResponse:
    source = db.scalar(select(Source).where(Source.slug == payload.source_slug))
    if source is None:
        raise HTTPException(status_code=404, detail=f"Unknown source slug: {payload.source_slug}")
    parser = build_parser(
        source_slug=source.slug, parser_type=source.parser_type, base_url=source.base_url
    )
    parsed = await parser.parse_article(str(payload.url))
    article = upsert_mock_draft(db, parsed)
    return IngestionResponse(
        article_id=article.id, status="success", picks_inserted=len(parsed.picks)
    )


@router.post("/actual-picks")
def ingest_actual_pick(payload: ActualPickInput, db: Session = DB_SESSION) -> dict[str, int]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == payload.draft_year))
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Unknown draft year: {payload.draft_year}")
    record = ActualDraftPick(
        draft_cycle_id=cycle.id,
        round_number=payload.round_number,
        overall_pick=payload.overall_pick,
        team_id=None,
        player_id=None,
        normalized_player_name=normalize_player_name(payload.player_name),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id}


@router.post("/analytics/backtest/{draft_year}", response_model=list[BacktestResult])
def backtest_sources(draft_year: int, db: Session = DB_SESSION) -> list[BacktestResult]:
    rows = run_source_backtest(db, draft_year)
    source_by_id = {source.id: source.slug for source in db.scalars(select(Source)).all()}
    return [
        BacktestResult(
            source_slug=source_by_id.get(row.source_id, "unknown"),
            exact_pick_hits=row.exact_pick_hits,
            player_team_hits=row.player_team_hits,
            round1_player_hits=row.round1_player_hits,
            avg_pick_distance=float(row.avg_pick_distance),
            weighted_accuracy_score=float(row.weighted_accuracy_score),
        )
        for row in rows
    ]


@router.post("/ingestion/run/all")
def run_all_ingestion() -> dict[str, str]:
    run_all_active_ingestion_sync()
    return {"status": "ok"}


@router.post("/ingestion/run/{source_slug}")
def run_source_ingestion(source_slug: str, db: Session = DB_SESSION) -> dict[str, str]:
    source = db.scalar(select(Source).where(Source.slug == source_slug))
    if source is None:
        raise HTTPException(status_code=404, detail=f"Unknown source slug: {source_slug}")
    run_ingestion_for_source_sync(source.id)
    return {"status": "ok"}


@router.post("/ingestion/draft-order")
def ingest_draft_order(
    payload: DraftOrderIngestionRequest, db: Session = DB_SESSION
) -> dict[str, int | str]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == payload.draft_year))
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Unknown draft year: {payload.draft_year}")

    for pick in payload.picks:
        team = db.scalar(select(Team).where(Team.abbreviation == pick.team_abbreviation.upper()))
        if team is None:
            raise HTTPException(status_code=404, detail=f"Unknown team: {pick.team_abbreviation}")
        row = db.scalar(
            select(DraftOrderPick).where(
                DraftOrderPick.draft_cycle_id == cycle.id,
                DraftOrderPick.overall_pick == pick.overall_pick,
            )
        )
        if row is None:
            db.add(
                DraftOrderPick(
                    draft_cycle_id=cycle.id,
                    round_number=pick.round_number,
                    overall_pick=pick.overall_pick,
                    team_id=team.id,
                    source_name=payload.source_name,
                )
            )
        else:
            row.round_number = pick.round_number
            row.team_id = team.id
            row.source_name = payload.source_name
    db.commit()
    return {"status": "ok", "picks_ingested": len(payload.picks)}


@router.get("/draft-order/{draft_year}")
def get_draft_order(
    draft_year: int,
    db: Session = DB_SESSION,
    team: str | None = Query(
        default=None,
        min_length=2,
        max_length=4,
        description="When set (e.g. TEN), response includes next unfilled overall for that team.",
    ),
    max_overall: int = Query(
        default=400,
        ge=1,
        le=400,
        description="Upper bound used when resolving next_overall_pick for team context.",
    ),
) -> dict[str, object]:
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Unknown draft year: {draft_year}")
    rows = db.execute(
        select(DraftOrderPick, Team.abbreviation)
        .join(Team, Team.id == DraftOrderPick.team_id)
        .where(DraftOrderPick.draft_cycle_id == cycle.id)
        .order_by(DraftOrderPick.overall_pick.asc())
    ).all()
    out: dict[str, object] = {
        "draft_year": draft_year,
        "picks": [
            {
                "overall_pick": row[0].overall_pick,
                "round_number": row[0].round_number,
                "team_abbreviation": row[1],
                "source_name": row[0].source_name,
            }
            for row in rows
        ],
    }
    if team:
        abbr = team.strip().upper()
        out["resolved_team"] = abbr
        out["next_overall_pick"] = compute_next_round1_overall_for_team(
            db, draft_cycle_id=cycle.id, team_abbr=abbr, max_overall=max_overall
        )
    return out


@router.post("/ingestion/draft-order/live")
def ingest_live_draft_order(
    draft_year: int = Query(..., ge=2010, le=2100),
    db: Session = DB_SESSION,
) -> dict[str, int | str]:
    try:
        count = ingest_live_tankathon_draft_order(db, draft_year=draft_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Live source fetch failed: {exc}") from exc
    return {"status": "ok", "picks_ingested": count}


@router.post("/ingestion/team-staff/live")
def ingest_live_staff(
    draft_year: int = Query(..., ge=2010, le=2100),
    db: Session = DB_SESSION,
) -> dict[str, int | str]:
    try:
        count = ingest_live_team_staff(db, draft_year=draft_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Live source fetch failed: {exc}") from exc
    return {"status": "ok", "teams_updated": count}


@router.post("/ingestion/prospects/live")
def ingest_live_prospects(
    draft_year: int = Query(..., ge=2010, le=2100),
    limit: int = Query(default=128, ge=16, le=512),
    db: Session = DB_SESSION,
) -> dict[str, int | str]:
    try:
        count = ingest_live_tankathon_prospects(db, draft_year=draft_year, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Live source fetch failed: {exc}") from exc
    return {"status": "ok", "prospects_ingested": count}


@router.post("/ingestion/nfl-draft-tracker/live")
def ingest_nfl_draft_tracker_live(
    draft_year: int = Query(..., ge=2010, le=2100),
    db: Session = DB_SESSION,
) -> dict[str, int | str]:
    """Fetch nfl.com draft tracker and upsert announced picks."""
    try:
        count = ingest_nfl_com_tracker_picks(db, draft_year=draft_year)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"NFL.com tracker fetch failed: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"NFL.com tracker parse failed: {type(exc).__name__}",
        ) from exc
    return {"status": "ok", "picks_upserted": count}


@router.get("/live-draft/{draft_year}", response_model=LiveDraftBoardResponse)
def get_live_draft_board(
    draft_year: int,
    sync: bool = Query(
        default=False,
        description="When true, fetches nfl.com draft tracker before reading the database.",
    ),
    max_overall: int = Query(
        default=257,
        ge=1,
        le=400,
        description="Maximum overall pick to return in the live board payload.",
    ),
    db: Session = DB_SESSION,
) -> LiveDraftBoardResponse:
    """Live draft board: official picks (when announced) vs mock consensus."""
    cycle = db.scalar(select(DraftCycle).where(DraftCycle.year == draft_year))
    if cycle is None:
        raise HTTPException(status_code=404, detail=f"Unknown draft year: {draft_year}")

    synced = False
    if sync:
        try:
            ingest_nfl_com_tracker_picks(db, draft_year=draft_year)
            synced = True
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502, detail=f"NFL.com tracker fetch failed: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"NFL.com tracker parse failed: {type(exc).__name__}",
            ) from exc

    actual_rows = db.execute(
        select(ActualDraftPick, Team.abbreviation)
        .outerjoin(Team, Team.id == ActualDraftPick.team_id)
        .where(
            ActualDraftPick.draft_cycle_id == cycle.id, ActualDraftPick.overall_pick <= max_overall
        )
    ).all()
    actual_by_overall: dict[int, tuple[ActualDraftPick, str | None]] = {
        int(row[0].overall_pick): (row[0], row[1]) for row in actual_rows
    }

    order_rows = db.execute(
        select(DraftOrderPick, Team.abbreviation)
        .join(Team, Team.id == DraftOrderPick.team_id)
        .where(
            DraftOrderPick.draft_cycle_id == cycle.id, DraftOrderPick.overall_pick <= max_overall
        )
    ).all()
    order_by_overall: dict[int, tuple[DraftOrderPick, str]] = {
        int(row[0].overall_pick): (row[0], row[1]) for row in order_rows
    }

    now = datetime.now(UTC)
    picks_out: list[LiveDraftPickRow] = []
    highest_seen_overall = max(
        [0, *actual_by_overall.keys(), *order_by_overall.keys()],
    )
    board_max = min(max_overall, max(32, highest_seen_overall))
    for overall in range(1, board_max + 1):
        taken_before = taken_normalized_names(db, draft_year, before_overall=overall)
        consensus = pick_consensus(
            db,
            draft_year=draft_year,
            overall_pick=overall,
            top_n=8,
            exclude_taken_normalized=taken_before if taken_before else None,
        )
        top1 = consensus.top_players[0] if consensus.top_players else None

        ap_t = actual_by_overall.get(overall)
        od_t = order_by_overall.get(overall)
        round_number = 1
        team_abbr: str | None = None
        actual_name: str | None = None
        if ap_t:
            ap, abbr = ap_t
            round_number = ap.round_number
            team_abbr = abbr
            actual_name = ap.normalized_player_name
        if team_abbr is None and od_t is not None:
            dop, abbr = od_t
            team_abbr = abbr
            round_number = dop.round_number

        rank = _consensus_rank_for_actual(actual_name, consensus)
        picks_out.append(
            LiveDraftPickRow(
                overall_pick=overall,
                round_number=round_number,
                team_abbreviation=team_abbr,
                actual_player_name=actual_name,
                consensus_top1_name=top1.player_name if top1 else None,
                consensus_top1_weighted_probability=top1.weighted_probability if top1 else None,
                consensus_rank_of_actual=rank,
            )
        )

    return LiveDraftBoardResponse(
        draft_year=draft_year,
        synced_from_source=synced,
        picks=picks_out,
        updated_at=now,
    )
