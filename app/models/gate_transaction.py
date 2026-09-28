from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class GateTransaction(Base):
    __tablename__ = "gate_transactions"

    id = Column(Integer, primary_key=True, index=True)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    transaction_type = Column(String, nullable=False)
    # exit, return, verify, unauthorized_attempt

    odometer = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    gate = relationship("Gate")
    journey = relationship("Journey")
    user = relationship("User")