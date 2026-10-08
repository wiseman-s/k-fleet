from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.templates import get_templates
from app.models.journey import Journey
from app.models.journey_audit import JourneyAudit
from app.models.vehicle import Vehicle
from app.models.driver import Driver
from app.models.station import Station
from app.models.department import Department
from app.models.user import User
from app.schemas.journey import (
    JourneyCreate, JourneyUpdate, JourneyOut,
    JourneyApprove, JourneyReject, JourneyExit, JourneyReturn
)
from app.services.audit import log_journey_action, diff_fields


router = APIRouter(prefix="/journeys", tags=["Journeys"])


templates = get_templates()


def generate_journey_code(db: Session) -> str:
    count = db.query(Journey).count() + 1
    return f"JRN-{count:05d}"


def get_driver_or_404(driver_id: int, db: Session) -> Driver:
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver {driver_id} not found")
    return driver


def user_can_act_on_journey(current_user: User, journey: Journey) -> bool:
    """Admin can act on any journey. Others must match the journey's origin station."""
    if current_user.role == "admin":
        return True
    return current_user.station_id == journey.origin_station_id


# =================================================================
# HTML FORM ROUTES — MUST COME BEFORE /{journey_id} ROUTES
# =================================================================

@router.get("/create-page", response_class=HTMLResponse)
def new_journey_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    departments = db.query(Department).filter(Department.is_active == True).all()  # noqa: E712
    stations = db.query(Station).filter(Station.is_active == True).all()  # noqa: E712
    return templates.TemplateResponse(
        request=request,
        name="new_journey.html",
        context={
            "departments": departments,
            "stations": stations,
        }
    )


