from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.dev_readings import router as dev_readings_router
from app.api.interpretations import router as interpretations_router
from app.api.spreads import router as spreads_router
from app.api.tarot_cards import router as tarot_cards_router
from app.config import get_settings
from app.db import engine


settings = get_settings()

app = FastAPI(title=settings.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(spreads_router)
app.include_router(tarot_cards_router)
app.include_router(interpretations_router)
app.include_router(dev_readings_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
async def health_db() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok"}
