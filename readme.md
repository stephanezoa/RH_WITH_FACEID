My RH Project
Un système RH décentralisé construit avec FastAPI, utilisant SQLite3 comme base de données et Jinja2 pour le frontend rendu côté serveur. Supporte la connexion et la création de comptes pour deux rôles : DRH (Super Admin) et RH (Admin régional).
Instructions de configuration

Cloner le dépôt
git clone <url-du-dépôt>
cd my-rh-project


Installer les dépendances
pip install -r backend/requirements.txt


Configurer les variables d'environnementCréer un fichier .env dans le dossier backend/ :
DATABASE_URL=sqlite:///backend/data/rh_project.db
JWT_SECRET=votre-clé-secrète


Lancer l'application
cd backend
uvicorn main:app --reload


Accéder à l'application

API : http://localhost:8000
Frontend : http://localhost:8000/login
Docs API : http://localhost:8000/docs



Fonctionnalités principales

Connexion : Authentification sécurisée avec JWT pour DRH et RH.
Création de compte : Le DRH peut créer des utilisateurs (DRH ou RH) avec une région attribuée.
Rôles : DRH (national, accès total) et RH (régional, accès limité).
Base de données : SQLite3 pour simplicité, avec transition possible vers PostgreSQL.

Points d'API



Endpoint
Méthode
Description
Accès



/api/auth/login
POST
Connexion utilisateur (JWT)
Tous


/api/users
POST
Créer un utilisateur
DRH


/api/users/create
GET
Afficher formulaire de création
DRH


Transition vers PostgreSQL

Mettre à jour core/config.py avec l'URL PostgreSQL :DATABASE_URL = "postgresql://utilisateur:motdepasse@localhost:5432/rh_project"


Modifier core/database.py pour supprimer connect_args spécifique à SQLite :engine = create_engine(DATABASE_URL)


Créer la base de données PostgreSQL et appliquer les migrations :createdb rh_project
python -m backend.main



Notes

SQLite3 est utilisé pour la simplicité ; PostgreSQL est recommandé pour la production.
Assurez-vous que le fichier .env contient une clé JWT sécurisée.
Le DRH peut créer des utilisateurs RH avec une région spécifique, tandis que les RH sont limités à leur région.
