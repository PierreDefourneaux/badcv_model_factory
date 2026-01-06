# ================================================================================================
# FILE: tools.py
# Définition de l'outil de redirection vers l'analyse vidéo Badminton
# ================================================================================================

import logging
from typing import Dict

logger = logging.getLogger(__name__)

def register_tools(mcp):
    """
    Enregistre l'outil d'aiguillage vers l'analyse vidéo.
    """
    
    @mcp.tool()
    def preparer_analyse_video() -> Dict:
        """
        Prépare l'interface pour l'analyse d'une vidéo de badminton (détection de coups, 
        trajectoire du volant, etc.). 
        À utiliser quand l'utilisateur veut analyser son jeu ou uploader une vidéo.
        """
        logger.info("🏸 Requête d'analyse vidéo reçue")
        
        return {
            "action": "redirect_to_upload",
            "message": "Je prépare l'interface d'analyse. Veuillez sélectionner votre vidéo de badminton.",
            "status": "ready"
        }
    
    logger.info("✅ Outil d'analyse badminton enregistré")