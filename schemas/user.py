from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum

class Role(str, Enum):
    SUPER_USER = "SUPER_USER"
    DRH = "DRH"
    RH = "RH"

class UserBase(BaseModel):
    nom_utilisateur: str
    email: EmailStr
    role: Role
    code_region: Optional[str] = None

class UserCreate(UserBase):
    mot_de_passe: str

class User(UserBase):
    id: int

    class Config:
        from_attributes = True