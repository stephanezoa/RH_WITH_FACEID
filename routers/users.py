from datetime import datetime
import requests
import base64
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from starlette.responses import JSONResponse
from core.database import get_db
from core.security import get_password_hash, get_current_user
from models.notification import Notification
from models.user import User
from models.personnel import Personnel
from models.region import Region
from models.affectation import Affectation, AffectationStatus
import os
import logging
from PIL import Image
import io
from routers.facepp_logic import FacePPComparator

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux SUPER_USER")

    # Récupérer toutes les régions
    regions = db.query(Region).all()
    logger.info(f"Régions récupérées : {len(regions)}")

    # Récupérer tous les utilisateurs
    utilisateurs = db.query(User).all()
    logger.info(f"Utilisateurs récupérés : {len(utilisateurs)}")

    # Récupérer les affectations en attente avec les informations du personnel
    affectations = db.query(Affectation, Personnel).join(
        Personnel, Affectation.personnel_id == Personnel.id
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    ).all()
    logger.info(f"Affectations en attente récupérées : {len(affectations)}")

    # Calculer les statistiques
    stats = {
        "total_users": db.query(User).filter(User.role.in_(["DRH", "RH"])).count(),
        "total_affectations": db.query(Affectation).filter(Affectation.status == AffectationStatus.PENDING).count(),
        "total_regions": db.query(Region).count()
    }

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "regions": regions,
            "utilisateurs": utilisateurs,
            "affectations": affectations,
            "stats": stats
        }
    )

@router.get("/drh_dashboard", response_class=HTMLResponse)
async def drh_dashboard(
    request: Request,
    region_filter: str | None = None,
    status_filter: str = "ALL",
    date_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à drh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}, filtre région : {region_filter}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé à drh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux DRH")

    regions = db.query(Region).all()
    query = db.query(Affectation, Personnel).join(Personnel, Affectation.personnel_id == Personnel.id)
    if region_filter:
        query = query.filter(Affectation.code_region == region_filter)
    if status_filter != "ALL":
        query = query.filter(Affectation.status == status_filter)
    if date_filter:
        query = query.filter(Affectation.created_at == date_filter)

    affectations = query.all()
    affectations_by_region = db.query(
        Affectation.code_region,
        func.count(Affectation.id).label('count')
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    ).group_by(Affectation.code_region).all()
    affectations_report = {region: count for region, count in affectations_by_region}
    logger.info(f"affectations_report type: {type(affectations_report)}, contenu: {affectations_report}")

    return templates.TemplateResponse(
        "drh_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "affectations": affectations,
            "affectations_report": affectations_report,
            "regions": regions,
            "region_filter": region_filter,
            "status_filter": status_filter,
            "date_filter": date_filter
        }
    )

@router.get("/rh_dashboard", response_class=HTMLResponse)
async def rh_dashboard(
    request: Request,
    region_filter: str | None = None,
    status_filter: str = "ALL",
    date_filter: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à rh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}, filtre région : {region_filter}")
    if current_user.role not in ["RH", "DRH"]:
        logger.error(f"Accès refusé à rh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux RH et DRH")

    regions = db.query(Region).all()
    query = db.query(Affectation, Personnel).join(Personnel, Affectation.personnel_id == Personnel.id)
    if region_filter:
        query = query.filter(Affectation.code_region == region_filter)
    if status_filter != "ALL":
        query = query.filter(Affectation.status == status_filter)
    if date_filter:
        query = query.filter(Affectation.created_at == date_filter)

    affectations = query.all()
    affectations_by_region = db.query(
        Affectation.code_region,
        func.count(Affectation.id).label('count')
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    ).group_by(Affectation.code_region).all()
    affectations_report = {region: count for region, count in affectations_by_region}
    logger.info(f"affectations_report type: {type(affectations_report)}, contenu: {affectations_report}")

    try:
        notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(10).all()
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des notifications : {str(e)}")
        notifications = []

    logger.info(f"Affectations récupérées : {len(affectations)}, Rapport : {affectations_report}")
    return templates.TemplateResponse(
        "rh_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "affectations": affectations,
            "affectations_report": affectations_report,
            "regions": regions,
            "region_filter": region_filter,
            "status_filter": status_filter,
            "date_filter": date_filter,
            "notifications": notifications
        }
    )

