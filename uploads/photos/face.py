import requests

url = "https://api-us.faceplusplus.com/facepp/v3/detect"
params = {
    "api_key": "40w_gxLhB1VZIQTcrJcpQ8S4ZWEiwyJz",
    "api_secret": "E_b2qpKdDR6td87RJuXKgssSBjmycWKa",
    "return_landmark": 1,  # 83-point landmarks
    "return_attributes": "gender,age"
}
files = {"image_file": open("mt234rfeu_webcam_photo.jpg", "rb")}

response = requests.post(url, files=files, data=params)
print(response.json())


import requests

# Configuration
API_KEY = "VOTRE_CLE_API"  # Remplacez par votre clé API
API_SECRET = "VOTRE_SECRET_API"  # Remplacez par votre secret API
URL = "https://api-us.faceplusplus.com/facepp/v3/faceset/create"

# Paramètres de la requête
params = {
    "api_key": API_KEY,
    "api_secret": API_SECRET,
    "outer_id": "uuid4",  # ID personnalisé (optionnel)
    "tags": "mindef,vip",  # Tags (optionnel)
    "face_tokens": "token1,token2,token3",  # Liste de face_tokens (optionnel, max 5)
    "force_merge": 0  # 0 = ne pas fusionner, 1 = fusionner (optionnel)
}

# Envoi de la requête POST
response = requests.post(URL, data=params)

# Affichage de la réponse
if response.status_code == 200:
    print("FaceSet créé avec succès !")
    print(response.json())  # Affiche la réponse JSON
else:
    print("Erreur lors de la création du FaceSet :")
    print(response.json())  # Affiche le message d'erreur