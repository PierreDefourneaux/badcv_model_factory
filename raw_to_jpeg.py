import os
from PIL import Image
from pillow_heif import register_heif_opener
import cv2
import logging
from logging.handlers import SMTPHandler
import smtplib
from email.message import EmailMessage
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import sys

import io
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from dotenv import load_dotenv

# ----------------------------------- IMPORT DES SECRETS GITHUB------------------------------------
load_dotenv()
MDP_MAIL = os.getenv("MDP_MAIL")
MAIL_SENDER_ADRESS = os.getenv("MAIL_SENDER_ADRESS")
MAIL_RECIEVER = os.getenv("MAIL_RECIEVER")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
# ROOT_FOLDER_NAME = os.getenv("ROOT_FOLDER_NAME")
ROOT_FOLDER_ID = os.getenv("ROOT_FOLDER_ID")
# VIDEO_RAW_FOLDER_NAME = os.getenv("VIDEO_RAW_FOLDER_NAME")
# VIDEO_RAW_FOLDER_ID = os.getenv("VIDEO_RAW_FOLDER_ID")
PHOTO_RAW_FOLDER_NAME = os.getenv("PHOTO_RAW_FOLDER_NAME")
PHOTO_RAW_FOLDER_ID = os.getenv("PHOTO_RAW_FOLDER_ID")
CLEANED_DATA_FOLDER_NAME = os.getenv("CLEANED_DATA_FOLDER_NAME")
CLEANED_DATA_FOLDER_ID = os.getenv("CLEANED_DATA_FOLDER_ID")
# TREATED_LIST_FOLDER = os.getenv("TREATED_LIST_FOLDER")
# TREATED_LIST_FOLDER_ID = os.getenv("TREATED_LIST_FOLDER_ID")
GDRIVE_SERVICE_ACCOUNT_KEY = os.getenv("GDRIVE_SERVICE_ACCOUNT_KEY")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
SCOPES = [os.getenv("SCOPES")]

# ------------------------------------------------ CONFIG LOGGING ---------------------------------
logger = logging.getLogger(__name__)
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "raw_to_jpeg.log")
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8")])

# ------------------------------------ CONFIG REPORTING MAIL --------------------------------------

mail_handler = SMTPHandler(
    mailhost=(SMTP_HOST, 587),
    fromaddr=MAIL_SENDER_ADRESS,
    toaddrs=[MAIL_RECIEVER],
    subject="CRITICAL EVENT IN RAW TO JPEG IN BADIA PROJECT",
    credentials=(MAIL_SENDER_ADRESS, MDP_MAIL),
    secure=()
)
mail_handler.setLevel(logging.CRITICAL)
logger.addHandler(mail_handler)




# ------------------------------------------------ FONCTIONS -----------------------------------------
def envoyer_un_mail_reporting(nombre_images, MAIL_RECIEVER):
    try:
        msg = EmailMessage()
        msg["Subject"] = "REPORT RAW TO JPEG IN BADIA PROJECT"
        msg["From"] = MAIL_SENDER_ADRESS
        msg["To"] = MAIL_RECIEVER
        msg.set_content(f"""
            Le script raw_to_jpeg.py vient de se terminer.\n
            Il y a actuellement {nombre_images} images.""")

        with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT)) as smtp:
            smtp.starttls()
            smtp.login(MAIL_SENDER_ADRESS, MDP_MAIL)
            smtp.send_message(msg)
    except Exception as e:
        logger.critical(f"Erreur lors de l'envoi de mail : {e}")

# ----------------------------------- AUTHENTIFICATION ---------------------------------
def get_drive_service():
    """Authentification avec le Compte de Service (Local ou GitHub)."""
    try:
        # 1. Tentative de lecture du fichier local pour tests PC
        if SERVICE_ACCOUNT_FILE:
            logger.info(f"Authentification via fichier local : {SERVICE_ACCOUNT_FILE}")
            creds = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        
        # 2. Lecture depuis les secrets GitHub
        else:
            logger.info("Authentification via Secret GitHub (GDRIVE_SERVICE_ACCOUNT_KEY)")
            json_secret = os.getenv("GDRIVE_SERVICE_ACCOUNT_KEY")
            
            if not json_secret:
                logger.critical("Le Secret 'GDRIVE_SERVICE_ACCOUNT_KEY' est vide ou introuvable.")
                return None

            try:
                service_account_info = json.loads(json_secret)
            except json.JSONDecodeError as e:
                logger.critical(f"Le format du Secret JSON est invalide : {e}")
                return None

            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES)
        
        # 3. Création du service
        service = build('drive', 'v3', credentials=creds)
        return service

    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'authentification Drive : {e}")
        return None

