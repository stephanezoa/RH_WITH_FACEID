from sqlalchemy import Column, Integer, String, Enum
from core.database import Base
from enum import Enum as PyEnum

class MilitaryGrade(PyEnum):
    SOLDAT = "Soldat"
    CAPORAL = "Caporal"
    CAPORAL_CHEF = "Caporal-Chef"
    SERGENT = "Sergent"
    SERGENT_CHEF = "Sergent-Chef"
    ADJUDANT = "Adjudant"
    ADJUDANT_CHEF = "Adjudant-Chef"
    LIEUTENANT = "Lieutenant"
    CAPITAINE = "Capitaine"
    COMMANDANT = "Commandant"
    LIEUTENANT_COLONEL = "Lieutenant-Colonel"
    COLONEL = "Colonel"

class Personnel(Base):
    __tablename__ = "personnels"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    prenom = Column(String)
    sexe = Column(String)
    age = Column(Integer)
    grade = Column(Enum(MilitaryGrade), nullable=False)
    matricule = Column(String, unique=True, index=True)
    taille = Column(Integer)
    photo_url = Column(String, nullable=True)
    code_region = Column(String)
    face_token = Column(String, nullable=True)