@router.post("/upload_webcam_photo")
async def upload_webcam_photo(
        photo: UploadFile = File(...),
        current_user: User = Depends(get_current_user)
):
    if current_user.role != "DRH":
        logger.error(
            f"Accès refusé à upload_webcam_photo pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_extension = os.path.splitext(photo.filename)[1].lower()
    if file_extension not in allowed_extensions:
        logger.error(f"Format de fichier non supporté : {file_extension}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP.")

    try:
        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        photo_filename = os.path.splitext(photo.filename)[0] + ".jpg"
        photo_path = os.path.join("uploads/photos", photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        with open(photo_path, "wb") as buffer:
            buffer.write(photo_content)
        photo_url = f"/uploads/photos/{photo_filename}"
        logger.info(f"Photo webcam enregistrée : {photo_filename}")
        return {"photo_url": photo_url}
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la photo webcam : {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Erreur lors de l'enregistrement de la photo : {str(e)}")

@router.get("/create_user", response_class=HTMLResponse)
async def create_user_form(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(
        f"Tentative d'accès au formulaire create_user par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role not in ["SUPER_USER", "DRH"]:
        logger.error(
            f"Accès refusé au formulaire create_user pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
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
        return templates.TemplateResponse("create_user.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user, "error": "Nom d'utilisateur déjà pris"})

    new_user = User(
        nom_utilisateur=nom_utilisateur,
        email=email,
        mot_de_passe_hash=get_password_hash(mot_de_passe),
        role=role,
        code_region=code_region
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    logger.info(f"Utilisateur créé : {nom_utilisateur}, rôle : {role}")
    return RedirectResponse(url="/api/users/drh_dashboard", status_code=status.HTTP_303_SEE_OTHER)

@router.get("/create_personnel", response_class=HTMLResponse)
async def create_personnel_form(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(
        f"Tentative d'accès au formulaire create_personnel par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(
            f"Accès refusé au formulaire create_personnel pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
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
        logger.error(f"Accès refusé à create_personnel pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user, "error": "Accès non autorisé"})

    region = db.query(Region).filter(Region.code == code_region).first()
    if not region:
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user, "error": "Région non trouvée"})

    existing_personnel = db.query(Personnel).filter(Personnel.matricule == matricule).first()
    if existing_personnel:
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user, "error": "Matricule déjà utilisé"})

    if not photo:
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Veuillez fournir une photo (via webcam ou téléchargement)"})

    photo_url = None
    face_token = None
    photo_path = None

    try:
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        file_extension = os.path.splitext(photo.filename)[1].lower()
        if file_extension not in allowed_extensions:
            logger.error(f"Format de fichier non supporté : {file_extension}")
            return templates.TemplateResponse("create_personnel.html",
                                              {"request": request, "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": "Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP."})

        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        photo_filename = f"{matricule}_{os.path.splitext(photo.filename)[0]}.jpg"
        photo_path = os.path.join("uploads/photos", photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        with open(photo_path, "wb") as buffer:
            buffer.write(photo_content)
        photo_url = f"/uploads/photos/{photo_filename}"

        try:
            face_detect_url = "https://api-us.faceplusplus.com/facepp/v3/detect"
            params = {
                "api_key": "40w_gxLhB1VZIQTcrJcpQ8S4ZWEiwyJz",
                "api_secret": "E_b2qpKdDR6td87RJuXKgssSBjmycWKa",
                "return_landmark": 1,
                "return_attributes": "gender,age"
            }
            with open(photo_path, "rb") as photo_file:
                files = {"image_file": photo_file}
                response = requests.post(face_detect_url, files=files, data=params)

            if response.status_code != 200:
                logger.error(f"Erreur API Face++ detect : {response.json()}")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": f"Erreur API Face++ : {response.json().get('error_message', 'Erreur inconnue')}"})

            response_data = response.json()
            if not response_data.get('faces'):
                logger.error("Aucun visage détecté dans l'image")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": "Aucun visage détecté dans l'image"})

            face = response_data['faces'][0]
            face_token = face['face_token']
            detected_gender = face['attributes']['gender']['value'].upper()
            detected_age = face['attributes']['age']['value']

            if detected_gender != sexe:
                logger.error(f"Incohérence de genre : formulaire={sexe}, détecté={detected_gender}")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": f"Le genre détecté ({detected_gender}) ne correspond pas au genre saisi ({sexe})"})

            faceset_url = "https://api-us.faceplusplus.com/facepp/v3/faceset/create"
            faceset_params = {
                "api_key": "40w_gxLhB1VZIQTcrJcpQ8S4ZWEiwyJz",
                "api_secret": "E_b2qpKdDR6td87RJuXKgssSBjmycWKa",
                "outer_id": matricule,
                "tags": "mindefrh",
                "face_tokens": face_token,
                "force_merge": 0
            }
            faceset_response = requests.post(faceset_url, data=faceset_params)

            if faceset_response.status_code != 200:
                logger.error(f"Erreur API Face++ faceset : {faceset_response.json()}")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": f"Erreur lors de la création du FaceSet : {faceset_response.json().get('error_message', 'Erreur inconnue')}"})

        except Exception as e:
            logger.error(f"Erreur lors de l'appel API Face++ : {str(e)}")
            return templates.TemplateResponse("create_personnel.html",
                                              {"request": request, "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": f"Erreur lors de l'appel API Face++ : {str(e)}"})

        new_personnel = Personnel(
            nom=nom,
            prenom=prenom,
            sexe=sexe,
            age=age,
            grade=grade,
            matricule=matricule,
            taille=taille,
            code_region=code_region,
            photo_url=photo_url,
            face_token=face_token
        )
        db.add(new_personnel)
        db.commit()
        db.refresh(new_personnel)
        logger.info(f"Personnel créé : {matricule}, région : {code_region}, face_token : {face_token}")
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "success": f"Personnel {nom} {prenom} (Matricule: {matricule}) créé avec succès !"})

    except Exception as e:
        logger.error(f"Erreur générale lors du traitement de la photo : {str(e)}")
        if photo_path and os.path.exists(photo_path):
            os.remove(photo_path)
        return templates.TemplateResponse("create_personnel.html",
                                          {"request": request, "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": f"Erreur lors du traitement de la photo : {str(e)}"})

@router.get("/create_affectation", response_class=HTMLResponse)
async def create_affectation_form(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(
        f"Tentative d'accès au formulaire create_affectation par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(
            f"Accès refusé à create_affectation pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")

    personnels = db.query(Personnel).filter(Personnel.code_region == current_user.code_region).all()
    regions = db.query(Region).all()
    affectations = db.query(Affectation).filter(
        Affectation.personnel_id.in_([p.id for p in personnels])
    ).all()
    personnel_affectations = {p.id: [a for a in affectations if a.personnel_id == p.id] for p in personnels}

    # Ajouter pertinent_regions (toutes les régions pour l'instant)
    pertinent_regions = regions
    logger.info(f"Pertinent régions : {[(r.code, r.nom) for r in pertinent_regions]}")
    logger.info(f"Personnels récupérés : {len(personnels)} pour code_region : {current_user.code_region}")

    return templates.TemplateResponse(
        "affectation.html",
        {
            "request": request,
            "personnels": personnels,
            "regions": regions,
            "pertinent_regions": pertinent_regions,
            "current_user": current_user,
            "personnel_affectations": personnel_affectations
        }
    )

@router.post("/affectation", response_model=dict)
async def create_affectation(
    personnel_id: int = Form(...),
    code_region: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Tentative de création d'affectation par {current_user.nom_utilisateur}, personnel_id : {personnel_id}, région : {code_region}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé à create_affectation pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux DRH")

    personnel = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not personnel:
        logger.error(f"Personnel {personnel_id} non trouvé")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel non trouvé")

    region = db.query(Region).filter(Region.code == code_region).first()
    if not region:
        logger.error(f"Région {code_region} non trouvée")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Région non trouvée")

    if personnel.code_region == code_region:
        logger.warning(f"Le personnel {personnel_id} est déjà dans la région {code_region}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Le personnel est déjà dans cette région")

    affectation = Affectation(
        personnel_id=personnel_id,
        code_region=code_region,
        status=AffectationStatus.PENDING if isinstance(AffectationStatus.PENDING, str) else AffectationStatus.PENDING.value
    )
    db.add(affectation)
    db.commit()
    db.refresh(affectation)
    logger.info(f"Affectation créée pour personnel_id : {personnel_id}, région : {code_region}, id : {affectation.id}")

    return {"affectation_id": affectation.id, "message": "Affectation créée, en attente de validation faciale par RH"}

@router.post("/confirm_affectation_with_face/{affectation_id}", response_class=JSONResponse)
async def confirm_affectation_with_face(
    affectation_id: int,
    photo: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative de confirmation d'affectation {affectation_id} avec reconnaissance faciale par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à confirm_affectation_with_face pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux RH")

    affectation = db.query(Affectation).filter(Affectation.id == affectation_id).first()
    if not affectation:
        logger.error(f"Affectation {affectation_id} non trouvée")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Affectation non trouvée")

    personnel = db.query(Personnel).filter(Personnel.id == affectation.personnel_id).first()
    if not personnel or not personnel.face_token:
        logger.error(f"Personnel {affectation.personnel_id} non trouvé ou face_token manquant")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Personnel non trouvé ou face_token manquant")

    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_extension = os.path.splitext(photo.filename)[1].lower()
    if file_extension not in allowed_extensions:
        logger.error(f"Format de fichier non supporté : {file_extension}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP.")

    try:
        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        photo_filename = f"temp_{affectation_id}_webcam.jpg"
        photo_path = os.path.join("uploads/photos", photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        with open(photo_path, "wb") as buffer:
            buffer.write(photo_content)

        comparator = FacePPComparator(
            api_key="40w_gxLhB1VZIQTcrJcpQ8S4ZWEiwyJz",
            api_secret="E_b2qpKdDR6td87RJuXKgssSBjmycWKa"
        )
        response_data = comparator.compare(
            face_token=personnel.face_token,
            image_path=photo_path
        )

        if os.path.exists(photo_path):
            os.remove(photo_path)

        if "error" in response_data:
            error_message = response_data['error']
            logger.error(f"Erreur API Face++ : {error_message}")
            if "INVALID_API_KEY" in error_message:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Clés API Face++ invalides. Veuillez contacter l'administrateur.")
            elif "TIMEOUT" in error_message:
                raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Délai d'attente dépassé pour l'API Face++. Veuillez réessayer.")
            elif "INVALID_IMAGE" in error_message:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image invalide envoyée à l'API Face++. Veuillez réessayer avec une autre photo.")
            else:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur API Face++ : {error_message}")

        if not response_data.get('faces2'):
            logger.error("Aucun visage détecté dans la photo webcam")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun visage détecté dans la photo webcam. Veuillez réessayer.")

        confidence = response_data.get('confidence', 0)
        confidence_color = "red-700" if confidence < 60 else "yellow-700" if confidence < 80 else "green-700"
        confidence_message = f"Confiance de correspondance : {confidence:.2f}%"

        affectation.confidence = confidence
        affectation.confidence_color = confidence_color
        affectation.confidence_message = confidence_message

        if confidence <= 75:
            logger.info(f"Confiance insuffisante pour affectation {affectation_id} : {confidence}")
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Les visages ne correspondent pas (confiance : {confidence:.2f}%). Veuillez réessayer."
            )

        affectation.status = "CONFIRMED"
        personnel.code_region = affectation.code_region
        db.commit()
        logger.info(f"Affectation {affectation_id} confirmée par {current_user.nom_utilisateur} avec confiance : {confidence}")
        return {
            "message": f"Affectation pour {personnel.nom} {personnel.prenom} validée avec succès (confiance : {confidence:.2f}%)",
            "confidence": confidence,
            "confidence_color": confidence_color,
            "confidence_message": confidence_message
        }

    except HTTPException as e:
        raise e
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur réseau lors de la requête Face++ : {str(e)}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Erreur réseau lors de la connexion à l'API Face++. Veuillez réessayer.")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de la confirmation de l'affectation {affectation_id} : {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erreur inattendue : {str(e)}")

@router.get("/view_affectations", response_class=HTMLResponse)
async def view_affectations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à view_affectations par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à view_affectations pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé aux RH")
    affectations = db.query(Affectation).all()
    return templates.TemplateResponse("view_affectations.html", {
        "request": request,
        "affectations": affectations,
        "current_user": current_user
    })