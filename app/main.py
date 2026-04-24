from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.services.scheduler import build_scheduler
from backend.app.ml.routes.intelligence_routes import router as intelligence_router
from backend.app.org_intelligence.routes.team_view_routes import router as team_view_router

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
if settings.enable_draft_intelligence:
    app.include_router(intelligence_router)
if settings.enable_org_intelligence:
    app.include_router(team_view_router)
scheduler = build_scheduler()


@app.on_event("startup")
def startup_event() -> None:
    if not scheduler.running:
        scheduler.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
