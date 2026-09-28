from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.gate import Gate
from app.models.station import Station

router = APIRouter(prefix="/gates", tags=["Gates"])


class GateCreate(BaseModel):
    name: str
    code: str
    station_id: int
    is_active: Optional[bool] = True


class GateOut(BaseModel):
    id: int
    name: str
    code: str
    station_id: int
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/", response_model=GateOut, status_code=status.HTTP_201_CREATED)
def create_gate(gate: GateCreate, db: Session = Depends(get_db)):
    if not db.query(Station).filter(Station.id == gate.station_id).first():
        raise HTTPException(status_code=400, detail=f"Station {gate.station_id} does not exist")
    existing = db.query(Gate).filter(Gate.code == gate.code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Gate code {gate.code} already exists")

    new_gate = Gate(**gate.model_dump())
    db.add(new_gate)
    db.commit()
    db.refresh(new_gate)
    return new_gate


@router.get("/", response_model=List[GateOut])
def list_gates(db: Session = Depends(get_db)):
    return db.query(Gate).all()


@router.get("/{gate_id}", response_model=GateOut)
def get_gate(gate_id: int, db: Session = Depends(get_db)):
    gate = db.query(Gate).filter(Gate.id == gate_id).first()
    if not gate:
        raise HTTPException(status_code=404, detail="Gate not found")
    return gate