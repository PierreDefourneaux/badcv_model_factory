# ================================================================================================
# FILE: main.py
# Point d'entrée principal du serveur MCP
# ================================================================================================

import logging
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from config import logger, DATA_DIR, PORT_MCP
from tools import register_tools
from resources import register_resources, list_available_resources
# from prompts import register_prompts

HEALTHCHECK_FILE = Path("/tmp/mcp_ready.txt")

logger = logging.getLogger(__name__)

# ------------------------------- GESTION DU HEALTHCHECK  -----------------------------------------
def create_ready_signal():
    try:
        HEALTHCHECK_FILE.write_text("OK")
        logger.info(f"✅ SIGNAL HEALTHCHECK : Fichier créé -> {HEALTHCHECK_FILE}")
    except Exception as e:
        logger.error(f"❌ Impossible de créer le signal: {e}")

def remove_ready_signal():
    if HEALTHCHECK_FILE.exists():
        HEALTHCHECK_FILE.unlink()
        logger.info("🛑 SIGNAL HEALTHCHECK : Fichier supprimé.")

# ------------------------------- CREATION DU SERVEUR MCP  ----------------------------------------
def create_server() -> FastMCP:
    """
    Crée et configure le serveur MCP.
    
    Returns:
        Instance FastMCP configurée
    """
    mcp = FastMCP(
        "serveur_mcp_pierre_defourneaux",
        json_response=True,
        host="0.0.0.0",
        port=PORT_MCP
    )
    logger.info("🔧 Enregistrement des outils...")
    register_tools(mcp)
    logger.info("📚 Enregistrement des ressources...")
    register_resources(mcp)
    # logger.info("📝 Enregistrement des prompts...")
    # register_prompts(mcp)
    
    return mcp

# ------------------------------- INFOS DU SERVEUR MCP AU DEMARRAGE  ------------------------------
def display_server_info():
    """Affiche les informations du serveur au démarrage."""
    print("\n" + "=" * 70)
    print("SERVEUR MCP")
    print("=" * 70)
    print(f"Port: {PORT_MCP}")
    print(f"Dossier DATA: {DATA_DIR}")
    
    # Afficher les ressources disponibles
    resources = list_available_resources()
    print(f"\n📚 Documents disponibles ({len(resources)}):")
    if resources:
        for res in resources:
            print(f"  • {res['name']}")
            print(f"    URI: {res['uri']}")
            print(f"    Taille: {res['size']} octets")
    else:
        print("  Aucun document trouvé")
    
    print("\n" + "=" * 70)
    print("✅ Serveur prêt à recevoir des connexions")
    print("=" * 70 + "\n")


def main():
    """Point d'entrée principal."""
    try:
        mcp = create_server()
        display_server_info()
        create_ready_signal()
        logger.info("Démarrage du transport HTTP...")
        mcp.run(transport="streamable-http")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Arrêt du serveur...")
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}", exc_info=True)
        raise
    finally:
        remove_ready_signal()

if __name__ == "__main__":
    main()