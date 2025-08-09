from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import verify_password, create_access_token
from models.user import User
import logging

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    nom_utilisateur: str = Form(...),
    mot_de_passe: str = Form(...),
    db: Session = Depends(get_db)
):
    utilisateur = db.query(User).filter(User.nom_utilisateur == nom_utilisateur).first()
    if not utilisateur or not verify_password(mot_de_passe, utilisateur.mot_de_passe_hash):
        logger.error(f"Échec de la connexion pour {nom_utilisateur}: utilisateur non trouvé ou mot de passe incorrect")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nom d'utilisateur ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Loguer le rôle de l'utilisateur
    logger.info(f"Utilisateur connecté : {utilisateur.nom_utilisateur}, rôle : {utilisateur.role}")

    access_token = create_access_token(
        data={"sub": utilisateur.nom_utilisateur, "role": utilisateur.role, "code_region": utilisateur.code_region}
    )
    # Définir l'URL de redirection en fonction du rôle
    if utilisateur.role == "SUPER_USER":
        redirect_url = "/api/users/admin_dashboard"
    elif utilisateur.role == "DRH":
        redirect_url = "/api/users/drh_dashboard"
    elif utilisateur.role == "RH":
        redirect_url = "/api/users/rh_dashboard"
    else:
        logger.error(f"Rôle non valide pour {utilisateur.nom_utilisateur}: {utilisateur.role}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rôle utilisateur non valide"
        )

    logger.info(f"Redirection vers : {redirect_url}")

    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax")
    return response