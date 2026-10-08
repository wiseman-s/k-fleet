"""Helper for writing journey audit entries.

Usage from anywhere that changes a journey:
    from app.services.audit import log_journey_action
    log_journey_action(db, journey, current_user, "approved", remarks="...")
    # then db.commit() in the caller
"""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.journey import Journey
from app.models.journey_audit import JourneyAudit
from app.models.user import User


def log_journey_action(
    db: Session,
    journey: Journey,
    current_user: Optional[User],
    action: str,
    field_changes: Optional[Dict[str, Any]] = None,
    remarks: Optional[str] = None,
) -> JourneyAudit:
    """Record an audit entry for a journey action. Does NOT commit; caller commits."""

    entry = JourneyAudit(
        journey_id=journey.id,
        user_id=current_user.id if current_user else None,
        user_name=current_user.full_name if current_user else None,
        action=action,
        field_changes=json.dumps(field_changes) if field_changes else None,
        remarks=remarks,
    )
    db.add(entry)
    return entry


def diff_fields(old_dict: Dict[str, Any], new_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Return a dict of {field: [old, new]} for fields that changed."""
    changes = {}
    for key in new_dict:
        old_val = old_dict.get(key)
        new_val = new_dict.get(key)
        if old_val != new_val:
            changes[key] = [old_val, new_val]
    return changes