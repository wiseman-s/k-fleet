import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, engine
from app.models import (
    station, vehicle, driver, department, journey,
    security_alert, user, gate, gate_transaction, gps_event,
)
from app.routers import (
    stations, vehicles, drivers, departments, journeys,
    dashboard, gate as gate_router, gates, auth, tracking,
)
from app.services.tracker import run_poller


logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Start background GPS poller
    poller_task = asyncio.create_task(run_poller())
    yield
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="K-FLEET SECURE", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(auth.router)
app.include_router(stations.router)
app.include_router(gates.router)
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(departments.router)
app.include_router(journeys.router)
app.include_router(dashboard.router)
app.include_router(gate_router.router)
app.include_router(tracking.router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")


@app.get("/health")
def health():
    return {"status": "ok"}