from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from models import affectation, region, personnel
from models.affectation import Affectation
from models.personnel import Personnel
from models.region import Region
from models.user import User
from schemas.affectation import AffectationUpdate
from core.security import get_current_user
from models import user
import logging

router = APIRouter(prefix="/api/affectations", tags=["Affectations"])
templates = Jinja2Templates(directory="templates")
logger = logging.getLogger(__name__)


@router.get("/{affectation_id}/edit", response_class=HTMLResponse)
async def edit_affectation_form(
        request: Request,
        affectation_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "DRH":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux DRH")

    affectation = db.query(Affectation).filter(Affectation.id == affectation_id).first()
    if not affectation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affectation non trouvée")

    personnel = db.query(Personnel).filter(Personnel.id == affectation.personnel_id).first()
    if not personnel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel non trouvé")

    regions = db.query(Region).all()
    return templates.TemplateResponse(
        "edit_affectation.html",
        {
            "request": request,
            "affectation": affectation,
            "personnel": personnel,
            "regions": regions,
            "current_user": current_user
        }
    )


@router.post("/{affectation_id}/edit")
async def update_affectation(
        affectation_id: int,
        affectation_update: AffectationUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "DRH":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux DRH")

    affectation = db.query(Affectation).filter(Affectation.id == affectation_id).first()
    if not affectation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affectation non trouvée")

    affectation.code_region = affectation_update.code_region
    affectation.status = affectation_update.status
    db.commit()
    logger.info(f"Affectation {affectation_id} mise à jour par {current_user.nom_utilisateur}")
    return {"detail": "Affectation mise à jour avec succès"}