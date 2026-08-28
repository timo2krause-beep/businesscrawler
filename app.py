"""FastAPI App – SaaS Platform für automatisierte Reports."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.admin_router import router as admin_router
from api.auth_router import router as auth_router
from api.company_router import router as company_router
from api.event_router import router as event_router
from api.module_router import router as module_router
from api.oauth_router import router as oauth_router
from api.payment_router import router as payment_router
from api.report_router import router as report_router
from config.settings import settings
from core import registry
from core.database import init_db
from modules.cve_monitor import CVEMonitor
from modules.ki_wettbewerb import KIWettbewerbMonitor
from modules.review_monitor import ReviewMonitor
from modules.rss_monitor import RSSMonitor
from modules.social_media_generator import SocialMediaGenerator
from modules.social_sentiment import SocialSentimentMonitor
from modules.tech_stack_monitor import TechStackMonitor
from modules.wettbewerbs_monitor import WettbewerbsMonitor

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logging.getLogger(__name__).info("Datenbank-Tabellen erstellt")
    yield


app = FastAPI(title="Scraper Platform", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list({settings.frontend_url, "http://localhost:3000"}),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Module registrieren
registry.register(TechStackMonitor())
registry.register(CVEMonitor())
registry.register(RSSMonitor())
registry.register(WettbewerbsMonitor())
registry.register(KIWettbewerbMonitor())
registry.register(SocialMediaGenerator())
registry.register(SocialSentimentMonitor())
registry.register(ReviewMonitor())

# Router einbinden
app.include_router(auth_router)
app.include_router(oauth_router)
app.include_router(company_router)
app.include_router(payment_router)
app.include_router(module_router)
app.include_router(report_router)
app.include_router(event_router)
app.include_router(admin_router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