# ----------------------------------- FONCTIONS DRIVE ----------------------------------
def get_over_1000_existing_names(service, folder_id):
    """Récupère TOUS les noms de fichiers d'un dossier, peu importe le nombre en gérant la limite de 1000 de google drive."""
    names = set()
    page_token = None
    while True:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(name)",
            pageSize=1000,
            pageToken=page_token
        ).execute()
        for f in results.get('files', []):
            names.add(f['name'])
        page_token = results.get('nextPageToken')
        if not page_token:
            break      
    return names

def process_photos(service, existing_clean_files, PHOTO_RAW_FOLDER_NAME):
    # Lister les fichiers dans RAW
    results_raw = service.files().list(
        q=f"'{PHOTO_RAW_FOLDER_ID}' in parents and trashed = false",
        fields="files(id, name)"
    ).execute()
    raw_files = results_raw.get('files', [])

    logger.info(f"Nombre de fichiers dans photos clean :{len(existing_clean_files)}")
    if len(raw_files)>5:
        logger.critical(
            f"Il y a {len(raw_files)} fichiers dans {PHOTO_RAW_FOLDER_NAME}. "
            f"Le seuil bloquant de 800 fichiers dans photos raw sera bientôt atteint. "
            f"Il faut déplacer les fichiers dans le dossier 'archives'. "
            )
    elif len(raw_files)>8:
        logger.critical(
            f"INTERRUPTION DU SCRIPT : {len(raw_files)} fichiers trouvés. "
            f"Le seuil maximal de 800 est dépassé. Nettoyage requis dans {PHOTO_RAW_FOLDER_NAME}."
            )
        sys.exit(1)
    else :
        logger.info(f"Nombre de fichiers dans photos raw :{len(raw_files)}")

    # wrong_ext_pic = 0
    # already_treated_pic = 0
    # new_rec_pic = 0

    # EXTENSIONS_IMAGES = (".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")

    # for file_drive in raw_files:
    #     file_name = file_drive['name']
    #     file_id = file_drive['id']

    #     if not file_name.lower().endswith(EXTENSIONS_IMAGES):
    #         logger.info(f"{file_name}: extension incompatible")
    #         wrong_ext_pic += 1
    #         continue

    #     jpeg_name = file_name.rsplit(".", 1)[0] + ".jpg"
        
    #     # Vérification si déjà traité
    #     if jpeg_name in existing_clean_files:
    #         already_treated_pic += 1
    #         continue

    #     try:
    #         # --- TÉLÉCHARGEMENT ---
    #         request = service.files().get_media(fileId=file_id)
    #         file_stream = io.BytesIO()
    #         downloader = MediaIoBaseDownload(file_stream, request)
    #         done = False
    #         while not done:
    #             _, done = downloader.next_chunk()
            
    #         # --- CONVERSION EN MÉMOIRE ---
    #         file_stream.seek(0)
    #         img = Image.open(file_stream)
            
    #         # Conversion RGB (nécessaire pour HEIC/PNG vers JPEG)
    #         if img.mode in ("RGBA", "P", "CMYK"):
    #             img = img.convert("RGB")
            
    #         output_buffer = io.BytesIO()
    #         img.save(output_buffer, format="JPEG", quality=95)
    #         output_buffer.seek(0)

    #         # --- UPLOAD VERS DRIVE ---
    #         file_metadata = {
    #             'name': jpeg_name,
    #             'parents': [CLEANED_DATA_FOLDER_ID]
    #         }
    #         media = MediaIoBaseUpload(output_buffer, mimetype='image/jpeg')
    #         service.files().create(body=file_metadata, media_body=media, fields='id').execute()

    #         logger.info(f"Converti et uploadé : {jpeg_name}")
    #         new_rec_pic += 1

    #     except Exception as e:
    #         logger.error(f"Erreur lors du traitement de {file_name} : {e}")

    # logger.info(f"""Rapport final :
    #     {new_rec_pic} nouvelles images enregistrées sur Drive,
    #     {already_treated_pic} images ignorées car déjà présentes dans {CLEANED_DATA_FOLDER_NAME},
    #     {wrong_ext_pic} fichiers ignorés (extension incompatible)""")


################################################################################################################################
################################################################################################################################
################################################################################################################################

# ----------------------------------- EXECUTION ----------------------------------------

if __name__ == "__main__":
    logger.info("Début d'une execution raw_to_jpeg.py")
    try:
        service = get_drive_service()
        existing_clean_files = get_over_1000_existing_names(service, CLEANED_DATA_FOLDER_ID)
        process_photos(service, existing_clean_files, PHOTO_RAW_FOLDER_NAME)
    except Exception as e:
        logger.error(f"Une erreur est survenue : {e}")

