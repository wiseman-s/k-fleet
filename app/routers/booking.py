from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import decode_token
from app.core.templates import get_templates
from app.models.journey import Journey
from app.models.user import User

router = APIRouter(prefix="/booking", tags=["Booking"])

templates = get_templates()


def _current_user(request: Request, db: Session):
    """Return the logged-in user, or None. Used for HTML pages where we want
    to redirect to login rather than return a JSON 401."""
    token = request.cookies.get("kfleet_token")
    if not token:
        return None
    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.is_active:
        return None
    return user


@router.get("", response_class=HTMLResponse)
def booking_home(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if user.role == "gatekeeper":
        return RedirectResponse(url="/gate", status_code=303)

    my_requests = (
        db.query(Journey)
        .filter(Journey.requested_by_user_id == user.id)
        .order_by(desc(Journey.created_at))
        .limit(20)
        .all()
    )

    active_count = sum(
        1 for j in my_requests
        if j.status in ("requested", "approved", "out")
    )

    return templates.TemplateResponse(
        request=request,
        name="booking.html",
        context={
            "current_user": user,
            "my_requests": my_requests,
            "active_count": active_count,
        }
    )


@router.get("/new", response_class=HTMLResponse)
def booking_new(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
    if user.role == "gatekeeper":
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
            "redirect_to": "/booking",
        }
    )