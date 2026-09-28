from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, date

from app.core.database import get_db
from app.core.security import require_roles
from app.models.vehicle import Vehicle
from app.models.journey import Journey
from app.models.driver import Driver
from app.models.user import User

router = APIRouter(tags=["Dashboard"])

templates = Jinja2Templates(directory="app/templates")


def build_dashboard_data(db: Session):
    now = datetime.utcnow()
    today_start = datetime.combine(date.today(), datetime.min.time())

    all_vehicles = db.query(Vehicle).all()

    # Active journeys = status "out" (vehicle on the road)
    active_journeys = db.query(Journey).filter(Journey.status == "out").all()
    active_by_vehicle = {j.vehicle_id: j for j in active_journeys}

    vehicle_statuses = []
    counts = {"parked": 0, "on_journey": 0, "overdue": 0}

    for v in all_vehicles:
        journey = active_by_vehicle.get(v.id)
        if not journey:
            counts["parked"] += 1
            vehicle_statuses.append({
                "vehicle_id": v.id,
                "registration_number": v.registration_number,
                "make": v.make,
                "model": v.model,
                "home_station": v.home_station.name if v.home_station else None,
                "status": "parked",
                "journey_code": None,
                "driver_name": None,
                "destination": None,
                "expected_return": None,
            })
        else:
            is_overdue = journey.expected_return and journey.expected_return < now
            status = "overdue" if is_overdue else "on_journey"
            counts[status] += 1
            vehicle_statuses.append({
                "vehicle_id": v.id,
                "registration_number": v.registration_number,
                "make": v.make,
                "model": v.model,
                "home_station": v.home_station.name if v.home_station else None,
                "status": status,
                "journey_code": journey.journey_code,
                "driver_name": journey.driver.full_name if journey.driver else None,
                "destination": journey.destination,
                "expected_return": journey.expected_return,
            })

    pending = db.query(Journey).filter(Journey.status == "pending").count()
    approved = db.query(Journey).filter(Journey.status == "approved").count()
    out_count = db.query(Journey).filter(Journey.status == "out").count()
    closed_today = db.query(Journey).filter(
        Journey.status == "closed",
        Journey.actual_return >= today_start
    ).count()

    # Live activity: active journeys + those closed today
    active_statuses = ["pending", "approved", "out"]
    recent = (
        db.query(Journey)
        .filter(
            (Journey.status.in_(active_statuses)) |
            ((Journey.status == "closed") & (Journey.actual_return >= today_start))
        )
        .order_by(Journey.created_at.desc())
        .limit(20)
        .all()
    )
    recent_journeys = []
    for j in recent:
        recent_journeys.append({
            "id": j.id,
            "journey_code": j.journey_code,
            "registration_number": j.vehicle.registration_number if j.vehicle else None,
            "driver_name": j.driver.full_name if j.driver else None,
            "department": j.requesting_department.name if j.requesting_department else None,
            "destination": j.destination,
            "status": j.status,
        })

    supervisors = db.query(Driver).filter(
        Driver.is_supervisor == True,  # noqa: E712
        Driver.is_active == True        # noqa: E712
    ).all()

    from app.models.security_alert import SecurityAlert

    return {
        "vehicles_total": len(all_vehicles),
        "vehicles_parked": counts["parked"],
        "vehicles_on_journey": counts["on_journey"],
        "vehicles_overdue": counts["overdue"],
        "journeys_pending_approval": pending,
        "journeys_approved": approved,
        "journeys_out": out_count,
        "journeys_closed_today": closed_today,
        "vehicles": vehicle_statuses,
        "recent_journeys": recent_journeys,
        "supervisors": supervisors,
        "unresolved_alerts_count": db.query(SecurityAlert).filter(SecurityAlert.resolved == False).count(),  # noqa: E712
        "recent_alerts": db.query(SecurityAlert).filter(SecurityAlert.resolved == False).order_by(SecurityAlert.created_at.desc()).limit(10).all(),
    }


@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    return build_dashboard_data(db)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    data = build_dashboard_data(db)
    data["current_user"] = current_user
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"data": data}
    )