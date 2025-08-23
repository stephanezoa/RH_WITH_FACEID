from pydantic import BaseModel
from enum import Enum
from typing import Optional

class AffectationStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"

class AffectationBase(BaseModel):
    personnel_id: int
    code_region: str
    status: AffectationStatus = AffectationStatus.PENDING

class AffectationCreate(AffectationBase):
    pass

class Affectation(AffectationBase):
    id: int

    class Config:
        from_attributes = True



class AffectationUpdate(BaseModel):
    code_region: str
    status: str