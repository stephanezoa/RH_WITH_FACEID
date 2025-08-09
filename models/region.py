from sqlalchemy import Column, String
from core.database import Base

class Region(Base):
    __tablename__ = "regions"
    code = Column(String, primary_key=True)
    nom = Column(String, nullable=False)