# DraftDay

NFL mock draft aggregation and consensus prediction platform.

## MVP Included

- FastAPI backend with modular layers (ingestion, normalization, analytics, API)
- SQLAlchemy models for all core entities in the specification
- Alembic migration bootstrap
- Parsed mock draft schemas and parser interface contract
- Manual CSV import parser
- Consensus API endpoints:
  - `GET /v1/consensus/picks/{draft_year}/{overall_pick}`
  - `GET /v1/consensus/players/{draft_year}/{player_name}`
- Ingestion endpoints:
  - `POST /v1/ingestion/manual`
  - `POST /v1/ingestion/parse-url`
- Historical accuracy/backtesting:
  - `POST /v1/actual-picks`
  - `POST /v1/analytics/backtest/{draft_year}`
- Next.js + Tailwind dashboard scaffold in `frontend/`
- Draft Intelligence feature arm (Phase 1-4) under `backend/app/ml/`
- Dockerized local development with PostgreSQL

## Quickstart

1. Copy environment:
   - `copy .env.example .env`
2. Start services:
   - `docker compose up --build`
3. Run migrations in API container:
   - `docker compose exec api alembic upgrade head`
4. Open:
   - API docs: `http://localhost:8000/docs`
   - Health: `http://localhost:8000/health`
5. Run dashboard:
   - `cd frontend`
   - `npm install`
   - `set NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
   - `npm run dev`

## Parser Contract

Every source parser should implement:

- `discover()`
- `fetch(url)`
- `parse_metadata(payload, url)`
- `parse_picks(payload)`
- `validate(parsed)`

And return a common `ParsedMockDraft` object.

## Source Parser Configs

Source-specific parser behavior now lives in `app/parsers/source_configs.py`, including:

Default HTML sources (after `seed_sources.py`): `nfl-com`, `espn`, `cbssports`, `yahoo`, `pfn`, `si-com`, `fantasypros`, `sporting-news`, plus `manual`.

- discovery URL
- article link keyword filter
- selector chains for title/author/published/updated dates
- pick row/cell selectors
- parser date patterns

Seed source rows from these configs with:

- `python scripts/seed_sources.py`
- `python scripts/seed_draft_cycles.py`

Then trigger ingestion:

- `POST /v1/ingestion/run/all`
- `POST /v1/ingestion/run/{source_slug}`

Automated ingestion runs every 30 minutes for active automated sources via APScheduler.

## Parser Fallback Chain

`GenericStaticHtmlParser` now attempts pick extraction in this order:

1. table rows (`pick_row_selectors`)
2. list items (`ol li`, `ul li`)
3. article text line parsing with regex fallback

Metadata extraction also supports selector chains and date parsing for:

- author
- published timestamp
- updated timestamp

## Draft Intelligence (Phase 1 + 4)

This branch adds an isolated ML feature arm that extends the existing product without replacing consensus.

### Isolation and toggle

- ML code is isolated under `backend/app/ml/`
- Existing scraping and consensus flows are unchanged
- Disable ML routes by setting `ENABLE_DRAFT_INTELLIGENCE=false`

### New database tables

- `team_roster_snapshots`
- `team_position_need_features`
- `prospect_features`
- `pick_context_features`
- `candidate_player_features`
- `ml_model_runs`
- `ml_predictions`

Migration: `alembic/versions/0003_draft_intelligence_tables.py`

### Implemented models

- Need Model (heuristic baseline): `backend/app/ml/models/need_model.py`
- Position Model (interpretable logistic regression baseline): `backend/app/ml/models/position_model.py`
- Player Model (interpretable logistic regression baseline): `backend/app/ml/models/player_model.py`

### Implemented routes (Phase 2)

- `GET /api/v1/intelligence/team-needs?team=TEN&year=2026`
- `GET /api/v1/intelligence/pick-position-probs?team=TEN&pick=1&year=2026`

### Implemented routes (Phase 3)

- `POST /api/v1/intelligence/pick-player-probs`

### Implemented routes (Phase 4)

- `GET /api/v1/intelligence/compare-with-consensus?team=TEN&pick=1&year=2026`
- `GET /api/v1/intelligence/model-metadata`

### Frontend additions

- `Draft Intelligence` section on dashboard
- `TeamNeedProfile` component
- `PickIntelligencePanel` component
- `PlayerProbabilityPanel` component
- `ConsensusVsIntelligencePanel` component

### Train pipelines

- Need model: `backend/app/ml/training/train_need_model.py`
- Position model: `backend/app/ml/training/train_position_model.py`
- Player model: `backend/app/ml/training/train_player_model.py`

### Training quickstart

1. Run migrations:
   - `alembic upgrade head`
2. Seed sources/cycles and ingest data as needed.
3. Build need features/model:
   - call `train_need_model_for_year(<year>)` from `backend/app/ml/training/train_need_model.py`
4. Train position model:
   - call `train_position_model(...)` from `backend/app/ml/training/train_position_model.py`
5. Train player model:
   - call `train_player_model(...)` from `backend/app/ml/training/train_player_model.py`

Each run is recorded in `ml_model_runs` with model version, temporal windows, metrics, and artifact path.

### Inference and caching

- Position, player, and comparison predictions are cached in `ml_predictions`.
- Cache keys include:
  - `draft_cycle_id`
  - `team_id`
  - `overall_pick`
  - `prediction_type`
  - `model_version`
- Prediction payloads include grouped explanation components:
  - `need_component`
  - `talent_component`
  - `context_component`
- `superstar_override_score` is elevated when:
  - team need at the position is weak,
  - player talent profile is strong,
  - and model probability remains strong.

Artifacts are versioned in `backend/artifacts/ml/`.

## Organizational Intelligence + Team View (Phase 1 + 4)

This extension adds organization-aware priors (GM/HC/regime behavior) and a Team View workflow.

### Modular backend

- Core modules live under `backend/app/org_intelligence/`
- Artifacts are stored in `backend/artifacts/org_intelligence/`
- Feature can be toggled with `ENABLE_ORG_INTELLIGENCE=false`
- Existing consensus and Draft Intelligence routes continue to work independently

### New tables

- `general_managers`
- `head_coaches`
- `team_front_office_history`
- `gm_draft_history_features`
- `coach_draft_context_features`
- `team_org_tendency_features`
- `team_view_predictions`

Migration: `alembic/versions/0004_org_intelligence_tables.py`

### Implemented Phase 1 routes

- `GET /api/v1/team-view/org-profile?team=TEN&year=2026`
- `GET /api/v1/team-view/history?team=TEN&year=2026&lookback_years=5`

### Implemented Phase 2 route

- `GET /api/v1/team-view/position-probs?team=TEN&pick=1&year=2026`

This returns:
- base ML position probabilities
- org-adjusted position probabilities
- per-position deltas
- team snapshot context

### Implemented Phase 3 routes

- `POST /api/v1/team-view/player-probs`
- `GET /api/v1/team-view/summary?team=TEN&year=2026&pick=1`

### Implemented Phase 4 route

- `GET /api/v1/team-view/backtest`

This returns comparative evaluation snapshots for:
- base ML
- org-adjusted ML
- consensus+ML+org ensemble

Player prediction payloads now include:
- `need_component`
- `talent_component`
- `context_component`
- `organizational_component`

Summary payload includes:
- team snapshot
- consensus top players
- base ML top players
- org-adjusted top players
- integrated explanation text for Team View

### Team View frontend

Route:
- `/teams/:teamId/draft-view`

Components:
- `TeamSnapshotCard`
- `NeedProfilePanel`
- `OrgTendenciesPanel`
- `PredictionPanel`
- `ExplanationPanel`
- `DraftHistoryPanel`

Main page component:
- `frontend/src/features/team-view/TeamViewPage.tsx`

Phase 3 Team View updates:
- prediction panel now includes org-adjusted player probabilities
- explanation panel now renders contribution components including `organizational_component`
- frontend uses backend-generated `integrated_explanation` text

Phase 4 Team View updates:
- Team View supports year/pick controls and manual refresh for draft-day workflows
- team-view payloads are cached in `team_view_predictions` for:
  - org profile
  - history
  - position probabilities
  - player probabilities
  - summary
- explanation text now incorporates:
  - regime stability context
  - offense/defense tilt
  - need-vs-BPA style
  - top position and top player rationale
- page load now degrades gracefully with partial data if one endpoint fails

### Org-intelligence training and inference

Training modules:
- `backend/app/org_intelligence/training/train_org_prior_model.py`
- `backend/app/org_intelligence/training/train_integrated_team_model.py`

Evaluation modules:
- `backend/app/org_intelligence/evaluation/metrics.py`
- `backend/app/org_intelligence/evaluation/backtests.py`

Backtesting compares:
- base Draft Intelligence model
- org-adjusted model
- consensus+ML+org blended ensemble

Inference module:
- `backend/app/org_intelligence/inference/org_predictor.py`

Artifacts:
- `backend/artifacts/org_intelligence/`

## Draft-Slot Predictor Research

Measures which pre-draft traits are statistically significant predictors of where a
prospect is drafted, using every NFL Combine invitee since 2000 (drafted and undrafted)
plus 2015+ college production. Results feed the prospect/player models.

- Findings: `docs/draft-slot-predictors.md`
- Code: `backend/app/draft_slot/` (data joins, features, statistical tests, priors)
- Generated tables and per-position priors: `backend/artifacts/draft_slot/`
- Run: `pip install -e ".[research]"` then `python -m backend.app.draft_slot.cli`

## Next Build Steps

- Add persistent alias lookup logic from `player_aliases` and `school_aliases`
- Add deeper calibration and SHAP explainability utilities
- Add endpoint-level integration tests against seeded Postgres fixtures

## Raspberry Pi Deployment

You can run the full stack on a Raspberry Pi using the deployment bundle in `deploy/pi/`:

- Compose stack: `deploy/pi/docker-compose.pi.yml`
- Reverse proxy config: `deploy/pi/Caddyfile`
- Env template: `deploy/pi/.env.pi.example`
- Step-by-step guide: `deploy/pi/PI_DEPLOY.md`

Quick start:

1. `cp deploy/pi/.env.pi.example deploy/pi/.env.pi`
2. `docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml up -d --build`
3. `docker compose --env-file deploy/pi/.env.pi -f deploy/pi/docker-compose.pi.yml exec api alembic upgrade head`
