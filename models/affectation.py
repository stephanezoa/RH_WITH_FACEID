from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum as PyEnum

Base = declarative_base()

class AffectationStatus(PyEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"

class Affectation(Base):
    __tablename__ = "affectations"
    id = Column(Integer, primary_key=True, index=True)
    personnel_id = Column(Integer, ForeignKey("personnels.id"), nullable=False)
    code_region = Column(String, nullable=False)
    status = Column(Enum(AffectationStatus), nullable=False, default=AffectationStatus.PENDING)