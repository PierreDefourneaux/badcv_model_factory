# ================================================================================================
# FILE: client/mcp_client.py
# Client HTTP pour communiquer avec le serveur MCP
# ================================================================================================

import json
from typing import Optional, List, Dict
import aiohttp
from .config import json_logger


class MCPHTTPClient:
    """Client MCP pour la communication via HTTP avec le serveur."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.session_id: Optional[str] = None
    
    async def __aenter__(self): # __aenter__ = méthode spéciale asynchrone
        self.session = aiohttp.ClientSession()
        await self.initialize() # dans la gestion du cycle de vie, c'est ici que se fait le "handshake"
        return self
    
    async def __aexit__(self, *args, **kwargs): # aexit est toujours la fin du cycle de vie du context manager
        """
        Appelé automatiquement à la sortie du bloc 'async with'.
        Garantit la fermeture propre de la session HTTP, même en cas d'erreur.
        """
        if self.session:
            await self.session.close()
    
    async def _send_request(self, method: str, params: dict = None) -> dict:
        """
        Envoie une requête JSON-RPC au serveur MCP.
        
        Args:
            method: Nom de la méthode MCP à appeler
            params: Paramètres de la méthode
            
        Returns:
            Résultat de la requête
        """
        if not self.session:
            raise RuntimeError("Session non initialisée")
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if self.session_id and method != "initialize":
            headers["mcp-session-id"] = self.session_id

        json_logger.info(f"Requête client MCP ({method}): {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        try:
            async with self.session.post(
                self.server_url,
                json=payload,
                headers=headers
            ) as response:
                if method == "initialize" and "mcp-session-id" in response.headers:
                    self.session_id = response.headers["mcp-session-id"]
                
                response_text = await response.text()
                
                if response.status != 200:
                    json_logger.error(f"❌ Erreur HTTP {response.status} pour {method}: {response_text}")
                    raise RuntimeError(f"Erreur HTTP {response.status}: {response_text}")
                
                try:
                    result = json.loads(response_text)
                except json.JSONDecodeError:
                    json_logger.error(f"❌ Erreur de parsing JSON pour {method}")
                    raise RuntimeError(f"Réponse JSON invalide du serveur: {response_text}")

                json_logger.info(f"Réponse serveur MCP ({method}) STATUT {response.status}: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if "error" in result:
                    raise RuntimeError(f"Erreur serveur: {result['error']}")
                
                return result.get("result", {})
        
        except aiohttp.ClientError as e:
            json_logger.error(f"❌ Erreur de connexion lors de l'envoi de {method}: {e}")
            raise RuntimeError(f"Erreur de connexion: {e}")
    
    async def initialize(self) -> dict:
        """Initialise la connexion avec le serveur MCP (Handshake)."""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "mcp-mistral-requests-client",
                "version": "1.0.0"
            }
        })
        return result
    
    async def list_tools(self) -> List[dict]:
        """Liste tous les outils disponibles sur le serveur."""
        result = await self._send_request("tools/list")
        return result.get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """
        Appelle un outil sur le serveur.
        
        Args:
            tool_name: Nom de l'outil à appeler
            arguments: Arguments pour l'outil
            
        Returns:
            Résultat de l'outil
        """
        params = {
            "name": tool_name,
            "arguments": arguments or {}
        }
        return await self._send_request("tools/call", params)
    
    async def list_resources(self) -> List[dict]:
        """Liste toutes les ressources disponibles sur le serveur."""
        result = await self._send_request("resources/list")
        return result.get("resources", [])
    
    async def read_resource(self, uri: str) -> dict:
        """
        Lit le contenu d'une ressource.
        
        Args:
            uri: URI de la ressource à lire
            
        Returns:
            Contenu de la ressource
        """
        params = {"uri": uri}
        return await self._send_request("resources/read", params)
    
    async def list_prompts(self) -> List[dict]:
        """Liste tous les prompts disponibles sur le serveur."""
        result = await self._send_request("prompts/list")
        return result.get("prompts", [])
    
    async def get_prompt(self, name: str, arguments: dict = None) -> dict:
        """
        Récupère un prompt formaté avec les arguments.
        
        Args:
            name: Nom du prompt
            arguments: Arguments pour le prompt
            
        Returns:
            Prompt formaté
        """
        params = {
            "name": name,
            "arguments": arguments or {}
        }
        return await self._send_request("prompts/get", params)