@router.get("/{journey_id}/assign-page", response_class=HTMLResponse)
def assign_journey_page(
    journey_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "requested":
        return RedirectResponse(
            url="/dashboard?error=not_requested",
            status_code=303
        )

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(
            url="/dashboard?error=out_of_scope",
            status_code=303
        )

    # Only show vehicles whose home station matches the journey's origin
    vehicles = (
        db.query(Vehicle)
        .filter(
            Vehicle.status == "active",
            Vehicle.home_station_id == journey.origin_station_id,
        )
        .all()
    )

    drivers = db.query(Driver).filter(
        Driver.is_active == True
    ).all()  # noqa: E712

    return templates.TemplateResponse(
        request=request,
        name="assign_journey.html",
        context={
            "journey": journey,
            "vehicles": vehicles,
            "drivers": drivers,
        }
    )


@router.post("/{journey_id}/assign-page")
def assign_journey_form(
    journey_id: int,
    vehicle_id: int = Form(...),
    driver_id: int = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "requested":
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(
            url="/dashboard?error=out_of_scope",
            status_code=303
        )

    journey.vehicle_id = vehicle_id
    journey.driver_id = driver_id
    journey.status = "approved"
    journey.approved_at = datetime.utcnow()

    if remarks:
        journey.remarks = remarks

    log_journey_action(
        db,
        journey,
        current_user,
        "approved",
        field_changes={
            "vehicle_id": [None, vehicle_id],
            "driver_id": [None, driver_id]
        },
        remarks=remarks or "Assigned and approved"
    )

    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/create-page")
def create_journey_form(
    requesting_department_id: int = Form(...),
    requested_by_name: str = Form(...),
    requested_by_staff_number: str = Form(""),
    origin_station_id: int = Form(...),
    destination: str = Form(...),
    purpose: str = Form(...),
    priority: str = Form("normal"),
    expected_departure: str = Form(...),
    expected_return: str = Form(...),
    redirect_to: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    def _parse_dt(s):
        if len(s) == 16:
            s += ":00"
        return datetime.fromisoformat(s)

    new_journey = Journey(
        vehicle_id=None,
        driver_id=None,
        requesting_department_id=requesting_department_id,
        requested_by_name=requested_by_name,
        requested_by_staff_number=requested_by_staff_number or None,
        requested_by_user_id=current_user.id,
        origin_station_id=origin_station_id,
        destination=destination,
        purpose=purpose,
        priority=priority,
        expected_departure=_parse_dt(expected_departure),
        expected_return=_parse_dt(expected_return),
        journey_code=generate_journey_code(db),
        status="requested",
    )

    db.add(new_journey)
    db.flush()

    log_journey_action(
        db,
        new_journey,
        current_user,
        "created",
        remarks="Vehicle request submitted"
    )

    db.commit()

    target = redirect_to if redirect_to in ("/dashboard", "/booking") else "/dashboard"
    return RedirectResponse(url=target, status_code=303)


@router.get("/{journey_id}/modify-page", response_class=HTMLResponse)
def modify_journey_page(
    journey_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "pending":
        return RedirectResponse(url="/dashboard?error=not_pending", status_code=303)

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(url="/dashboard?error=out_of_scope", status_code=303)

    vehicles = db.query(Vehicle).filter(Vehicle.status == "active").all()
    drivers = db.query(Driver).filter(Driver.is_active == True).all()  # noqa: E712
    departments = db.query(Department).filter(Department.is_active == True).all()  # noqa: E712
    stations = db.query(Station).filter(Station.is_active == True).all()  # noqa: E712

    return templates.TemplateResponse(
        request=request,
        name="modify_journey.html",
        context={
            "journey": journey,
            "vehicles": vehicles,
            "drivers": drivers,
            "departments": departments,
            "stations": stations,
        }
    )


@router.post("/{journey_id}/modify-page")
def modify_journey_form(
    journey_id: int,
    vehicle_id: int = Form(...),
    driver_id: int = Form(...),
    requesting_department_id: int = Form(...),
    requested_by_name: str = Form(...),
    requested_by_staff_number: str = Form(""),
    origin_station_id: int = Form(...),
    destination: str = Form(...),
    purpose: str = Form(...),
    priority: str = Form("normal"),
    expected_departure: str = Form(...),
    expected_return: str = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "pending":
        return RedirectResponse(url="/dashboard?error=not_pending", status_code=303)

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(url="/dashboard?error=out_of_scope", status_code=303)

    # Capture old values before applying modifications
    old_values = {
        "vehicle_id": journey.vehicle_id,
        "driver_id": journey.driver_id,
        "requesting_department_id": journey.requesting_department_id,
        "requested_by_name": journey.requested_by_name,
        "requested_by_staff_number": journey.requested_by_staff_number,
        "origin_station_id": journey.origin_station_id,
        "destination": journey.destination,
        "purpose": journey.purpose,
        "priority": journey.priority,
        "expected_departure": (
            journey.expected_departure.isoformat()
            if journey.expected_departure
            else None
        ),
        "expected_return": (
            journey.expected_return.isoformat()
            if journey.expected_return
            else None
        ),
    }

    def _parse_dt(s):
        if len(s) == 16:
            s += ":00"
        return datetime.fromisoformat(s)

    journey.vehicle_id = vehicle_id
    journey.driver_id = driver_id
    journey.requesting_department_id = requesting_department_id
    journey.requested_by_name = requested_by_name
    journey.requested_by_staff_number = requested_by_staff_number or None
    journey.origin_station_id = origin_station_id
    journey.destination = destination
    journey.purpose = purpose
    journey.priority = priority
    journey.expected_departure = _parse_dt(expected_departure)
    journey.expected_return = _parse_dt(expected_return)

    if remarks:
        journey.remarks = remarks

    # Capture new values and create audit entry for actual changes
    new_values = {
        "vehicle_id": vehicle_id,
        "driver_id": driver_id,
        "requesting_department_id": requesting_department_id,
        "requested_by_name": requested_by_name,
        "requested_by_staff_number": requested_by_staff_number or None,
        "origin_station_id": origin_station_id,
        "destination": destination,
        "purpose": purpose,
        "priority": priority,
        "expected_departure": _parse_dt(expected_departure).isoformat(),
        "expected_return": _parse_dt(expected_return).isoformat(),
    }

    changes = diff_fields(old_values, new_values)

    if changes:
        log_journey_action(
            db,
            journey,
            current_user,
            "modified",
            field_changes=changes
        )

    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/{journey_id}/approve-page")
def approve_journey_form(
    journey_id: int,
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey or journey.status != "pending":
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(url="/dashboard?error=out_of_scope", status_code=303)

    journey.status = "approved"
    journey.approved_at = datetime.utcnow()

    if remarks:
        journey.remarks = remarks

    # Audit approval
    log_journey_action(
        db,
        journey,
        current_user,
        "approved",
        remarks=remarks or None
    )

    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.post("/{journey_id}/reject-page")
def reject_journey_form(
    journey_id: int,
    rejection_reason: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey or journey.status != "pending":
        return RedirectResponse(url="/dashboard", status_code=303)

    if not user_can_act_on_journey(current_user, journey):
        return RedirectResponse(url="/dashboard?error=out_of_scope", status_code=303)

    journey.status = "rejected"
    journey.approved_at = datetime.utcnow()
    journey.rejection_reason = rejection_reason

    # Audit rejection
    log_journey_action(
        db,
        journey,
        current_user,
        "rejected",
        remarks=rejection_reason
    )

    db.commit()

    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/{journey_id}/history", response_class=HTMLResponse)
def journey_history_page(
    journey_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    audits = (
        db.query(JourneyAudit)
        .filter(JourneyAudit.journey_id == journey_id)
        .order_by(JourneyAudit.created_at.asc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="journey_history.html",
        context={"journey": journey, "audits": audits}
    )


# =================================================================
# JSON API ROUTES
# =================================================================

@router.post("/", response_model=JourneyOut, status_code=status.HTTP_201_CREATED)
def create_journey(journey: JourneyCreate, db: Session = Depends(get_db)):
    if not db.query(Vehicle).filter(Vehicle.id == journey.vehicle_id).first():
        raise HTTPException(
            status_code=400,
            detail=f"Vehicle {journey.vehicle_id} does not exist"
        )

    if not db.query(Driver).filter(Driver.id == journey.driver_id).first():
        raise HTTPException(
            status_code=400,
            detail=f"Driver {journey.driver_id} does not exist"
        )

    if not db.query(Department).filter(
        Department.id == journey.requesting_department_id
    ).first():
        raise HTTPException(
            status_code=400,
            detail=f"Department {journey.requesting_department_id} does not exist"
        )

    if not db.query(Station).filter(
        Station.id == journey.origin_station_id
    ).first():
        raise HTTPException(
            status_code=400,
            detail=f"Origin station {journey.origin_station_id} does not exist"
        )

    if journey.destination_station_id:
        if not db.query(Station).filter(
            Station.id == journey.destination_station_id
        ).first():
            raise HTTPException(
                status_code=400,
                detail=f"Destination station {journey.destination_station_id} does not exist"
            )

    new_journey = Journey(
        **journey.model_dump(),
        journey_code=generate_journey_code(db),
        status="pending"
    )

    db.add(new_journey)
    db.commit()
    db.refresh(new_journey)

    return new_journey


@router.get("/", response_model=List[JourneyOut])
def list_journeys(db: Session = Depends(get_db)):
    return db.query(Journey).order_by(Journey.created_at.desc()).all()


@router.get("/{journey_id}", response_model=JourneyOut)
def get_journey(journey_id: int, db: Session = Depends(get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    return journey


@router.patch("/{journey_id}", response_model=JourneyOut)
def update_journey(
    journey_id: int,
    updates: JourneyUpdate,
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "pending":
        raise HTTPException(
            status_code=400,
            detail="Only pending journeys can be edited"
        )

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(journey, field, value)

    db.commit()
    db.refresh(journey)

    return journey


@router.post("/{journey_id}/approve", response_model=JourneyOut)
def approve_journey(
    journey_id: int,
    payload: JourneyApprove,
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Journey is {journey.status}, cannot approve"
        )

    journey.status = "approved"
    journey.approved_at = datetime.utcnow()

    if payload.remarks:
        journey.remarks = payload.remarks

    db.commit()
    db.refresh(journey)

    return journey


@router.post("/{journey_id}/reject", response_model=JourneyOut)
def reject_journey(
    journey_id: int,
    payload: JourneyReject,
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Journey is {journey.status}, cannot reject"
        )

    journey.status = "rejected"
    journey.approved_at = datetime.utcnow()
    journey.rejection_reason = payload.rejection_reason

    db.commit()
    db.refresh(journey)

    return journey


@router.post("/{journey_id}/exit", response_model=JourneyOut)
def record_exit(
    journey_id: int,
    payload: JourneyExit,
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "approved":
        raise HTTPException(
            status_code=400,
            detail=f"Journey is {journey.status}, cannot exit"
        )

    journey.status = "out"
    journey.actual_departure = datetime.utcnow()
    journey.starting_odometer = payload.starting_odometer

    if payload.remarks:
        journey.remarks = payload.remarks

    db.commit()
    db.refresh(journey)

    return journey


@router.post("/{journey_id}/return", response_model=JourneyOut)
def record_return(
    journey_id: int,
    payload: JourneyReturn,
    db: Session = Depends(get_db)
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()

    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")

    if journey.status != "out":
        raise HTTPException(
            status_code=400,
            detail=f"Journey is {journey.status}, cannot return"
        )

    journey.status = "closed"
    journey.actual_return = datetime.utcnow()
    journey.ending_odometer = payload.ending_odometer

    if journey.starting_odometer is not None:
        journey.distance_km = (
            payload.ending_odometer - journey.starting_odometer
        )

    if payload.remarks:
        journey.remarks = payload.remarks

    vehicle = db.query(Vehicle).filter(
        Vehicle.id == journey.vehicle_id
    ).first()

    if vehicle:
        vehicle.current_odometer = payload.ending_odometer

    db.commit()
    db.refresh(journey)

    return journey