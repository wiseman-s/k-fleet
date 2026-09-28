from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from app.core.database import get_db
from app.models.driver import Driver
from app.models.station import Station
from app.schemas.driver import DriverCreate, DriverUpdate, DriverOut

router = APIRouter(prefix="/drivers", tags=["Drivers"])

templates = Jinja2Templates(directory="app/templates")


# =================================================================
# HTML FORM ROUTES — MUST COME BEFORE /{driver_id} ROUTES
# =================================================================

@router.get("/add-page", response_class=HTMLResponse)
def add_driver_page(request: Request, db: Session = Depends(get_db)):
    stations = db.query(Station).filter(Station.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse(
        request=request,
        name="add_driver.html",
        context={"stations": stations}
    )


@router.post("/add-page")
def add_driver_form(
    staff_number: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(""),
    employment_type: str = Form("permanent"),
    duty_station_id: int = Form(...),
    license_number: str = Form(""),
    license_expiry: str = Form(""),
    is_supervisor: str = Form(""),
    db: Session = Depends(get_db),
):
    existing = db.query(Driver).filter(Driver.staff_number == staff_number).first()
    if existing:
        return RedirectResponse(url="/drivers/add-page?error=exists", status_code=303)

    station = db.query(Station).filter(Station.id == duty_station_id).first()
    if not station:
        return RedirectResponse(url="/drivers/add-page?error=station", status_code=303)

    expiry = None
    if license_expiry:
        try:
            expiry = date.fromisoformat(license_expiry)
        except ValueError:
            expiry = None

    driver = Driver(
        staff_number=staff_number,
        full_name=full_name,
        phone=phone or None,
        employment_type=employment_type or "permanent",
        duty_station_id=duty_station_id,
        license_number=license_number or None,
        license_expiry=expiry,
        is_supervisor=bool(is_supervisor),
    )
    db.add(driver)
    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


# =================================================================
# JSON API ROUTES
# =================================================================

@router.post("/", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    existing = db.query(Driver).filter(
        Driver.staff_number == driver.staff_number
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Driver {driver.staff_number} already exists"
        )

    station = db.query(Station).filter(Station.id == driver.duty_station_id).first()
    if not station:
        raise HTTPException(
            status_code=400,
            detail=f"Station with id {driver.duty_station_id} does not exist"
        )

    new_driver = Driver(**driver.model_dump())
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    return new_driver


@router.get("/", response_model=List[DriverOut])
def list_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()


@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


@router.patch("/{driver_id}", response_model=DriverOut)
def update_driver(driver_id: int, updates: DriverUpdate, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    if updates.duty_station_id is not None:
        station = db.query(Station).filter(Station.id == updates.duty_station_id).first()
        if not station:
            raise HTTPException(
                status_code=400,
                detail=f"Station with id {updates.duty_station_id} does not exist"
            )

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(driver, field, value)

    db.commit()
    db.refresh(driver)
    return driver


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")

    db.delete(driver)
    db.commit()
    return None