from sqlalchemy import Column, Integer, String
from core.database import Base

class Personnel(Base):
    __tablename__ = "personnels"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    prenom = Column(String)
    sexe = Column(String)
    age = Column(Integer)
    grade = Column(String)
    matricule = Column(String, unique=True, index=True)
    taille = Column(Integer)
    photo_url = Column(String, nullable=True)
    code_region = Column(String)