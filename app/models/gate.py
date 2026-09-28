from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Gate(Base):
    __tablename__ = "gates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)               # "Main Entrance", "Gate A"
    code = Column(String, unique=True, nullable=False)  # "GATE-UT-01"
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    station = relationship("Station")