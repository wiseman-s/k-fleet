from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.core.database import get_db
from app.core.security import (
    get_current_user, decode_token, verify_password, create_access_token
)

from app.models.vehicle import Vehicle
from app.models.journey import Journey
from app.models.driver import Driver
from app.models.user import User
from app.models.gate import Gate
from app.models.gate_transaction import GateTransaction
from app.models.security_alert import SecurityAlert

router = APIRouter(prefix="/gate", tags=["Gate"])

templates = Jinja2Templates(directory="app/templates")


def find_current_journey(vehicle_id: int, db: Session) -> Optional[Journey]:
    return (
        db.query(Journey)
        .filter(
            Journey.vehicle_id == vehicle_id,
            Journey.status.in_(["approved", "out"])
        )
        .order_by(Journey.created_at.desc())
        .first()
    )


def get_gatekeeper_station_id(current_user: User) -> Optional[int]:
    if current_user.gate:
        return current_user.gate.station_id
    return current_user.station_id


def record_transaction(
    db: Session,
    current_user: User,
    journey: Optional[Journey],
    tx_type: str,
    odometer: Optional[int] = None,
    notes: Optional[str] = None,
):
    tx = GateTransaction(
        gate_id=current_user.gate_id or 0,
        journey_id=journey.id if journey else None,
        user_id=current_user.id,
        transaction_type=tx_type,
        odometer=odometer,
        notes=notes,
    )
    db.add(tx)


# ---------------- Gate login / logout ----------------

@router.get("/login", response_class=HTMLResponse)
def gate_login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="gate_login.html",
        context={"error": None}
    )


@router.post("/login")
def gate_login(
    request: Request,
    gate_code: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # TEMPORARY DEBUG
    print(f"[GATE LOGIN] gate_code={gate_code!r} password={password!r}")

    user = db.query(User).filter(User.staff_number == gate_code).first()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request=request,
            name="gate_login.html",
            context={"error": "Invalid gate code or password"},
            status_code=401
        )

    if user.role != "gatekeeper":
        return templates.TemplateResponse(
            request=request,
            name="gate_login.html",
            context={"error": "This account is not a gate account"},
            status_code=403
        )

    if not user.is_active:
        return templates.TemplateResponse(
            request=request,
            name="gate_login.html",
            context={"error": "This gate account is disabled"},
            status_code=403
        )

    token = create_access_token({"sub": str(user.id), "role": user.role})

    response = RedirectResponse(url="/gate", status_code=303)
    response.set_cookie(
        key="kfleet_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12
    )
    return response


@router.get("/logout")
def gate_logout():
    response = RedirectResponse(url="/gate/login", status_code=303)
    response.delete_cookie("kfleet_token")
    return response


# ---------------- Gate console ----------------

