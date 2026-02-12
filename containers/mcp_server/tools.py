# ================================================================================================
# FILE: tools.py
# Définition de l'outil de redirection vers l'analyse vidéo Badminton
# ================================================================================================

import logging
from pydantic import BaseModel, Field
from mcp.server.fastmcp import Context, FastMCP
from typing import Dict

logger = logging.getLogger(__name__)

# 1. Définition du formulaire (Form mode)
class BadmintonVideoInfo(BaseModel):
    four_corners_visible: bool = Field(
        description="La vidéo montre-t-elle toujours les 4 coins du terrain ou pas ?"
    )

def register_tools(mcp):
    """
    Enregistre l'outil d'aiguillage vers l'analyse vidéo.
    """
    @mcp.tool()
    async def preparer_analyse_video(ctx: Context) -> Dict:
        """
        Prépare l'interface pour l'analyse d'une vidéo de badminton.
        Demande des précisions sur la visibilité des 4 coins du terrain.
        """
        logger.info("🏸 Requête d'analyse vidéo reçue")

        # 2. Lancement de l'élicitation
        # Le tool s'arrête ici et attend la réponse de l'utilisateur via l'interface du client
        # ici puisque c'est la méthode elicit et pas elicit_url : c'est une elicitation de type FORM
        result = await ctx.elicit(
            message="Avant de commencer, j'ai besoin de savoir si la vidéo montre bien les 4 coins du terrain.",
            schema=BadmintonVideoInfo
        )

        # 3. Traitement de la réponse
        # L'action peut être "accept", "decline" ou "cancel"
        if result.action == "accept" and result.data:
            visibilite = result.data.four_corners_visible
            message_suite = "Parfait, je configure l'analyse pour 4 coins bien visibles." if visibilite else "D'accord, je vais adapter la détection pour un terrain partiellement visible."
            
            return {
                "action": "redirect_to_upload",
                "message": f"{message_suite} Veuillez sélectionner votre vidéo.",
                "status": "ready",
                "corners_visible": visibilite
            }
        
        # Gestion du refus ou de l'annulation par l'utilisateur
        return {
            "action": "stop",
            "message": "L'analyse a été annulée car les informations nécessaires n'ont pas été fournies.",
            "status": "cancelled"
        }
    
    logger.info("✅ Outil d'analyse badminton enregistré")


# Points clés à retenir :
# Mode Formulaire : Le SDK Python utilise par défaut le "form mode", qui permet de collecter des données structurées et non sensibles directement dans l'interface du client MCP (comme Claude Desktop),.
# Actions de réponse : L'objet retourné par ctx.elicit() contient un champ action. Vous devez vérifier si l'utilisateur a cliqué sur "Accepter" (accept) avant d'accéder aux données dans result.data,.
# Validation automatique : Le client MCP utilise votre schéma Pydantic pour valider la saisie de l'utilisateur avant même que la réponse ne revienne à votre outil.
# L'élicitation est comme un assistant de vol qui interrompt brièvement le pilote pour demander : "Voulez-vous du café ou du thé ?" avant de reprendre la navigation ; elle assure que le reste du voyage se déroule avec les bonnes informations en main.