from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.templates import get_templates
from app.models.journey import Journey
from app.models.user import User

router = APIRouter(prefix="/booking", tags=["Booking"])

templates = get_templates()


def _is_staff_role(role: str) -> bool:
    """Any role except gatekeeper can use the booking portal."""
    return role != "gatekeeper"


@router.get("", response_class=HTMLResponse)
def booking_home(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_staff_role(current_user.role):
        return RedirectResponse(url="/gate", status_code=303)

    # Recent requests by this user
    my_requests = (
        db.query(Journey)
        .filter(Journey.requested_by_user_id == current_user.id)
        .order_by(desc(Journey.created_at))
        .limit(20)
        .all()
    )

    # Active ones (still in progress)
    active_count = sum(
        1 for j in my_requests
        if j.status in ("requested", "approved", "out")
    )

    return templates.TemplateResponse(
        request=request,
        name="booking.html",
        context={
            "current_user": current_user,
            "my_requests": my_requests,
            "active_count": active_count,
        }
    )


@router.get("/new", response_class=HTMLResponse)
def booking_new(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not _is_staff_role(current_user.role):
        return RedirectResponse(url="/gate", status_code=303)

    from app.models.department import Department
    from app.models.station import Station

    departments = db.query(Department).filter(Department.is_active == True).all()  # noqa: E712
    stations = db.query(Station).filter(Station.is_active == True).all()  # noqa: E712

    return templates.TemplateResponse(
        request=request,
        name="new_journey.html",
        context={
            "departments": departments,
            "stations": stations,
            "redirect_to": "/booking",  # so the form posts and returns to booking
        }
    )