@router.get("", response_class=HTMLResponse)
def gate_page(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("kfleet_token")
    user = None

    if token:
        payload = decode_token(token)
        if payload and payload.get("sub"):
            user = db.query(User).filter(User.id == int(payload["sub"])).first()

    if not user or not user.is_active or user.role != "gatekeeper":
        return templates.TemplateResponse(
            request=request,
            name="gate_login.html",
            context={"error": None}
        )

    return templates.TemplateResponse(
        request=request,
        name="gate.html",
        context={
            "plate": "",
            "vehicle": None,
            "journey": None,
            "state": "idle",
            "current_user": user,
            "can_act": False,
            "is_home": False,
        }
    )


@router.get("/lookup", response_class=HTMLResponse)
def gate_lookup(
    request: Request,
    plate: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    plate = (plate or "").strip().upper()
    gatekeeper_station_id = get_gatekeeper_station_id(current_user)

    if not plate:
        return templates.TemplateResponse(
            request=request,
            name="gate.html",
            context={
                "plate": "",
                "vehicle": None,
                "journey": None,
                "state": "idle",
                "current_user": current_user,
                "can_act": False,
                "is_home": False,
            }
        )

    normalized = plate.replace(" ", "")

    vehicle = next(
        (
            v for v in db.query(Vehicle).all()
            if v.registration_number.replace(" ", "").upper() == normalized
        ),
        None
    )

    if not vehicle:
        return templates.TemplateResponse(
            request=request,
            name="gate.html",
            context={
                "plate": plate,
                "vehicle": None,
                "journey": None,
                "state": "unknown_vehicle",
                "current_user": current_user,
                "can_act": True,
                "is_home": False,
            }
        )

    journey = find_current_journey(vehicle.id, db)

    if journey is None:
        state = "no_journey"
        can_act = True
        is_home = False

    elif journey.status == "approved":
        state = "approved"
        is_home = (journey.origin_station_id == gatekeeper_station_id)
        can_act = is_home

    elif journey.status == "out":
        state = "out"
        is_home = (journey.origin_station_id == gatekeeper_station_id)
        can_act = is_home

    else:
        state = "no_journey"
        can_act = True
        is_home = False

    # Record the verify event for pass-throughs (not home gate)
    if state in ("approved", "out") and not is_home:
        record_transaction(
            db,
            current_user,
            journey,
            "verify",
            notes=f"Pass-through at {current_user.gate.name if current_user.gate else 'unknown gate'}"
        )
        db.commit()

    return templates.TemplateResponse(
        request=request,
        name="gate.html",
        context={
            "plate": plate,
            "vehicle": vehicle,
            "journey": journey,
            "state": state,
            "current_user": current_user,
            "can_act": can_act,
            "is_home": is_home,
        }
    )


@router.post("/unauthorized")
def gate_unauthorized(
    plate: str = Form(...),
    reported_by_name: str = Form(...),
    reported_by_staff_number: str = Form(""),
    reason: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    normalized = plate.replace(" ", "").upper()
    vehicles = db.query(Vehicle).all()

    vehicle = next(
        (
            v for v in vehicles
            if v.registration_number.replace(" ", "").upper() == normalized
        ),
        None
    )

    if not vehicle:
        alert = SecurityAlert(
            alert_type="unauthorized_attempt",
            vehicle_id=None,
            journey_id=None,
            severity="high",
            message=f"Unauthorized attempt at gate for unknown plate {plate}. Reason: {reason or 'not specified'}",
            reported_by_name=reported_by_name,
            reported_by_staff_number=reported_by_staff_number or None,
        )

        db.add(alert)

        record_transaction(
            db,
            current_user,
            None,
            "unauthorized_attempt",
            notes=f"Unknown plate {plate}: {reason or 'no reason given'}"
        )

        db.commit()

        return RedirectResponse(url="/gate", status_code=303)

    journey = Journey(
        journey_code=f"UNAUTH-{vehicle.id}-{int(datetime.utcnow().timestamp())}",
        vehicle_id=vehicle.id,
        driver_id=1,
        requesting_department_id=1,
        requested_by_name=reported_by_name,
        requested_by_staff_number=reported_by_staff_number or None,
        origin_station_id=vehicle.home_station_id,
        destination="Unknown (unauthorized attempt)",
        purpose=reason or "Unauthorized movement attempt recorded at gate",
        expected_departure=datetime.utcnow(),
        expected_return=datetime.utcnow(),
        status="unauthorized",
    )

    db.add(journey)
    db.commit()
    db.refresh(journey)

    alert = SecurityAlert(
        alert_type="unauthorized_attempt",
        vehicle_id=vehicle.id,
        journey_id=journey.id,
        severity="high",
        message=f"Unauthorized attempt: {vehicle.registration_number}. Reason: {reason or 'not specified'}",
        reported_by_name=reported_by_name,
        reported_by_staff_number=reported_by_staff_number or None,
    )

    db.add(alert)

    record_transaction(
        db,
        current_user,
        journey,
        "unauthorized_attempt",
        notes=f"{vehicle.registration_number}: {reason or 'no reason given'}"
    )

    db.commit()

    return RedirectResponse(url="/gate", status_code=303)


@router.post("/exit")
def gate_exit(
    journey_id: int = Form(...),
    starting_odometer: int = Form(...),
    fuel_level: str = Form(""),
    spare_wheel: str = Form(""),
    wheel_spanner: str = Form(""),
    jack: str = Form(""),
    lock_chain: str = Form(""),
    vhf_radio: str = Form(""),
    damage_reported: str = Form(""),
    damage_description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    gatekeeper_station_id = get_gatekeeper_station_id(current_user)

    if (
        journey
        and journey.status == "approved"
        and journey.origin_station_id == gatekeeper_station_id
    ):
        journey.status = "out"
        journey.actual_departure = datetime.utcnow()
        journey.starting_odometer = starting_odometer

        inspection_summary = (
            f"Fuel: {fuel_level or 'n/a'}. "
            f"Spare: {'yes' if spare_wheel else 'no'}, "
            f"Spanner: {'yes' if wheel_spanner else 'no'}, "
            f"Jack: {'yes' if jack else 'no'}, "
            f"Chain: {'yes' if lock_chain else 'no'}, "
            f"VHF: {'yes' if vhf_radio else 'no'}."
        )

        if damage_reported:
            inspection_summary += f" DAMAGE: {damage_description or 'reported'}"

        existing = journey.remarks or ""
        journey.remarks = (
            existing + " | " + inspection_summary
        ).strip(" |")

        record_transaction(
            db,
            current_user,
            journey,
            "exit",
            odometer=starting_odometer,
            notes=f"Gate: {current_user.gate.name if current_user.gate else 'unknown'}"
        )

        db.commit()

    return RedirectResponse(url="/gate", status_code=303)


@router.post("/return")
def gate_return(
    journey_id: int = Form(...),
    ending_odometer: int = Form(...),
    fuel_level: str = Form(""),
    damage_reported: str = Form(""),
    damage_description: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    gatekeeper_station_id = get_gatekeeper_station_id(current_user)

    if (
        journey
        and journey.status == "out"
        and journey.origin_station_id == gatekeeper_station_id
    ):
        journey.status = "closed"
        journey.actual_return = datetime.utcnow()
        journey.ending_odometer = ending_odometer

        if journey.starting_odometer is not None:
            journey.distance_km = (
                ending_odometer - journey.starting_odometer
            )

        return_summary = f"Return fuel: {fuel_level or 'n/a'}."

        if damage_reported:
            return_summary += (
                f" DAMAGE ON RETURN: {damage_description or 'reported'}"
            )

        existing = journey.remarks or ""
        journey.remarks = (
            existing + " | " + return_summary
        ).strip(" |")

        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.id == journey.vehicle_id)
            .first()
        )

        if vehicle:
            vehicle.current_odometer = ending_odometer

        record_transaction(
            db,
            current_user,
            journey,
            "return",
            odometer=ending_odometer,
            notes=f"Gate: {current_user.gate.name if current_user.gate else 'unknown'}"
        )

        db.commit()

    return RedirectResponse(url="/gate", status_code=303)


@router.get("/cache")
def gate_cache(db: Session = Depends(get_db)):
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "active")
        .all()
    )

    snapshot = []

    for v in vehicles:
        active = (
            db.query(Journey)
            .filter(
                Journey.vehicle_id == v.id,
                Journey.status.in_(["approved", "out"])
            )
            .order_by(Journey.created_at.desc())
            .first()
        )

        entry = {
            "vehicle_id": v.id,
            "registration_number": v.registration_number,
            "make": v.make,
            "model": v.model,
            "home_station": v.home_station.name if v.home_station else None,
            "current_odometer": v.current_odometer,
            "journey": None,
        }

        if active:
            entry["journey"] = {
                "id": active.id,
                "code": active.journey_code,
                "status": active.status,
                "destination": active.destination,
                "purpose": active.purpose,
                "driver_name": (
                    active.driver.full_name
                    if active.driver else None
                ),
                "department": (
                    active.requesting_department.name
                    if active.requesting_department else None
                ),
                "expected_return": (
                    active.expected_return.isoformat()
                    if active.expected_return else None
                ),
                "origin_station_id": active.origin_station_id,
            }

        snapshot.append(entry)

    return JSONResponse(
        content={
            "generated_at": datetime.utcnow().isoformat(),
            "vehicles": snapshot,
        }
    )


@router.post("/sync")
def sync_offline_actions(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    actions = payload.get("actions", [])
    applied = 0
    failed = 0
    errors = []

    for action in actions:
        try:
            act = action.get("action", "")

            if act.endswith("/gate/exit"):
                journey_id = int(action.get("journey_id"))
                starting_odometer = int(
                    action.get("starting_odometer")
                )

                journey = (
                    db.query(Journey)
                    .filter(Journey.id == journey_id)
                    .first()
                )

                if journey and journey.status == "approved":
                    journey.status = "out"
                    journey.actual_departure = datetime.fromisoformat(
                        action["timestamp"].replace("Z", "+00:00")
                    )
                    journey.starting_odometer = starting_odometer

                    record_transaction(
                        db,
                        current_user,
                        journey,
                        "exit",
                        odometer=starting_odometer,
                        notes="Synced from offline"
                    )

                    db.commit()
                    applied += 1

                else:
                    failed += 1
                    errors.append(
                        f"journey {journey_id} not in approved state"
                    )

            elif act.endswith("/gate/return"):
                journey_id = int(action.get("journey_id"))
                ending_odometer = int(
                    action.get("ending_odometer")
                )

                journey = (
                    db.query(Journey)
                    .filter(Journey.id == journey_id)
                    .first()
                )

                if journey and journey.status == "out":
                    journey.status = "closed"
                    journey.actual_return = datetime.fromisoformat(
                        action["timestamp"].replace("Z", "+00:00")
                    )
                    journey.ending_odometer = ending_odometer

                    if journey.starting_odometer is not None:
                        journey.distance_km = (
                            ending_odometer
                            - journey.starting_odometer
                        )

                    vehicle = (
                        db.query(Vehicle)
                        .filter(Vehicle.id == journey.vehicle_id)
                        .first()
                    )

                    if vehicle:
                        vehicle.current_odometer = ending_odometer

                    record_transaction(
                        db,
                        current_user,
                        journey,
                        "return",
                        odometer=ending_odometer,
                        notes="Synced from offline"
                    )

                    db.commit()
                    applied += 1

                else:
                    failed += 1
                    errors.append(
                        f"journey {journey_id} not in out state"
                    )

            elif act.endswith("/gate/unauthorized"):
                plate = (
                    action.get("plate") or ""
                ).replace(" ", "").upper()

                vehicles = db.query(Vehicle).all()

                vehicle = next(
                    (
                        v for v in vehicles
                        if v.registration_number.replace(
                            " ", ""
                        ).upper() == plate
                    ),
                    None
                )

                if vehicle:
                    journey = Journey(
                        journey_code=(
                            f"UNAUTH-{vehicle.id}-"
                            f"{int(datetime.utcnow().timestamp())}"
                        ),
                        vehicle_id=vehicle.id,
                        driver_id=1,
                        requesting_department_id=1,
                        requested_by_name=action.get(
                            "reported_by_name",
                            "Unknown"
                        ),
                        requested_by_staff_number=(
                            action.get("reported_by_staff_number")
                            or None
                        ),
                        origin_station_id=vehicle.home_station_id,
                        destination="Unknown (unauthorized attempt)",
                        purpose=(
                            action.get("reason")
                            or "Unauthorized movement attempt"
                        ),
                        expected_departure=datetime.utcnow(),
                        expected_return=datetime.utcnow(),
                        status="unauthorized",
                    )

                    db.add(journey)
                    db.commit()
                    db.refresh(journey)

                alert = SecurityAlert(
                    alert_type="unauthorized_attempt",
                    vehicle_id=vehicle.id if vehicle else None,
                    journey_id=journey.id if vehicle else None,
                    severity="high",
                    message=(
                        f"Unauthorized attempt "
                        f"(synced from offline): {plate}"
                    ),
                    reported_by_name=action.get(
                        "reported_by_name"
                    ),
                    reported_by_staff_number=(
                        action.get("reported_by_staff_number")
                        or None
                    ),
                )

                db.add(alert)
                db.commit()
                applied += 1

            else:
                failed += 1
                errors.append(
                    f"unknown action type: {act}"
                )

        except Exception as e:
            db.rollback()
            failed += 1
            errors.append(
                f"{action.get('action', '?')}: {str(e)}"
            )

    return {
        "applied": applied,
        "failed": failed,
        "errors": errors
    }