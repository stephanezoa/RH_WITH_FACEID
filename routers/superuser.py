from fastapi import APIRouter, Depends, HTTPException, status, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from core.database import get_db
from core.security import get_password_hash, get_current_user
from models.user import User
from models.region import Region
from models.affectation import Affectation, AffectationStatus
from models.personnel import Personnel
import logging

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/superuser", tags=["superuser"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def superuser_dashboard(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Affiche le tableau de bord du super utilisateur avec les utilisateurs DRH/RH, affectations en attente, et statistiques.
    """
    logger.info(
        f"Tentative d'accès à superuser_dashboard par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "SUPER_USER":
        logger.error(
            f"Accès refusé à superuser_dashboard pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
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

    # Statistiques
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


@router.post("/create_user", response_class=JSONResponse)
async def create_user(
        nom_utilisateur: str = Form(...),
        email: str = Form(...),
        mot_de_passe: str = Form(...),
        role: str = Form(...),
        code_region: str | None = Form(None),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Crée un utilisateur DRH ou RH avec une réponse JSON pour les requêtes AJAX.
    """
    logger.info(f"Tentative de création d'utilisateur par {current_user.nom_utilisateur}, rôle : {current_user.role}")

    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à create_user pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    if role not in ["DRH", "RH"]:
        logger.error(f"Rôle non autorisé : {role}")
        return JSONResponse(content={"error": "Le Super Utilisateur peut uniquement créer des DRH ou RH"},
                            status_code=400)

    if code_region:
        region = db.query(Region).filter(Region.code == code_region).first()
        if not region:
            logger.error(f"Région non trouvée : {code_region}")
            return JSONResponse(content={"error": "Région non trouvée"}, status_code=404)

    existing_user = db.query(User).filter(User.nom_utilisateur == nom_utilisateur).first()
    if existing_user:
        logger.error(f"Nom d'utilisateur déjà pris : {nom_utilisateur}")
        return JSONResponse(content={"error": "Ce nom d'utilisateur est déjà pris"}, status_code=400)

    try:
        hashed_password = get_password_hash(mot_de_passe)
        new_user = User(
            nom_utilisateur=nom_utilisateur,
            email=email,
            mot_de_passe_hash=hashed_password,
            role=role,
            code_region=code_region
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"Utilisateur créé : {nom_utilisateur}, rôle : {role}, région : {code_region}")
        return JSONResponse(content={"success": f"Utilisateur {nom_utilisateur} ({role}) créé avec succès !"})
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'utilisateur : {str(e)}")
        return JSONResponse(content={"error": f"Erreur lors de la création de l'utilisateur : {str(e)}"},
                            status_code=500)


