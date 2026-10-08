from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class JourneyAudit(Base):
    __tablename__ = "journey_audit"

    id = Column(Integer, primary_key=True, index=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user_name = Column(String, nullable=True)  # snapshot, in case user is deleted

    action = Column(String, nullable=False)
    # created, modified, approved, rejected, exit, return, closed, unauthorized_attempt

    field_changes = Column(Text, nullable=True)  # JSON string, e.g. {"destination": ["old", "new"]}
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    journey = relationship("Journey")
    user = relationship("User")