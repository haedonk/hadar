import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import config
from routers import devices, events, readings, summary
from schemas import HealthResponse

logging.basicConfig(level=config.LOG_LEVEL)

app = FastAPI(title="Hadar Dashboard API", debug=config.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(events.router)
app.include_router(summary.router)
app.include_router(readings.router)


@app.get("/healthz", response_model=HealthResponse, tags=["health"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