@router.get("/modifier_utilisateur/{user_id}", response_class=JSONResponse)
async def get_modifier_utilisateur(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Récupère les données d'un utilisateur pour le formulaire de modification (AJAX).
    """
    logger.info(f"Tentative de récupération des données de l'utilisateur {user_id} par {current_user.nom_utilisateur}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à modifier_utilisateur pour {current_user.nom_utilisateur}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"Utilisateur non trouvé : {user_id}")
        return JSONResponse(content={"error": "Utilisateur non trouvé"}, status_code=404)

    user_data = {
        "id": user.id,
        "nom_utilisateur": user.nom_utilisateur,
        "email": user.email,
        "role": user.role,
        "code_region": user.code_region
    }
    return JSONResponse(content=user_data)


@router.post("/modifier_utilisateur/{user_id}", response_class=JSONResponse)
async def modifier_utilisateur(
        user_id: int,
        nom_utilisateur: str = Form(...),
        email: str = Form(...),
        mot_de_passe: str = Form(None),
        role: str = Form(...),
        code_region: str | None = Form(None),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Modifie un utilisateur DRH ou RH avec une réponse JSON pour les requêtes AJAX.
    """
    logger.info(f"Tentative de modification de l'utilisateur {user_id} par {current_user.nom_utilisateur}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à modifier_utilisateur pour {current_user.nom_utilisateur}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"Utilisateur non trouvé : {user_id}")
        return JSONResponse(content={"error": "Utilisateur non trouvé"}, status_code=404)

    if role not in ["DRH", "RH"]:
        logger.error(f"Rôle non autorisé : {role}")
        return JSONResponse(content={"error": "Le Super Utilisateur peut uniquement modifier des DRH ou RH"},
                            status_code=400)

    if code_region:
        region = db.query(Region).filter(Region.code == code_region).first()
        if not region:
            logger.error(f"Région non trouvée : {code_region}")
            return JSONResponse(content={"error": "Région non trouvée"}, status_code=404)

    existing_user = db.query(User).filter(User.nom_utilisateur == nom_utilisateur, User.id != user_id).first()
    if existing_user:
        logger.error(f"Nom d'utilisateur déjà pris : {nom_utilisateur}")
        return JSONResponse(content={"error": "Ce nom d'utilisateur est déjà pris"}, status_code=400)

    try:
        user.nom_utilisateur = nom_utilisateur
        user.email = email
        if mot_de_passe:
            user.mot_de_passe_hash = get_password_hash(mot_de_passe)
        user.role = role
        user.code_region = code_region
        db.commit()
        db.refresh(user)
        logger.info(f"Utilisateur modifié : {nom_utilisateur}, rôle : {role}, région : {code_region}")
        return JSONResponse(content={"success": f"Utilisateur {nom_utilisateur} ({role}) modifié avec succès !"})
    except Exception as e:
        logger.error(f"Erreur lors de la modification de l'utilisateur : {str(e)}")
        return JSONResponse(content={"error": f"Erreur lors de la modification de l'utilisateur : {str(e)}"},
                            status_code=500)


@router.post("/supprimer_utilisateur/{user_id}", response_class=JSONResponse)
async def supprimer_utilisateur(
        user_id: int,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Supprime un utilisateur DRH ou RH avec une réponse JSON pour les requêtes AJAX.
    """
    logger.info(f"Tentative de suppression de l'utilisateur {user_id} par {current_user.nom_utilisateur}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à supprimer_utilisateur pour {current_user.nom_utilisateur}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"Utilisateur non trouvé : {user_id}")
        return JSONResponse(content={"error": "Utilisateur non trouvé"}, status_code=404)

    if user.role not in ["DRH", "RH"]:
        logger.error(f"Suppression non autorisée pour le rôle : {user.role}")
        return JSONResponse(content={"error": "Le Super Utilisateur peut uniquement supprimer des DRH ou RH"},
                            status_code=400)

    try:
        db.delete(user)
        db.commit()
        logger.info(f"Utilisateur supprimé : {user.nom_utilisateur}")
        return JSONResponse(content={"success": f"Utilisateur {user.nom_utilisateur} supprimé avec succès !"})
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'utilisateur : {str(e)}")
        return JSONResponse(content={"error": f"Erreur lors de la suppression de l'utilisateur : {str(e)}"},
                            status_code=500)


@router.get("/get_users", response_class=JSONResponse)
async def get_users(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Retourne la liste des utilisateurs DRH et RH en JSON pour le rechargement dynamique.
    """
    logger.info(
        f"Tentative de récupération des utilisateurs par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à get_users pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    utilisateurs = db.query(User).all()
    users_data = [
        {
            "id": user.id,
            "nom_utilisateur": user.nom_utilisateur,
            "email": user.email,
            "role": user.role,
            "code_region": user.code_region
        }
        for user in utilisateurs
    ]
    logger.info(f"Utilisateurs envoyés : {len(users_data)}")
    return JSONResponse(content=users_data)


@router.get("/get_stats", response_class=JSONResponse)
async def get_stats(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Retourne les statistiques en JSON pour le rechargement dynamique.
    """
    logger.info(
        f"Tentative de récupération des statistiques par {current_user.nom_utilisateur}, rôle : {current_user.role}")
    if current_user.role != "SUPER_USER":
        logger.error(f"Accès refusé à get_stats pour {current_user.nom_utilisateur}, rôle : {current_user.role}")
        return JSONResponse(content={"error": "Accès non autorisé"}, status_code=403)

    stats = {
        "total_users": db.query(User).filter(User.role.in_(["DRH", "RH"])).count(),
        "total_affectations": db.query(Affectation).filter(Affectation.status == AffectationStatus.PENDING).count(),
        "total_regions": db.query(Region).count()
    }
    logger.info(f"Statistiques envoyées : {stats}")
    return JSONResponse(content=stats)