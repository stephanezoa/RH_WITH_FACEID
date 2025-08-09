from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_password_hash, get_current_user
from models.user import User
from models.personnel import Personnel
from models.region import Region
from models.affectation import Affectation, AffectationStatus
import os
from core.config import settings
import logging

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/admin_dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à admin_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à admin_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/drh_dashboard", response_class=HTMLResponse)
async def drh_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à drh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé à drh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return templates.TemplateResponse(
        "drh_dashboard.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/rh_dashboard", response_class=HTMLResponse)
async def rh_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à rh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à rh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    return templates.TemplateResponse(
        "rh_dashboard.html",
        {"request": request, "current_user": current_user}
    )

@router.get("/create_user", response_class=HTMLResponse)
async def create_user_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès au formulaire create_user par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role not in ["SUPER_USER", "DRH"]:
        logger.error(f"Accès refusé au formulaire create_user pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    regions = db.query(Region).all()
    return templates.TemplateResponse(
        "create_user.html",
        {"request": request, "regions": regions, "current_user": current_user}
    )

@router.post("/create_user", response_class=HTMLResponse)
async def create_user(
    nom_utilisateur: str = Form(...),
    email: str = Form(...),
    mot_de_passe: str = Form(...),
    role: str = Form(...),
    code_region: str | None = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Tentative de création d'utilisateur par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role == "SUPER_USER":
        if role not in ["DRH", "RH"]:
            return templates.TemplateResponse("create_user.html",
                                             {"request": request, "regions": db.query(Region).all(),
                                              "current_user": current_user,
                                              "error": "Le Super Utilisateur peut uniquement créer des DRH ou RH"})
    elif current_user.role == "DRH":
        if role != "RH":
            return templates.TemplateResponse("create_user.html",
                                             {"request": request, "regions": db.query(Region).all(),
                                              "current_user": current_user,
                                              "error": "Le DRH peut uniquement créer des RH"})
        if not code_region:
            return templates.TemplateResponse("create_user.html",
                                             {"request": request, "regions": db.query(Region).all(),
                                              "current_user": current_user,
                                              "error": "Une région est requise pour les RH"})
    else:
        return templates.TemplateResponse("create_user.html", {"request": request, "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Accès non autorisé"})

    if code_region:
        region = db.query(Region).filter(Region.code == code_region).first()
        if not region:
            return templates.TemplateResponse("create_user.html",
                                             {"request": request, "regions": db.query(Region).all(),
                                              "current_user": current_user, "error": "Région non trouvée"})

    existing_user = db.query(User).filter(User.nom_utilisateur == nom_utilisateur).first()
    if existing_user:
        return templates.TemplateResponse("create_user.html", {"request": request, "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Nom d'utilisateur déjà pris"})

    db_user = User(
        nom_utilisateur=nom_utilisateur,
        mot_de_passe_hash=get_password_hash(mot_de_passe),
        email=email,
        role=role,
        code_region=code_region
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    if current_user.role == "SUPER_USER":
        redirect_url = "/api/users/admin_dashboard"
    elif current_user.role == "DRH":
        redirect_url = "/api/users/drh_dashboard"
    else:
        redirect_url = "/api/users/rh_dashboard"
    return RedirectResponse(url=redirect_url, status_code=status.HTTP_303_SEE_OTHER)

@router.get("/create_personnel", response_class=HTMLResponse)
async def create_personnel_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès au formulaire create_personnel par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé au formulaire create_personnel pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    regions = db.query(Region).all()
    return templates.TemplateResponse(
        "create_personnel.html",
        {"request": request, "regions": regions, "current_user": current_user}
    )

@router.post("/create_personnel", response_class=HTMLResponse)
async def create_personnel(
    nom: str = Form(...),
    prenom: str = Form(...),
    sexe: str = Form(...),
    age: int = Form(...),
    grade: str = Form(...),
    matricule: str = Form(...),
    taille: int = Form(...),
    code_region: str = Form(...),
    photo: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Tentative de création de personnel par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        return templates.TemplateResponse("create_personnel.html",
                                         {"request": request, "regions": db.query(Region).all(),
                                          "current_user": current_user, "error": "Accès non autorisé"})

    region = db.query(Region).filter(Region.code == code_region).first()
    if not region:
        return templates.TemplateResponse("create_personnel.html",
                                         {"request": request, "regions": db.query(Region).all(),
                                          "current_user": current_user, "error": "Région non trouvée"})

    existing_matricule = db.query(Personnel).filter(Personnel.matricule == matricule).first()
    if existing_matricule:
        return templates.TemplateResponse("create_personnel.html",
                                         {"request": request, "regions": db.query(Region).all(),
                                          "current_user": current_user, "error": "Matricule déjà pris"})

    photo_url = None
    if photo:
        photo_filename = f"{matricule}_{photo.filename}"
        photo_path = os.path.join(settings.UPLOAD_DIR, photo_filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        with open(photo_path, "wb") as buffer:
            content = await photo.read()
            buffer.write(content)
        photo_url = f"/uploads/{photo_filename}"

    db_personnel = Personnel(
        nom=nom,
        prenom=prenom,
        sexe=sexe,
        age=age,
        grade=grade,
        matricule=matricule,
        taille=taille,
        photo_url=photo_url,
        code_region=code_region
    )
    db.add(db_personnel)
    db.commit()
    db.refresh(db_personnel)
    return RedirectResponse(url="/api/users/drh_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/create_affectation", response_class=HTMLResponse)
async def create_affectation_form(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès au formulaire create_affectation par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé au formulaire create_affectation pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    personnels = db.query(Personnel).filter(Personnel.code_region == current_user.code_region).all()
    regions = db.query(Region).all()
    return templates.TemplateResponse(
        "affectation.html",
        {"request": request, "personnels": personnels, "regions": regions, "current_user": current_user}
    )

@router.post("/create_affectation", response_class=HTMLResponse)
async def create_affectation(
    personnel_id: int = Form(...),
    code_region: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Tentative de création d'affectation par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        return templates.TemplateResponse("affectation.html", {"request": request,
                                                              "personnels": db.query(Personnel).filter(
                                                                  Personnel.code_region == current_user.code_region).all(),
                                                              "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Accès non autorisé"})

    personnel = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not personnel:
        return templates.TemplateResponse("affectation.html", {"request": request,
                                                              "personnels": db.query(Personnel).filter(
                                                                  Personnel.code_region == current_user.code_region).all(),
                                                              "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Personnel non trouvé"})

    region = db.query(Region).filter(Region.code == code_region).first()
    if not region:
        return templates.TemplateResponse("affectation.html", {"request": request,
                                                              "personnels": db.query(Personnel).filter(
                                                                  Personnel.code_region == current_user.code_region).all(),
                                                              "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Région non trouvée"})

    if personnel.code_region == code_region:
        return templates.TemplateResponse("affectation.html", {"request": request,
                                                              "personnels": db.query(Personnel).filter(
                                                                  Personnel.code_region == current_user.code_region).all(),
                                                              "regions": db.query(Region).all(),
                                                              "current_user": current_user,
                                                              "error": "Le personnel est déjà dans cette région"})

    db_affectation = Affectation(
        personnel_id=personnel_id,
        code_region=code_region,
        status=AffectationStatus.PENDING
    )
    db.add(db_affectation)
    db.commit()
    db.refresh(db_affectation)

    return RedirectResponse(url="/api/users/drh_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/confirm_affectation", response_class=HTMLResponse)
async def confirm_affectation_form(request: Request, current_user: User = Depends(get_current_user),
                                  db: Session = Depends(get_db)):
    logger.info(f"Tentative d'accès à confirm_affectation par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à confirm_affectation pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    affectations = db.query(Affectation).filter(Affectation.code_region == current_user.code_region,
                                               Affectation.status == AffectationStatus.PENDING).all()
    return templates.TemplateResponse("confirm_affectation.html",
                                     {"request": request, "affectations": affectations, "current_user": current_user})

@router.post("/confirm_affectation/{affectation_id}", response_class=HTMLResponse)
async def confirm_affectation(
    affectation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    logger.info(f"Tentative de confirmation d'affectation {affectation_id} par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        return templates.TemplateResponse("confirm_affectation.html", {"request": request,
                                                                     "affectations": db.query(Affectation).filter(
                                                                         Affectation.code_region == current_user.code_region,
                                                                         Affectation.status == AffectationStatus.PENDING).all(),
                                                                     "current_user": current_user,
                                                                     "error": "Accès non autorisé"})

    affectation = db.query(Affectation).filter(Affectation.id == affectation_id).first()
    if not affectation:
        return templates.TemplateResponse("confirm_affectation.html", {"request": request,
                                                                     "affectations": db.query(Affectation).filter(
                                                                         Affectation.code_region == current_user.code_region,
                                                                         Affectation.status == AffectationStatus.PENDING).all(),
                                                                     "current_user": current_user,
                                                                     "error": "Affectation non trouvée"})

    if affectation.code_region != current_user.code_region:
        return templates.TemplateResponse("confirm_affectation.html", {"request": request,
                                                                     "affectations": db.query(Affectation).filter(
                                                                         Affectation.code_region == current_user.code_region,
                                                                         Affectation.status == AffectationStatus.PENDING).all(),
                                                                     "current_user": current_user,
                                                                     "error": "Vous n'êtes pas autorisé à confirmer cette affectation"})

    affectation.status = AffectationStatus.CONFIRMED
    personnel = db.query(Personnel).filter(Personnel.id == affectation.personnel_id).first()
    personnel.code_region = affectation.code_region
    db.commit()

    return RedirectResponse(url="/api/users/rh_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/view_affectations", response_class=HTMLResponse)
async def view_affectations(request: Request, current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    logger.info(f"Tentative d'accès à view_affectations par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à view_affectations pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    affectations = db.query(Affectation).all()
    return templates.TemplateResponse("view_affectations.html",
                                     {"request": request, "affectations": affectations, "current_user": current_user})