import requests
import base64
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from core.database import get_db
from core.security import get_password_hash, get_current_user
from models.user import User
from models.personnel import Personnel
from models.region import Region
from models.affectation import Affectation, AffectationStatus
import os
import logging
from PIL import Image
import io

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FacePPComparator:
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialise le comparateur de visages Face++

        Args:
            api_key: Clé API Face++
            api_secret: Secret API Face++
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api-us.faceplusplus.com/facepp/v3/compare"

    def compare_face_to_image(
            self,
            face_token: str,
            image_path: Optional[str] = None,
            image_url: Optional[str] = None,
            image_base64: Optional[str] = None
    ) -> Dict:
        """
        Compare un face_token avec une image

        Args:
            face_token: Le token du visage à comparer
            image_path: Chemin vers l'image locale (optionnel)
            image_url: URL de l'image (optionnel)
            image_base64: Image encodée en base64 (optionnel)

        Returns:
            Dictionnaire contenant la réponse de l'API

        Note:
            Un seul des paramètres image_path, image_url ou image_base64 doit être fourni
        """
        # Vérification des paramètres
        if sum([1 for x in [image_path, image_url, image_base64] if x is not None]) != 1:
            raise ValueError("Vous devez fournir exactement une source d'image (path, URL ou base64)")

        # Préparation des données pour la requête
        files = {}
        data = {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "face_token1": face_token
        }

        # Gestion des différents types d'images
        if image_path:
            with open(image_path, 'rb') as f:
                files["image_file2"] = f
        elif image_url:
            data["image_url2"] = image_url
        elif image_base64:
            data["image_base64_2"] = image_base64

        try:
            # Envoi de la requête
            response = requests.post(self.base_url, data=data, files=files)
            response.raise_for_status()

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur lors de la requête API: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Réponse d'erreur: {e.response.text}")
            return {"error": str(e)}


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
        region_filter: str | None = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(
        f"Tentative d'accès à drh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}, filtre région : {region_filter}")
    if current_user.role != "DRH":
        logger.error(f"Accès refusé à drh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")

    regions = db.query(Region).all()
    query = db.query(Affectation, Personnel).join(
        Personnel, Affectation.personnel_id == Personnel.id
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    )

    if region_filter:
        query = query.filter(Affectation.code_region == region_filter)
    else:
        query = query.filter(Affectation.code_region == current_user.code_region)

    affectations = query.all()

    affectations_by_region = db.query(
        Affectation.code_region,
        func.count(Affectation.id).label('count')
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    ).group_by(Affectation.code_region).all()

    logger.info(f"Résultat de la requête affectations_by_region : {affectations_by_region}")
    affectations_report = {region: count for region, count in affectations_by_region}

    return templates.TemplateResponse(
        "drh_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "affectations": affectations,
            "affectations_report": affectations_report,
            "regions": regions,
            "region_filter": region_filter
        }
    )


