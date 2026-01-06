# ================================================================================================
# FILE: client/config.py
# Configuration et initialisation du logging
# ================================================================================================

import os
import logging
from pathlib import Path

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MCP_SERVER_URL = "http://MCP_SERVER_CONTAINER:8000/mcp"
MISTRAL_MODEL = "mistral-small-latest"

CLIENT_DIR = Path("/app/logs_ctn_flask")
LOG_FILE = CLIENT_DIR / "mcp_client.log"

# ============= CONFIGURATION DU LOGGING =============

# Logger pour les échanges JSON détaillés (fichier uniquement)
json_logger = logging.getLogger('mcp_json')
json_logger.setLevel(logging.INFO)
json_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
json_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', 
    datefmt='%H:%M:%S'
))
json_logger.addHandler(json_handler)
json_logger.propagate = False

# Logger pour les messages système et utilisateur (Console Docker "docker compose logs -f")
user_logger = logging.getLogger('mcp_user')
user_logger.setLevel(logging.INFO)
user_handler = logging.StreamHandler()
user_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))
user_logger.addHandler(user_handler)
user_logger.propagate = False

if not MISTRAL_API_KEY:
    user_logger.error("❌ MISTRAL_API_KEY manquante dans les variables d'environnement !")

