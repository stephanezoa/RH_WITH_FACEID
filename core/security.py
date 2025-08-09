from datetime import datetime, timedelta
from jose import jwt, JWTError
from pydantic_settings import BaseSettings
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from core.database import get_db
from models.user import User
from enum import Enum
import logging

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    JWT_SECRET: str = "your-secret-key"  # Remplacer par une clé secrète sécurisée en production
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Convertir le rôle en chaîne si c'est un Enum
    if "role" in to_encode and isinstance(to_encode["role"], Enum):
        to_encode["role"] = to_encode["role"].value
    elif "role" in to_encode:
        to_encode["role"] = str(to_encode["role"])  # Convertir en chaîne par précaution
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.info(f"Jeton JWT créé pour {to_encode['sub']}, rôle : {to_encode['role']}")
    return encoded_jwt

def get_password_hash(password: str) -> str:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    result = pwd_context.verify(plain_password, hashed_password)
    logger.info(f"Vérification du mot de passe : {'succès' if result else 'échec'}")
    return result

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    request: Request = None,
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Vérifier si le jeton est dans le cookie
        if not token and request:
            token = request.cookies.get("access_token")
        if not token:
            logger.error("Aucun jeton fourni")
            raise credentials_exception
        # Supprimer "Bearer " si présent (par précaution)
        token = token.replace("Bearer ", "") if token.startswith("Bearer ") else token
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        nom_utilisateur: str = payload.get("sub")
        role: str = payload.get("role")
        if nom_utilisateur is None or role is None:
            logger.error(f"Payload JWT invalide : sub={nom_utilisateur}, role={role}")
            raise credentials_exception
        logger.info(f"Jeton décodé : sub={nom_utilisateur}, role={role}")
    except JWTError as e:
        logger.error(f"Erreur JWT : {str(e)}")
        raise credentials_exception from e
    utilisateur = db.query(User).filter(User.nom_utilisateur == nom_utilisateur).first()
    if utilisateur is None:
        logger.error(f"Utilisateur non trouvé : {nom_utilisateur}")
        raise credentials_exception
    # Vérifier que le rôle dans la base correspond au rôle du jeton
    if utilisateur.role != role:
        logger.error(f"Incohérence de rôle : base={utilisateur.role}, jeton={role}")
        raise credentials_exception
    return utilisateur