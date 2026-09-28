from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.core.security import require_roles
from app.models.vehicle import Vehicle
from app.models.gps_event import GpsEvent
from app.models.journey import Journey
from app.models.user import User

router = APIRouter(prefix="/tracking", tags=["Tracking"])


@router.get("/live")
def live_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    """Return the latest known position for each vehicle that has a Traccar device."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.traccar_device_id.isnot(None)
    ).all()

    result = []

    for v in vehicles:
        latest = (
            db.query(GpsEvent)
            .filter(GpsEvent.vehicle_id == v.id)
            .order_by(desc(GpsEvent.recorded_at))
            .first()
        )

        active = (
            db.query(Journey)
            .filter(
                Journey.vehicle_id == v.id,
                Journey.status == "out"
            )
            .order_by(desc(Journey.created_at))
            .first()
        )

        if latest:
            # Determine the vehicle's current status
            status = "parked"

            if active:
                overdue = (
                    active.expected_return
                    and active.expected_return < datetime.utcnow()
                )
                status = "overdue" if overdue else "out"

            result.append({
                "vehicle_id": v.id,
                "registration_number": v.registration_number,
                "make": v.make,
                "model": v.model,
                "latitude": latest.latitude,
                "longitude": latest.longitude,
                "speed": latest.speed,
                "course": latest.course,
                "accuracy": latest.accuracy,
                "last_seen": (
                    latest.device_time.isoformat()
                    if latest.device_time else None
                ),
                "recorded_at": (
                    latest.recorded_at.isoformat()
                    if latest.recorded_at else None
                ),
                "journey_code": (
                    active.journey_code
                    if active else None
                ),
                "destination": (
                    active.destination
                    if active else None
                ),
                "driver_name": (
                    active.driver.full_name
                    if active and active.driver else None
                ),
                "is_out": bool(active),
                "status": status,
            })

    return {
        "count": len(result),
        "vehicles": result
    }


@router.get("/vehicle/{vehicle_id}/history")
def vehicle_history(
    vehicle_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    """Return recent GPS events for a vehicle, newest first."""
    events = (
        db.query(GpsEvent)
        .filter(GpsEvent.vehicle_id == vehicle_id)
        .order_by(desc(GpsEvent.recorded_at))
        .limit(limit)
        .all()
    )

    return {
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "latitude": e.latitude,
                "longitude": e.longitude,
                "speed": e.speed,
                "device_time": (
                    e.device_time.isoformat()
                    if e.device_time else None
                ),
                "recorded_at": (
                    e.recorded_at.isoformat()
                    if e.recorded_at else None
                ),
                "journey_id": e.journey_id,
            }
            for e in events
        ]
    }


# ---------------- Today's GPS trail ----------------

@router.get("/vehicle/{vehicle_id}/today")
def vehicle_track_today(
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    """Return all GPS events for a vehicle from today, oldest first — used for the map trail."""
    from datetime import datetime, time, timedelta

    today_start = datetime.combine(
        datetime.utcnow().date(),
        time.min
    )

    events = (
        db.query(GpsEvent)
        .filter(
            GpsEvent.vehicle_id == vehicle_id,
            GpsEvent.recorded_at >= today_start,
        )
        .order_by(GpsEvent.recorded_at.asc())
        .all()
    )

    return {
        "vehicle_id": vehicle_id,
        "count": len(events),
        "points": [
            {
                "lat": e.latitude,
                "lng": e.longitude,
                "t": e.recorded_at.isoformat()
            }
            for e in events
        ],
    }


@router.get("/trails/today")
def all_trails_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("admin", "fleet_officer", "supervisor")
    ),
):
    """Return today's GPS trail for every tracked vehicle, in one call."""
    from datetime import datetime, time, timedelta

    today_start = datetime.combine(
        datetime.utcnow().date(),
        time.min
    )

    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.traccar_device_id.isnot(None))
        .all()
    )

    result = {}

    for v in vehicles:
        events = (
            db.query(GpsEvent)
            .filter(
                GpsEvent.vehicle_id == v.id,
                GpsEvent.recorded_at >= today_start,
            )
            .order_by(GpsEvent.recorded_at.asc())
            .all()
        )

        result[v.id] = [
            {
                "lat": e.latitude,
                "lng": e.longitude
            }
            for e in events
        ]

    return result