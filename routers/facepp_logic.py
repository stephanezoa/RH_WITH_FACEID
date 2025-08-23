import requests
import logging
from typing import Dict, Optional

# Configurer le logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FacePPComparator:
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialisation simple avec les clés API
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.url = "https://api-us.faceplusplus.com/facepp/v3/compare"
        logger.info("FacePPComparator initialisé avec succès")

    def compare(self, face_token: str, image_path: str) -> dict:
        """
        Compare un face_token avec une image locale

        Args:
            face_token: Le token du visage à comparer
            image_path: Chemin vers l'image à comparer

        Returns:
            Résultat de la comparaison au format JSON
        """
        logger.info(f"Début de la comparaison faciale pour face_token : {face_token}, image : {image_path}")
        try:
            with open(image_path, 'rb') as image_file:
                response = requests.post(
                    self.url,
                    files={'image_file2': image_file},
                    data={
                        'api_key': self.api_key,
                        'api_secret': self.api_secret,
                        'face_token1': face_token
                    }
                )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Résultat de la comparaison : {result}")
            return result
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison faciale : {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Réponse d'erreur de l'API : {e.response.text}")
            return {'error': str(e)}


def detect_face(image_path: str, api_key: str, api_secret: str) -> Dict:
    """
    Détecte un visage dans une image et retourne ses attributs

    Args:
        image_path: Chemin vers l'image locale
        api_key: Clé API Face++
        api_secret: Secret API Face++

    Returns:
        Dictionnaire contenant la réponse de l'API de détection
    """
    logger.info(f"Début de la détection faciale pour image : {image_path}")
    url = "https://api-us.faceplusplus.com/facepp/v3/detect"
    params = {
        "api_key": api_key,
        "api_secret": api_secret,
        "return_landmark": 1,
        "return_attributes": "gender,age"
    }
    try:
        with open(image_path, "rb") as image_file:
            files = {"image_file": image_file}
            response = requests.post(url, files=files, data=params)
        response.raise_for_status()
        result = response.json()
        logger.info(f"Résultat de la détection faciale : {result}")
        return result
    except Exception as e:
        logger.error(f"Erreur lors de la détection faciale : {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Réponse d'erreur de l'API : {e.response.text}")
        return {'error': str(e)}