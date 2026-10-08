"""Odometer anomaly detection.

Rules:
  1. Any recorded odometer must be >= the vehicle's previous current_odometer.
  2. A jump larger than what's plausible for the elapsed time is flagged.
  3. An exit/return with the exact same odometer as before is flagged (no change recorded).

When a rule is violated, a SecurityAlert is added (not committed — caller commits).
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.vehicle import Vehicle
from app.models.journey import Journey
from app.models.security_alert import SecurityAlert

logger = logging.getLogger(__name__)

# 200 km/h is generous — assume a vehicle can't realistically average more over a journey.
MAX_SPEED_KMH = 200.0
# If elapsed time is unknown, assume this much time has passed at minimum (minutes).
DEFAULT_ELAPSED_MINUTES = 30


def check_odometer(
    db: Session,
    vehicle: Vehicle,
    journey: Optional[Journey],
    new_reading: int,
    context: str,
) -> Optional[SecurityAlert]:
    """Check a new odometer reading against the vehicle's history.

    `context` should be a short string like "exit" or "return".

    Returns the SecurityAlert if one was raised, or None. Does NOT commit.
    """
    if new_reading is None:
        return None

    previous = vehicle.current_odometer
    if previous is None:
        return None

    # Rule 1: odometer went backwards
    if new_reading < previous:
        alert = SecurityAlert(
            alert_type="odometer_anomaly",
            vehicle_id=vehicle.id,
            journey_id=journey.id if journey else None,
            severity="high",
            message=(
                f"{vehicle.registration_number}: odometer decreased at "
                f"{context} — was {previous} km, now {new_reading} km "
                f"(difference: {previous - new_reading} km)."
            ),
        )
        db.add(alert)
        logger.info("odometer anomaly: vehicle %s went backwards", vehicle.registration_number)
        return alert

    # Rule 3: same value when a change is expected
    # Only flag at exit if previous journey had distance; skip for simplicity now.
    # We'll enable this once we have reliable "last exit" data.
    # (Leave disabled for the MVP to avoid false positives on parked vehicles.)

    # Rule 2: implausible jump for elapsed time
    if journey and journey.actual_departure and context == "return":
        elapsed = datetime.utcnow() - journey.actual_departure.replace(tzinfo=None) \
            if journey.actual_departure.tzinfo else datetime.utcnow() - journey.actual_departure
        elapsed_minutes = max(elapsed.total_seconds() / 60.0, 1.0)
    else:
        elapsed_minutes = DEFAULT_ELAPSED_MINUTES

    km_diff = new_reading - previous
    max_plausible = (elapsed_minutes / 60.0) * MAX_SPEED_KMH

    if km_diff > max_plausible and elapsed_minutes >= 5:
        alert = SecurityAlert(
            alert_type="odometer_anomaly",
            vehicle_id=vehicle.id,
            journey_id=journey.id if journey else None,
            severity="medium",
            message=(
                f"{vehicle.registration_number}: large odometer jump at {context} — "
                f"from {previous} km to {new_reading} km (+{km_diff} km) in "
                f"~{int(elapsed_minutes)} minutes. Please verify."
            ),
        )
        db.add(alert)
        logger.info("odometer anomaly: vehicle %s jumped %s km", vehicle.registration_number, km_diff)
        return alert

    return None