# ================================================================================================
# FILE: resources.py
# Définition de toutes les ressources MCP
# ================================================================================================
# Gemini 01 07 2025:

import logging
from pathlib import Path
from config import DATA_DIR

logger = logging.getLogger(__name__)

def register_resources(mcp):
    """
    Enregistre toutes les fiches techniques de badminton comme ressources MCP.
    Scanne le dossier DATA_DIR pour trouver les fichiers .txt et les expose.
    
    Args:
        mcp: Instance FastMCP
    """
    
    if not DATA_DIR.exists():
        logger.warning(f"⚠️  Le dossier {DATA_DIR} n'existe pas. Vérifiez le volume Docker.")
        return
    FICHES_DIR = DATA_DIR / "fiches_techniques"
    # Recherche récursive pour supporter des sous-dossiers (Technique/, Stratégie/, etc.)
    text_files = list(FICHES_DIR.rglob("*.txt"))
    
    if not text_files:
        logger.warning(f"⚠️  Aucune fiche technique (.txt) trouvée dans {FICHES_DIR}")
        return
    
    # Enregistrer chaque fichier comme ressource
    for file_path in text_files:
        filename = file_path.name
        
        # Créer une URI propre et unique
        safe_name = (
            filename
            .replace(" ", "_")
            .replace("'", "")
            .replace("é", "e")
            .replace("è", "e")
            .replace("à", "a")
            .lower()
        )
        
        # URI sémantique pour aider le LLM à identifier le contexte
        uri = f"doc://badminton/fiches/{safe_name}"
        
        # Utiliser une closure pour capturer le chemin et les métadonnées spécifiques
        def make_reader(path: Path, original_name: str, doc_uri: str):
            """Factory function pour créer un lecteur de document isolé."""
            
            @mcp.resource(doc_uri)
            def read_document() -> str:
                f"""
                Fiche technique de Badminton : {original_name}
                
                Ce document contient des conseils officiels sur le badminton 
                (tactique, technique, stratégie, préparation ou prévention).
                """
                logger.info(f"🏸 Lecture de la fiche : '{original_name}'")
                
                if not path.exists():
                    error_msg = f"[Erreur] La fiche '{original_name}' est introuvable sur le disque."
                    logger.error(error_msg)
                    return error_msg
                
                try:
                    content = path.read_text(encoding="utf-8")
                    logger.info(f"✅ Fiche '{original_name}' transmise au LLM ({len(content)} carac.)")
                    return content
                except Exception as e:
                    error_msg = f"[Erreur] Impossible de lire la fiche '{original_name}': {str(e)}"
                    logger.error(error_msg)
                    return error_msg
            
            return read_document
        
        # Enregistrement effectif de la ressource dans FastMCP
        make_reader(file_path, filename, uri)
        logger.debug(f"resource registered: {filename} -> {uri}")
    
    logger.info(f"✅ {len(text_files)} fiches techniques de badminton chargées et prêtes.")




# import logging
# from pathlib import Path
# from typing import List, Dict
# from config import DATA_DIR

# logger = logging.getLogger(__name__)


# def register_resources(mcp):
#     """
#     Enregistre toutes les ressources MCP (documents statiques).
    
#     Args:
#         mcp: Instance FastMCP
#     """
    
#     if not DATA_DIR.exists():
#         logger.warning(f"⚠️  Le dossier {DATA_DIR} n'existe pas")
#         return
    
#     # Trouver tous les fichiers texte
#     text_files = list(DATA_DIR.glob("*.txt"))
    
#     if not text_files:
#         logger.warning(f"⚠️  Aucun fichier .txt trouvé dans {DATA_DIR}")
#         return
    
#     # Enregistrer chaque fichier comme ressource
#     for file_path in text_files:
#         filename = file_path.name
        
#         # Créer une URI sûre (remplacer caractères spéciaux)
#         safe_name = (
#             filename
#             .replace(" ", "_")
#             .replace("'", "")
#             .replace("é", "e")
#             .replace("è", "e")
#             .replace("à", "a")
#         )
        
#         uri = f"doc://documents/{safe_name}"
        
#         # Utiliser une closure pour capturer le chemin
#         def make_reader(path: Path, original_name: str, doc_uri: str):
#             """Factory function pour créer un lecteur de document."""
            
#             @mcp.resource(doc_uri)
#             def read_document() -> str:
#                 f"""
#                 Document: {original_name}
                
#                 Contient des informations et cours sur la guitare.
#                 """
#                 logger.info(f"📄 Lecture du document: '{original_name}'")
                
#                 if not path.exists():
#                     error_msg = f"[Erreur] Le fichier '{original_name}' n'existe plus."
#                     logger.error(error_msg)
#                     return error_msg
                
#                 try:
#                     content = path.read_text(encoding="utf-8")
#                     logger.info(f"✅ Document '{original_name}' lu ({len(content)} caractères)")
#                     return content
#                 except Exception as e:
#                     error_msg = f"[Erreur] Impossible de lire '{original_name}': {str(e)}"
#                     logger.error(error_msg)
#                     return error_msg
            
#             return read_document
        
#         # Enregistrer la ressource
#         make_reader(file_path, filename, uri)
#         logger.info(f"✅ Ressource enregistrée: {filename} -> {uri}")
    
#     logger.info(f"✅ {len(text_files)} ressource(s) enregistrée(s)")


# def list_available_resources() -> List[Dict[str, str]]:
#     """
#     Liste toutes les ressources disponibles.
    
#     Returns:
#         Liste de dictionnaires contenant les infos des ressources
#     """
#     if not DATA_DIR.exists():
#         return []
    
#     resources = []
#     for file_path in DATA_DIR.glob("*.txt"):
#         safe_name = (
#             file_path.name
#             .replace(" ", "_")
#             .replace("'", "")
#             .replace("é", "e")
#             .replace("è", "e")
#             .replace("à", "a")
#         )
        
#         resources.append({
#             "name": file_path.name,
#             "uri": f"doc://documents/{safe_name}",
#             "size": file_path.stat().st_size,
#             "description": f"Document: {file_path.name}"
#         })
    
#     return resources

