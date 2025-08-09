

from sqlalchemy import Column, Integer, String
from enum import Enum as SQLEnum
from core.database import Base

class Role(str, SQLEnum):
    SUPER_USER = "SUPER_USER"
    DRH = "DRH"
    RH = "RH"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nom_utilisateur = Column(String, unique=True, index=True)
    mot_de_passe_hash = Column(String)
    email = Column(String, unique=True, index=True)
    role = Column(String)  # Stocke la valeur de l'Enum comme chaîne
    code_region = Column(String, nullable=True)