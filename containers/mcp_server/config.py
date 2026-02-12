# ================================================================================================
# FILE: config.py
# Configuration centralisée
# ================================================================================================
import os
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CONFIG")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
PORT_MCP = 8000

if not MISTRAL_API_KEY:
    logger.critical("ERREUR : MISTRAL_API_KEY manquante. Vérifier le fichier .env ou la configuration Docker.")
    raise EnvironmentError("MISTRAL_API_KEY non définie.")
else:
    masked_key = f"{MISTRAL_API_KEY[:4]}...{MISTRAL_API_KEY[-4:]}"
    logger.info(f"MISTRAL_API_KEY chargée avec succès : {masked_key}")

DATA_DIR_PATH = os.getenv("DATA_DIR", "/app/badia_server_files")
DATA_DIR = Path(DATA_DIR_PATH)

if not DATA_DIR.exists():
    logger.error(f"ATTENTION : Le répertoire de données {DATA_DIR} n'existe pas.")
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Répertoire {DATA_DIR} créé automatiquement.")
    except Exception as e:
        logger.critical(f"Impossible de créer le répertoire {DATA_DIR} : {e}")
        sys.exit(1)
else:
    logger.info(f"Répertoire de données validé : {DATA_DIR}")
    if not os.access(DATA_DIR, os.W_OK):
        logger.warning(f"Le répertoire {DATA_DIR} n'a pas les droits d'écriture !")