@router.get("/rh_dashboard", response_class=HTMLResponse)
async def rh_dashboard(
        request: Request,
        region_filter: str | None = None,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(
        f"Tentative d'accès à rh_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}, filtre région : {region_filter}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à rh_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")

    regions = db.query(Region).all()
    query = db.query(Affectation, Personnel).join(
        Personnel, Affectation.personnel_id == Personnel.id
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    )

    if region_filter:
        query = query.filter(Affectation.code_region == region_filter)

    affectations = query.all()

    affectations_by_region = db.query(
        Affectation.code_region,
        func.count(Affectation.id).label('count')
    ).filter(
        Affectation.status == AffectationStatus.PENDING
    ).group_by(Affectation.code_region).all()

    logger.info(f"Résultat de la requête affectations_by_region : {affectations_by_region}")
    affectations_report = {region: count for region, count in affectations_by_region}

    return templates.TemplateResponse(
        "rh_dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "affectations": affectations,
            "affectations_report": affectations_report,
            "regions": regions,
            "region_filter": region_filter
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

    # Valider le format de l'image
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_extension = os.path.splitext(photo.filename)[1].lower()
    if file_extension not in allowed_extensions:
        logger.error(f"Format de fichier non supporté : {file_extension}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP.")

    try:
        # Convertir l'image en JPEG
        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")  # Convertir en RGB pour JPEG
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        # Sauvegarder l'image convertie
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
        # Valider le format de l'image
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        file_extension = os.path.splitext(photo.filename)[1].lower()
        if file_extension not in allowed_extensions:
            logger.error(f"Format de fichier non supporté : {file_extension}")
            return templates.TemplateResponse("create_personnel.html",
                                              {"request": request, "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": "Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP."})

        # Convertir l'image en JPEG
        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")  # Convertir en RGB pour JPEG
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        # Sauvegarder l'image convertie
        photo_filename = f"{matricule}_{os.path.splitext(photo.filename)[0]}.jpg"
        photo_path = os.path.join("uploads/photos", photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        with open(photo_path, "wb") as buffer:
            buffer.write(photo_content)
        photo_url = f"/uploads/photos/{photo_filename}"

        # Appel à l'API Face++ pour détecter le visage
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

            # Vérifier la cohérence des données
            if detected_gender != sexe:
                logger.error(f"Incohérence de genre : formulaire={sexe}, détecté={detected_gender}")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": f"Le genre détecté ({detected_gender}) ne correspond pas au genre saisi ({sexe})"})

            if abs(detected_age - age) > 5:
                logger.error(f"Incohérence d'âge : formulaire={age}, détecté={detected_age}")
                return templates.TemplateResponse("create_personnel.html",
                                                  {"request": request, "regions": db.query(Region).all(),
                                                   "current_user": current_user,
                                                   "error": f"L'âge détecté ({detected_age}) diffère trop de l'âge saisi ({age})"})

            # Créer un FaceSet avec le face_token
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

        # Créer le personnel avec le face_token
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
            os.remove(photo_path)  # Nettoyer le fichier en cas d'erreur
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
    return templates.TemplateResponse(
        "affectation.html",
        {
            "request": request,
            "personnels": personnels,
            "regions": regions,
            "current_user": current_user,
            "personnel_affectations": personnel_affectations
        }
    )


@router.post("/affectation", response_class=HTMLResponse)
async def create_affectation(
        personnel_id: int = Form(...),
        code_region: str = Form(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
):
    logger.info(f"Tentative de création d'affectation par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "DRH":
        logger.error(
            f"Accès refusé à create_affectation pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return templates.TemplateResponse("affectation.html",
                                          {"request": request,
                                           "personnels": db.query(Personnel).filter(
                                               Personnel.code_region == current_user.code_region).all(),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Accès non autorisé"})

    personnel = db.query(Personnel).filter(Personnel.id == personnel_id).first()
    if not personnel:
        return templates.TemplateResponse("affectation.html",
                                          {"request": request,
                                           "personnels": db.query(Personnel).filter(
                                               Personnel.code_region == current_user.code_region).all(),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Personnel non trouvé"})

    region = db.query(Region).filter(Region.code == code_region).first()
    if not region:
        return templates.TemplateResponse("affectation.html",
                                          {"request": request,
                                           "personnels": db.query(Personnel).filter(
                                               Personnel.code_region == current_user.code_region).all(),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Région non trouvée"})

    if personnel.code_region == code_region:
        return templates.TemplateResponse("affectation.html",
                                          {"request": request,
                                           "personnels": db.query(Personnel).filter(
                                               Personnel.code_region == current_user.code_region).all(),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Le personnel est déjà dans cette région"})

    existing_affectation = db.query(Affectation).filter(
        Affectation.personnel_id == personnel_id,
        Affectation.status.in_([AffectationStatus.PENDING, AffectationStatus.CONFIRMED])
    ).first()
    if existing_affectation:
        return templates.TemplateResponse("affectation.html",
                                          {"request": request,
                                           "personnels": db.query(Personnel).filter(
                                               Personnel.code_region == current_user.code_region).all(),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": f"Le personnel {personnel.nom} {personnel.prenom} a déjà une affectation {existing_affectation.status} vers {existing_affectation.code_region}"})

    db_affectation = Affectation(
        personnel_id=personnel_id,
        code_region=code_region,
        status=AffectationStatus.PENDING
    )
    db.add(db_affectation)
    db.commit()
    db.refresh(db_affectation)
    logger.info(f"Affectation créée pour personnel_id : {personnel_id}, région : {code_region}")
    return RedirectResponse(url="/api/users/drh_dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/confirm_affectation_with_face/{affectation_id}", response_class=HTMLResponse)
async def confirm_affectation_with_face(
        affectation_id: int,
        photo: UploadFile = File(...),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
        request: Request = None
):
    logger.info(
        f"Tentative de confirmation d'affectation {affectation_id} avec reconnaissance faciale par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(
            f"Accès refusé à confirm_affectation_with_face pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return templates.TemplateResponse("rh_dashboard.html",
                                          {"request": request,
                                           "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                               Affectation.status == AffectationStatus.PENDING).all(),
                                           "affectations_report": dict(
                                               db.query(Affectation.code_region, func.count(Affectation.id))
                                               .filter(Affectation.status == AffectationStatus.PENDING)
                                               .group_by(Affectation.code_region).all()),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Accès non autorisé"})

    affectation = db.query(Affectation).filter(Affectation.id == affectation_id).first()
    if not affectation:
        return templates.TemplateResponse("rh_dashboard.html",
                                          {"request": request,
                                           "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                               Affectation.status == AffectationStatus.PENDING).all(),
                                           "affectations_report": dict(
                                               db.query(Affectation.code_region, func.count(Affectation.id))
                                               .filter(Affectation.status == AffectationStatus.PENDING)
                                               .group_by(Affectation.code_region).all()),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Affectation non trouvée"})

    personnel = db.query(Personnel).filter(Personnel.id == affectation.personnel_id).first()
    if not personnel or not personnel.face_token:
        return templates.TemplateResponse("rh_dashboard.html",
                                          {"request": request,
                                           "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                               Affectation.status == AffectationStatus.PENDING).all(),
                                           "affectations_report": dict(
                                               db.query(Affectation.code_region, func.count(Affectation.id))
                                               .filter(Affectation.status == AffectationStatus.PENDING)
                                               .group_by(Affectation.code_region).all()),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Personnel non trouvé ou face_token manquant"})

    # Valider le format de l'image
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_extension = os.path.splitext(photo.filename)[1].lower()
    if file_extension not in allowed_extensions:
        logger.error(f"Format de fichier non supporté : {file_extension}")
        return templates.TemplateResponse("rh_dashboard.html",
                                          {"request": request,
                                           "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                               Affectation.status == AffectationStatus.PENDING).all(),
                                           "affectations_report": dict(
                                               db.query(Affectation.code_region, func.count(Affectation.id))
                                               .filter(Affectation.status == AffectationStatus.PENDING)
                                               .group_by(Affectation.code_region).all()),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "error": "Format de fichier non supporté. Veuillez utiliser JPG, PNG ou BMP."})

    try:
        # Convert写真 en JPEG
        photo_content = await photo.read()
        with Image.open(io.BytesIO(photo_content)) as img:
            img = img.convert("RGB")
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            photo_content = output.getvalue()

        # Sauvegarder temporairement l'image
        photo_filename = f"temp_{affectation_id}_webcam.jpg"
        photo_path = os.path.join("uploads/photos", photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        with open(photo_path, "wb") as buffer:
            buffer.write(photo_content)

    except Exeception as e:
        print(e)

        # Appel à l'API Face++ via FacePPComparator
        comparator = FacePPComparator(
            api_key="40w_gxLhB1VZIQTcrJcpQ8S4ZWEiwyJz",
            api_secret="E_b2qpKdDR6td87RJuXKgssSBjmycWKa"
        )
        response_data = comparator.compare_face_to_image(
            face_token=personnel.face_token,
            image_path=photo_path
        )

        # Nettoyer le fichier temporaire
        if os.path.exists(photo_path):
            os.remove(photo_path)

        if "error" in response_data:
            logger.error(f"Erreur API Face++ : {response_data['error']}")
            return templates.TemplateResponse("rh_dashboard.html",
                                              {"request": request,
                                               "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                                   Affectation.status == AffectationStatus.PENDING).all(),
                                               "affectations_report": dict(
                                                   db.query(Affectation.code_region, func.count(Affectation.id))
                                                   .filter(Affectation.status == AffectationStatus.PENDING)
                                                   .group_by(Affectation.code_region).all()),
                                               "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": f"Erreur API Face++ : {response_data['error']}"})

        if not response_data.get('faces2'):
            logger.error("Aucun visage détecté dans la photo webcam")
            return templates.TemplateResponse("rh_dashboard.html",
                                              {"request": request,
                                               "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                                   Affectation.status == AffectationStatus.PENDING).all(),
                                               "affectations_report": dict(
                                                   db.query(Affectation.code_region, func.count(Affectation.id))
                                                   .filter(Affectation.status == AffectationStatus.PENDING)
                                                   .group_by(Affectation.code_region).all()),
                                               "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": "Aucun visage détecté dans la photo webcam. Veuillez réessayer."})

        confidence = response_data.get('confidence', 0)
        confidence_color = "text-red-700" if confidence < 60 else "text-yellow-700" if confidence < 80 else "text-green-700"
        confidence_message = f"Confiance de correspondance : {confidence:.3f}%"

        if confidence <= 75:
            logger.info(f"Confiance insuffisante pour affectation {affectation_id} : {confidence}")
            return templates.TemplateResponse("rh_dashboard.html",
                                              {"request": request,
                                               "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                                   Affectation.status == AffectationStatus.PENDING).all(),
                                               "affectations_report": dict(
                                                   db.query(Affectation.code_region, func.count(Affectation.id))
                                                   .filter(Affectation.status == AffectationStatus.PENDING)
                                                   .group_by(Affectation.code_region).all()),
                                               "regions": db.query(Region).all(),
                                               "current_user": current_user,
                                               "error": f"Les visages ne correspondent pas (confiance : {confidence:.3f}%). Veuillez réessayer.",
                                               "confidence": confidence,
                                               "confidence_color": confidence_color,
                                               "affectation_id": affectation_id})

        # Valider l'affectation
        affectation.status = AffectationStatus.CONFIRMED
        personnel.code_region = affectation.code_region
        db.commit()
        logger.info(
            f"Affectation {affectation_id} confirmée par {current_user.nom_utilisateur} avec confiance : {confidence}")
        return templates.TemplateResponse("rh_dashboard.html",
                                          {"request": request,
                                           "affectations": db.query(Affectation, Personnel).join(Personnel).filter(
                                               Affectation.status == AffectationStatus.PENDING).all(),
                                           "affectations_report": dict(
                                               db.query(Affectation.code_region, func.count(Affectation.id))
                                               .filter(Affectation.status == AffectationStatus.PENDING)
                                               .group_by(Affectation.code_region).all()),
                                           "regions": db.query(Region).all(),
                                           "current_user": current_user,
                                           "success": f"Affectation pour {personnel.nom} {personnel.prenom} validée avec succès (confiance : {confidence:.3f}%)",
                                           "confidence": confidence,
                                           "confidence_color": confidence_color,
                                           "affectation_id": affectation_id})

@router.get("/view_affectations", response_class=HTMLResponse)
async def view_affectations(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    logger.info(f"Tentative d'accès à view_affectations par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "RH":
        logger.error(f"Accès refusé à view_affectations pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès non autorisé")
    affectations = db.query(Affectation).all()
    return templates.TemplateResponse("view_affectations.html",
                                      {"request": request, "affectations": affectations, "current_user": current_user})