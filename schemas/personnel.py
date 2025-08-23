from pydantic import BaseModel
from enum import Enum
from typing import Optional

class Sexe(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class PersonnelBase(BaseModel):
    nom: str
    prenom: str
    sexe: Sexe
    age: int
    grade: str
    matricule: str
    taille: int
    code_region: str
    photo_url: Optional[str] = None
    face_token: Optional[str] = None  # Nouveau champ pour face_token

class PersonnelCreate(PersonnelBase):
    pass

class Personnel(PersonnelBase):
    id: int

    class Config:
        from_attributes = True