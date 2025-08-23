from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from core.database import Base

class AffectationStatus:
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"

class Affectation(Base):
    __tablename__ = "affectations"

    id = Column(Integer, primary_key=True, index=True)
    personnel_id = Column(Integer, ForeignKey("personnels.id"), nullable=False)
    code_region = Column(String, ForeignKey("regions.code"), nullable=False)
    status = Column(String, nullable=False, default=AffectationStatus.PENDING)
    created_at = Column(DateTime, nullable=False, default=func.now())
    confidence = Column(Float, nullable=True)
    confidence_color = Column(String, nullable=True)
    confidence_message = Column(String, nullable=True)