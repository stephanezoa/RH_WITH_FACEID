@echo off
setlocal enabledelayedexpansion

title Lancement RH_WITH_FACEID

echo ===================================================
echo     Demarrage du projet RH_WITH_FACEID
echo ===================================================

:: Verification de la presence de Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH de Windows.
    pause
    exit /b 1
)

:: Creation de l'environnement virtuel s'il n'existe pas
if not exist "venv" (
    echo [INFO] Creation de l'environnement virtuel en cours...
    python -m venv venv
)

:: Activation de l'environnement virtuel
echo [INFO] Activation de l'environnement virtuel...
call venv\Scripts\activate

:: Installation des dependances (mise a jour si necessaire)
echo [INFO] Verification et installation des dependances...
pip install -r requirements.txt --quiet

:: Gestion des ports et des collisions
set PORT=8000

:check_port
:: Verifier si le port est en ecoute
netstat -ano | findstr LISTENING | findstr ":!PORT! " >nul
if %errorlevel% equ 0 (
    echo [ATTENTION] Le port !PORT! est deja utilise. Test du port suivant...
    set /a PORT+=1
    goto check_port
)

echo [INFO] Port disponible trouve : !PORT!

:: Ouverture automatique du navigateur
echo [INFO] Ouverture du navigateur sur http://localhost:!PORT! ...
start http://localhost:!PORT!

:: Lancement du serveur uvicorn
echo ===================================================
echo     Serveur en cours d'execution...
echo     (Fermez cette fenetre pour arreter le serveur)
echo ===================================================
uvicorn main:app --host 0.0.0.0 --port !PORT!

pause
