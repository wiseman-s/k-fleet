from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.station import Station
from app.schemas.station import StationCreate, StationOut

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.post("/", response_model=StationOut, status_code=status.HTTP_201_CREATED)
def create_station(station: StationCreate, db: Session = Depends(get_db)):
    existing = db.query(Station).filter(Station.name == station.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Station {station.name} already exists")

    new_station = Station(**station.model_dump())
    db.add(new_station)
    db.commit()
    db.refresh(new_station)
    return new_station


@router.get("/", response_model=List[StationOut])
def list_stations(db: Session = Depends(get_db)):
    return db.query(Station).all()


@router.get("/{station_id}", response_model=StationOut)
def get_station(station_id: int, db: Session = Depends(get_db)):
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station