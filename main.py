from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from core.database import Base, engine, SessionLocal
from core.security import get_password_hash
from models.user import User
from models.region import Region
from models.personnel import Personnel
from models.affectation import Affectation
from routers import auth, users
import logging
from routers import affectations
from routers import superuser

# Configurer le logging pour déboguer
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API My RH Project")

app.include_router(superuser.router)
app.include_router(affectations.router)
# Montage des fichiers statiques et templates
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
templates = Jinja2Templates(directory="templates")

# Création des tables de la base de données
logger.info("Création des tables de la base de données...")
Base.metadata.create_all(bind=engine)
logger.info("Tables créées : %s", Base.metadata.tables.keys())

# Initialisation des données par défaut
def init_db():
    db: Session = SessionLocal()
    try:
        # Vérifier si un Super Utilisateur existe
        super_user = db.query(User).filter(User.nom_utilisateur == "superuser").first()
        if not super_user:
            super_user = User(
                nom_utilisateur="superuser",
                mot_de_passe_hash=get_password_hash("admin123"),
                email="superuser@example.com",
                role="SUPER_USER",
                code_region=None
            )
            db.add(super_user)
            db.commit()
            db.refresh(super_user)
            logger.info("Super utilisateur créé : superuser, rôle : SUPER_USER")

        # Vérifier si un utilisateur DRH existe
        drh_user = db.query(User).filter(User.nom_utilisateur == "drhuser").first()
        if not drh_user:
            drh_user = User(
                nom_utilisateur="drhuser",
                mot_de_passe_hash=get_password_hash("drh123"),
                email="drhuser@example2.com",
                role="DRH",
                code_region="DOUALA"
            )
            db.add(drh_user)
            db.commit()
            db.refresh(drh_user)
            logger.info("Utilisateur DRH créé : drhuser, rôle : DRH")

        # Vérifier si un utilisateur RH existe
        rh_user = db.query(User).filter(User.nom_utilisateur == "rhuser").first()
        if not rh_user:
            rh_user = User(
                nom_utilisateur="rhuser",
                mot_de_passe_hash=get_password_hash("rh123"),
                email="rhuser@example.com",
                role="RH",
                code_region="PARIS"
            )
            db.add(rh_user)
            db.commit()
            db.refresh(rh_user)
            logger.info("Utilisateur RH créé : rhuser, rôle : RH")

        # Vérifier si des régions existent
        regions_count = db.query(Region).count()
        if regions_count == 0:
            default_regions = [
                Region(code="AD", nom="Adamaoua"),
                Region(code="CE", nom="Centre"),
                Region(code="ES", nom="Est"),
                Region(code="EN", nom="Extreme-Nord"),
                Region(code="LI", nom="Littoral"),
                Region(code="NO", nom="Nord"),
                Region(code="NW", nom="Nord-Ouest"),
                Region(code="OU", nom="Ouest"),
                Region(code="SU", nom="Sud"),
                Region(code="SW", nom="Sud-Ouest")
            ]

            db.add_all(default_regions)
            db.commit()
            logger.info("Régions créées : PARIS, DOUALA")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur lors de l'initialisation de la base de données : {e}")
        raise
    finally:
        db.close()

# Appeler l'initialisation au démarrage
init_db()

# Inclusion des routeurs
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])

# Routes pour la gestion de la connexion
@app.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/")
async def root():
    return RedirectResponse(url="/login")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token")
    return response