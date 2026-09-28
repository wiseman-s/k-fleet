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


# ---------------------------------------------------------------------
# Ingest endpoint — used by Traccar's forwarder (running on the laptop)
# to push positions to K-FLEET running in the cloud.
# ---------------------------------------------------------------------

from fastapi import Request
from datetime import datetime
from app.models.vehicle import Vehicle
from app.models.gps_event import GpsEvent
from app.models.journey import Journey
from sqlalchemy import desc
import logging

logger = logging.getLogger(__name__)


@router.post("/ingest")
async def ingest_position(request: Request, db: Session = Depends(get_db)):
    """Receive a position from Traccar's forwarder.

    Traccar's `forward.type=json` sends a payload like:
    {
      "position": {
        "deviceId": 1, "protocol": "osmand",
        "deviceTime": "2026-09-28T11:50:25.000+00:00",
        "fixTime": "...", "valid": true,
        "latitude": -0.9218, "longitude": 36.9686,
        "altitude": 1694.1, "speed": 0.0, "course": 0.0,
        "accuracy": 20.0, ...
      },
      "device": {
        "id": 1, "name": "KAA 123X", "uniqueId": "KAA123X",
        ...
      }
    }

    We match the device's uniqueId to a vehicle's traccar_device_id,
    and store a GpsEvent. If the vehicle has an active journey ("out"),
    the event is linked to that journey.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.warning("ingest: bad JSON payload: %s", e)
        return {"status": "error", "reason": "invalid json"}

    # Traccar's JSON forwarder can send {position: {...}, device: {...}}
    # or just a position object, depending on version. Handle both.
    position = payload.get("position") if isinstance(payload, dict) else None
    device = payload.get("device") if isinstance(payload, dict) else None

    if position is None:
        # Fall back to treating the whole body as the position
        position = payload

    unique_id = None
    if device:
        unique_id = device.get("uniqueId") or device.get("name")
    if not unique_id:
        # Some forwarders include only deviceId; look it up via Traccar API?
        # For MVP, we require uniqueId.
        unique_id = str(position.get("deviceId")) if position.get("deviceId") else None

    if not unique_id:
        return {"status": "error", "reason": "no device identifier"}

    # Match to a vehicle
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.traccar_device_id == unique_id)
        .first()
    )
    if not vehicle:
        logger.info("ingest: no vehicle matches device %s", unique_id)
        return {"status": "ignored", "reason": f"no vehicle for {unique_id}"}

    # Parse timestamps
    device_time = None
    raw_time = position.get("deviceTime") or position.get("fixTime")
    if raw_time:
        try:
            device_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
        except Exception:
            device_time = None

    # Skip duplicates
    if device_time:
        existing = (
            db.query(GpsEvent)
            .filter(
                GpsEvent.vehicle_id == vehicle.id,
                GpsEvent.device_time == device_time,
            )
            .first()
        )
        if existing:
            return {"status": "duplicate"}

    # Find active journey
    active = (
        db.query(Journey)
        .filter(Journey.vehicle_id == vehicle.id, Journey.status == "out")
        .order_by(desc(Journey.created_at))
        .first()
    )

    event = GpsEvent(
        vehicle_id=vehicle.id,
        journey_id=active.id if active else None,
        latitude=position.get("latitude"),
        longitude=position.get("longitude"),
        altitude=position.get("altitude"),
        speed=position.get("speed"),
        course=position.get("course"),
        accuracy=position.get("accuracy"),
        device_time=device_time,
    )
    db.add(event)
    db.commit()

    return {"status": "stored", "vehicle": vehicle.registration_number, "event_id": event.id}