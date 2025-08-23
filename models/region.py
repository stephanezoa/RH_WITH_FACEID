from sqlalchemy import Column, String
from core.database import Base

class Region(Base):
    __tablename__ = "regions"
    code = Column(String, primary_key=True)
    nom = Column(String, nullable=False)

# Initialisation des 10 régions du Cameroun (à insérer dans la base via un script d'initialisation)
CAMEROON_REGIONS = [
    {"code": "AD", "nom": "Adamaoua"},
    {"code": "CE", "nom": "Centre"},
    {"code": "ES", "nom": "Est"},
    {"code": "EN", "nom": "Extrême-Nord"},
    {"code": "LI", "nom": "Littoral"},
    {"code": "NO", "nom": "Nord"},
    {"code": "NW", "nom": "Nord-Ouest"},
    {"code": "OU", "nom": "Ouest"},
    {"code": "SU", "nom": "Sud"},
    {"code": "SW", "nom": "Sud-Ouest"}
]