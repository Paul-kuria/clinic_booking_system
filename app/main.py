from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.db import engine, Base, SessionLocal
from app.core.seed import seed_initial_data
from app.api.v1.doctors import router as doctors_router
from app.api.v1.appointments import router as appointments_router
from app.api.v1.patients import router as patients_router

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Only run DB table creation and seed if not in testing environment
    if settings.ENVIRONMENT != "testing":
        try:
            Base.metadata.create_all(bind=engine)
            with SessionLocal() as db:
                seed_initial_data(db)
        except Exception as e:
            logger.warning("Could not auto-initialize database on startup: %s", e)

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "REST API for a physiotherapy clinic booking system with 5 doctors. "
        "Enforces strict 30-minute slot validation, race-condition proofing, "
        "and advance notice rules."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend clients / cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(patients_router)


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "clinic_timezone": settings.CLINIC_TIMEZONE,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
        "docs_url": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