# ------------------------------------------------ PHOTOS -----------------------------------------
# register_heif_opener() # ajoute un décodeur HEIF pou PIL
# EXTENSIONS_IMAGES = (".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp")
# wrong_ext_pic =0
# already_treated_pic = 0
# new_rec_pic =0
# for file in os.listdir(PHOTO_RAW_FOLDER_NAME):
#     if not file.lower().endswith(EXTENSIONS_IMAGES):
#         logger.info(f"{file}: extension incompatible")
#         wrong_ext_pic +=1
#         continue
#     jpeg_name = file.rsplit(".", 1)[0] + ".jpg" # le 1 dans rsplit c'est 1 coupure (part toujours de la droite)
#     jpeg_path = os.path.join(CLEANED_DATA_FOLDER_NAME, jpeg_name)
#     if os.path.exists(jpeg_path):
#         already_treated_pic += 1
#         continue
#     img = Image.open(os.path.join(PHOTO_RAW_FOLDER_NAME, file))
#     img.save(jpeg_path, format="JPEG", quality=95)
#     new_rec_pic += 1
# logger.info(f"""Depuis le dossier photos_terrains_raw :
#     {new_rec_pic} nouvelles images enregistrées,
#     {already_treated_pic} images laissées car déjà traitées,
#     {wrong_ext_pic} fichiers non traités car ayant une extension incompatible""")

# ------------------------------------------------ VIDEOS ------------------------------------------------------
# wrong_ext_vid =0
# already_treated_vid = 0
# new_rec_vid =0
# new_video_names = []
# new_saved_pics_counts = []
# with open(treated_videos_path, "r", encoding="utf-8") as f:
#     treated_videos = set(line.strip() for line in f if line.strip())
# for video_file in os.listdir(raw_videos_folder):
#     if not video_file.lower().endswith((".mp4", ".mov", ".avi", ".mkv")):
#         logger.info(f"{video_file}: extension non compatible")
#         wrong_ext_vid += 1
#         continue
#     video_path = os.path.join(raw_videos_folder, video_file)
#     video_name = os.path.splitext(video_file)[0] #autre manière de split : coupe à l'extension
#     if video_name in treated_videos:
#         already_treated_vid += 1
#         continue
#     cap = cv2.VideoCapture(video_path)
#     if not cap.isOpened():
#         logger.info(f"Impossible d'ouvrir {video_file}")
#         continue
#     fps = cap.get(cv2.CAP_PROP_FPS)
#     if fps <= 0:
#         logger.info(f"FPS invalide pour {video_file}")
#         cap.release()
#         continue
#     frame_interval = int(round(fps)) # pour enregistrer une image par seconde
#     frame_idx = 0
#     saved_idx = 0
#     # Début de la boucle de frames
#     while True:
#         not_seen_frame_label, frame = cap.read()
#         if not not_seen_frame_label:
#             break
#         if frame_idx % frame_interval == 0: # si frame_idx est un multiple entier de frame_interval
#             jpeg_name = f"{video_name}_frame_{saved_idx:06d}.jpg"
#             jpeg_path = os.path.join(destination_folder, jpeg_name)
#             if not os.path.exists(jpeg_path):
#                 cv2.imwrite(jpeg_path, frame)
#             saved_idx += 1
#         frame_idx += 1
#     with open(treated_videos_path, "a", encoding="utf-8") as f:
#         f.write(video_name + "\n")
#     treated_videos.add(video_name)
#     cap.release()
#     new_rec_vid +=1
#     new_video_names.append(video_name)
#     new_saved_pics_counts.append(saved_idx)
# logger.info(f"""Depuis le dossier videos_terrains_raw :
#     {new_rec_vid} nouvelles vidéos traitées : {new_video_names},
#     cela représente {new_saved_pics_counts} nouvelles images,
#     {already_treated_vid} vidéos laissées car déjà traitées,
#     {wrong_ext_vid} fichiers non traités car ayant une extension incompatible""")

# ------------------------------------------------ RAPPORT ------------------------------------------------------
# not_jpeg = 0
# for file in os.listdir(destination_folder):
#     if not file.lower().endswith(('.jpg', '.jpeg')):
#         logger.warning(f"Le fichier {file} n'est pas un jpg")
#         not_jpeg += 1
# if not_jpeg != 0:
#     logger.warning(f"{not_jpeg} fichier(s) ne sont pas des jpg dans photos_terrain_clean")
# nombre_images = len(os.listdir(destination_folder))
# logger.info(f"AU TOTAL : {nombre_images} images dans photos_terrain_clean\n\n")
# nombre_images = 5
# envoyer_un_mail_reporting(nombre_images, MAIL_RECIEVER)