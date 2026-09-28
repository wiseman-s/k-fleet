from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.vehicle import Vehicle
from app.models.station import Station
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.qr_utils import generate_qr_data_url

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

templates = Jinja2Templates(directory="app/templates")


# =================================================================
# HTML FORM ROUTES — MUST COME BEFORE /{vehicle_id} ROUTES
# =================================================================

@router.get("/add-page", response_class=HTMLResponse)
def add_vehicle_page(request: Request, db: Session = Depends(get_db)):
    stations = db.query(Station).filter(Station.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse(
        request=request,
        name="add_vehicle.html",
        context={"stations": stations}
    )


@router.post("/add-page")
def add_vehicle_form(
    registration_number: str = Form(...),
    make: str = Form(""),
    model: str = Form(""),
    year: int = Form(0),
    home_station_id: int = Form(...),
    fuel_type: str = Form(""),
    current_odometer: int = Form(0),
    status: str = Form("active"),
    db: Session = Depends(get_db),
):
    existing = db.query(Vehicle).filter(
        Vehicle.registration_number == registration_number
    ).first()
    if existing:
        return RedirectResponse(url="/vehicles/add-page?error=exists", status_code=303)

    station = db.query(Station).filter(Station.id == home_station_id).first()
    if not station:
        return RedirectResponse(url="/vehicles/add-page?error=station", status_code=303)

    vehicle = Vehicle(
        registration_number=registration_number,
        make=make or None,
        model=model or None,
        year=year or None,
        home_station_id=home_station_id,
        fuel_type=fuel_type or None,
        current_odometer=current_odometer or 0,
        status=status or "active",
    )
    db.add(vehicle)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/qr-codes", response_class=HTMLResponse)
def qr_codes_page(request: Request, db: Session = Depends(get_db)):
    vehicles = db.query(Vehicle).order_by(Vehicle.registration_number).all()
    qr_data = []
    for v in vehicles:
        qr_data.append({
            "vehicle": v,
            "qr_data_url": generate_qr_data_url(v.registration_number),
        })
    return templates.TemplateResponse(
        request=request,
        name="qr_codes.html",
        context={"qr_data": qr_data}
    )


@router.get("/{vehicle_id}/qr", response_class=HTMLResponse)
def vehicle_qr_page(vehicle_id: int, request: Request, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    qr_data_url = generate_qr_data_url(vehicle.registration_number)
    return templates.TemplateResponse(
        request=request,
        name="qr_single.html",
        context={"vehicle": vehicle, "qr_data_url": qr_data_url}
    )


# =================================================================
# JSON API ROUTES
# =================================================================

@router.post("/", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    existing = db.query(Vehicle).filter(
        Vehicle.registration_number == vehicle.registration_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Vehicle {vehicle.registration_number} already exists"
        )

    station = db.query(Station).filter(Station.id == vehicle.home_station_id).first()
    if not station:
        raise HTTPException(
            status_code=400,
            detail=f"Station with id {vehicle.home_station_id} does not exist"
        )

    new_vehicle = Vehicle(**vehicle.model_dump())
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    return new_vehicle


@router.get("/", response_model=List[VehicleOut])
def list_vehicles(db: Session = Depends(get_db)):
    return db.query(Vehicle).all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(vehicle_id: int, updates: VehicleUpdate, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    if updates.home_station_id is not None:
        station = db.query(Station).filter(Station.id == updates.home_station_id).first()
        if not station:
            raise HTTPException(
                status_code=400,
                detail=f"Station with id {updates.home_station_id} does not exist"
            )

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    db.delete(vehicle)
    db.commit()
    return None