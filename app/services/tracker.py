"""
Background poller that reads positions from Traccar and stores them in K-FLEET.

Runs as an asyncio task started at application startup.
For each online device whose traccar_device_id matches a vehicle, we store a GpsEvent.
If the vehicle has an active journey ("out"), the event is linked to that journey.
"""

import asyncio
import logging
import math
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import TRACCAR_POLL_SECONDS
from app.core.database import SessionLocal
from app.models.vehicle import Vehicle
from app.models.journey import Journey
from app.models.gps_event import GpsEvent
from app.models.station import Station
from app.models.security_alert import SecurityAlert
from app.services import traccar

logger = logging.getLogger(__name__)


def _get_active_journey(db: Session, vehicle_id: int):
    return (
        db.query(Journey)
        .filter(
            Journey.vehicle_id == vehicle_id,
            Journey.status == "out"
        )
        .order_by(Journey.created_at.desc())
        .first()
    )


def haversine_meters(lat1, lon1, lat2, lon2):
    """Distance between two lat/lng points in meters."""
    R = 6371000.0  # earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


def check_geofence(db: Session, vehicle, lat, lng, journey):
    """Raise an alert if the vehicle is outside its home station's geofence
    and there is no active journey."""

    if journey is not None:
        return  # vehicle is legally out on a journey

    station = vehicle.home_station

    if (
        not station
        or station.latitude is None
        or station.longitude is None
    ):
        return

    distance = haversine_meters(
        lat,
        lng,
        station.latitude,
        station.longitude
    )

    radius = station.radius_meters or 3000.0

    if distance <= radius:
        return

    # Already alerted recently? Avoid duplicates within the last hour.
    from datetime import timedelta

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    existing = (
        db.query(SecurityAlert)
        .filter(
            SecurityAlert.vehicle_id == vehicle.id,
            SecurityAlert.alert_type == "geofence_violation",
            SecurityAlert.created_at >= one_hour_ago,
        )
        .first()
    )

    if existing:
        return

    alert = SecurityAlert(
        alert_type="geofence_violation",
        vehicle_id=vehicle.id,
        journey_id=None,
        severity="high",
        message=(
            f"{vehicle.registration_number} is {distance/1000:.1f} km from "
            f"{station.name} with no active journey "
            f"(allowed: {radius/1000:.1f} km)."
        ),
    )

    db.add(alert)


def poll_once() -> int:
    """Fetch positions from Traccar, store new ones. Returns count of events stored."""
    positions = traccar.fetch_positions()

    if not positions:
        return 0

    devices = {
        d["id"]: d
        for d in traccar.fetch_devices()
    }

    db: Session = SessionLocal()
    stored = 0

    try:
        for pos in positions:
            device_id = pos.get("deviceId")
            device = devices.get(device_id)

            if not device:
                continue

            unique_id = device.get("uniqueId")

            if not unique_id:
                continue

            # Match device uniqueId to a vehicle's traccar_device_id
            vehicle = (
                db.query(Vehicle)
                .filter(
                    Vehicle.traccar_device_id == unique_id
                )
                .first()
            )

            if not vehicle:
                continue

            # Skip if we already stored this exact position (same deviceTime)
            device_time_raw = (
                pos.get("deviceTime")
                or pos.get("fixTime")
            )

            device_time = None

            if device_time_raw:
                try:
                    device_time = datetime.fromisoformat(
                        device_time_raw.replace("Z", "+00:00")
                    )
                except Exception:
                    device_time = None

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
                    continue

            journey = _get_active_journey(
                db,
                vehicle.id
            )

            event = GpsEvent(
                vehicle_id=vehicle.id,
                journey_id=journey.id if journey else None,
                latitude=pos.get("latitude"),
                longitude=pos.get("longitude"),
                altitude=pos.get("altitude"),
                speed=pos.get("speed"),
                course=pos.get("course"),
                accuracy=pos.get("accuracy"),
                device_time=device_time,
            )

            db.add(event)
            stored += 1

            # Geofence check
            check_geofence(
                db,
                vehicle,
                pos.get("latitude"),
                pos.get("longitude"),
                journey,
            )

        db.commit()

    except Exception as e:
        db.rollback()
        logger.warning(
            "tracker poll_once error: %s",
            e
        )

    finally:
        db.close()

    return stored


async def run_poller():
    """Runs forever, sleeping TRACCAR_POLL_SECONDS between iterations."""
    logger.info(
        "Traccar poller started (interval %ss)",
        TRACCAR_POLL_SECONDS
    )

    while True:
        try:
            n = poll_once()

            if n:
                logger.info(
                    "Stored %s new GPS event(s)",
                    n
                )

        except Exception as e:
            logger.warning(
                "poller loop error: %s",
                e
            )

        await asyncio.sleep(
            TRACCAR_POLL_SECONDS
        )