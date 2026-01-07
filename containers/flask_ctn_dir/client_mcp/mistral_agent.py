# ================================================================================================
# FILE: client/mistral_agent.py
# Agent intelligent utilisant Mistral API
# ================================================================================================

import asyncio
import json
import time
from typing import List, Dict
import requests
from .config import json_logger, MISTRAL_API_KEY

class MistralAgent:
    """Agent intelligent utilisant Mistral API pour orchestrer les outils MCP."""
    
    def __init__(self, model: str):
        self.model = model
        self.api_key = MISTRAL_API_KEY
        self.tools_info: List[dict] = []
        self.resources_info: List[dict] = []
        self.prompts_info: List[dict] = []
        self.mistral_url = "https://api.mistral.ai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def set_tools(self, tools: List[dict]):
        self.tools_info = tools
    
    def set_resources(self, resources: List[dict]):
        self.resources_info = resources

    def set_prompts(self, prompts: List[dict]):
        self.prompts_info = prompts
    
    def _prepare_tool_payload(self) -> List[dict]:
        """
        Convertit les outils MCP en format Mistral.
        INJECTE aussi un outil virtuel 'read_mcp_resource' pour permettre la lecture native.
        """
        mistral_tools = []
        
        # 1. Ajout des vrais outils du serveur (ex: preparer_analyse_video)
        for tool in self.tools_info:
            function_schema = {
                "name": tool['name'],
                "description": tool.get('description', 'Pas de description'),
                "parameters": tool.get('inputSchema', {"type": "object", "properties": {}})
            }
            mistral_tools.append({"type": "function", "function": function_schema})
        
        # 2. Injection de l'outil virtuel de lecture si des ressources existent
        if self.resources_info:
            mistral_tools.append({
                "type": "function",
                "function": {
                    "name": "read_mcp_resource",
                    "description": "Lit le contenu complet d'une fiche technique ou ressource à partir de son URI. Utilise ceci impérativement quand tu as besoin de consulter une fiche listée dans le contexte.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "L'URI exacte de la ressource (ex: doc://badminton/fiches/smash.txt)"
                            }
                        },
                        "required": ["uri"]
                    }
                }
            })
            
        return mistral_tools
    
    def _build_system_prompt(self) -> str:
        '''Construit le prompt système avec ressources ET prompts disponibles.'''
        parts = []
        
        # Identité de l'agent
        parts.append("Tu es Bad'IA, un coach expert en badminton (Technique, Tactique, Stratégie).")
        parts.append("Ton ton est encourageant, précis et sportif.")
        parts.append("Si une action nécessite une confirmation de l'utilisateur (comme lancer une analyse vidéo lourde), demande-lui confirmation avant d'utiliser l'outil.")
        
        # Ressources
        if self.resources_info:
            resources_text = "\n📚 Fiches techniques disponibles (Ressources MCP) :\n"
            for res in self.resources_info:
                uri = res.get('uri', '')
                name = res.get('name', uri.split('/')[-1])
                # On nettoie la description pour qu'elle soit concise
                desc = res.get('description', 'Fiche technique').strip()
                resources_text += f"- {name} (URI: {uri}) : {desc}\n"
            resources_text += "\nSi l'utilisateur pose une question théorique couverte par une fiche, utilise l'outil 'read_mcp_resource' avec l'URI correspondante."
            parts.append(resources_text)
        
        return "\n".join(parts)
    
    def _call_mistral(self, messages: List[dict], tools: List[dict] = None, temperature: float = 0.3) -> dict:
        """Appelle l'API Mistral avec retry automatique."""
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature
        }
        
        if tools:
            data["tools"] = tools
            data["tool_choice"] = "auto"
        
        json_logger.info(f"📢 REQ Mistral API: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.mistral_url,
                    headers=self.headers,
                    json=data,
                    timeout=30
                )
                
                # Log succinct pour éviter de polluer si tout va bien
                if response.status_code == 200:
                    json_logger.info(f"📣 RESP Mistral API: OK ({len(response.text)} bytes)")
                else:
                    json_logger.warning(f"📣 RESP Mistral API ERROR {response.status_code}: {response.text}")

                if response.status_code != 200:
                    raise RuntimeError(f"Erreur API Mistral {response.status_code}: {response.text}")
                
                return response.json()
                
            except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    json_logger.warning(f"⚠️  Erreur réseau (tentative {attempt + 1}), retry dans {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    json_logger.error(f"❌ Erreur réseau critique: {str(e)}")
                    raise
    
    def _sync_analyze(self, user_query: str) -> Dict:
        """Analyse une requête utilisateur et détermine l'action à effectuer."""
        tools_payload = self._prepare_tool_payload()
        system_prompt = self._build_system_prompt()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_query})
        
        try:
            response_data = self._call_mistral(messages, tools_payload)
            choice = response_data["choices"][0]
            
            # Cas 1 : Mistral veut déclencher un outil (Réel ou Virtuel 'read_mcp_resource')
            if choice.get("finish_reason") == 'tool_calls':
                tool_call = choice["message"]["tool_calls"][0]["function"]
                return {
                    "type": "tool",
                    "tool": tool_call["name"],
                    "arguments": json.loads(tool_call["arguments"]),
                    "explanation": f"🏸 J'active l'outil : {tool_call['name']}"
                }
            else:
                content = choice["message"].get("content", "Aucune réponse")
                
                # Cas 2 : Sécurité si Mistral mentionne l'URI sans appeler l'outil (Fallback)
                for res in self.resources_info:
                    uri = res.get('uri', '')
                    if uri in content:
                          return {
                            "type": "resource",
                            "resource_uri": uri,
                            "explanation": content
                        }
                
                # Cas 3 : Discussion simple
                return {
                    "type": "text",
                    "explanation": content
                }
        
        except Exception as e:
            json_logger.error(f"❌ Erreur analyse: {str(e)}")
            return {"type": "error", "explanation": f"Oups, j'ai raté mon smash (Erreur interne): {str(e)}"}
    
    async def analyze_query(self, user_query: str) -> Dict:
        return await asyncio.to_thread(self._sync_analyze, user_query)
    
    def _sync_reformulate(self, user_query: str, tool_result: dict) -> str:
        """Reformule un résultat JSON en langage naturel."""
        
        # Prompt de reformulation spécifique BADMINTON
        messages = [
            {
                "role": "system",
                "content": "Tu es Bad'IA, expert en badminton. Reformule les données techniques JSON reçues en une réponse claire, pédagogique et structurée pour le joueur. Utilise le vouvoiement."
            },
            {
                "role": "user",
                "content": f"Voici la question du joueur : '{user_query}'.\nVoici le résultat technique brut : {json.dumps(tool_result, ensure_ascii=False)}"
            }
        ]
        
        try:
            response_data = self._call_mistral(messages, temperature=0.7)
            return response_data["choices"][0]["message"]["content"]
        except Exception as e:
            json_logger.error(f"❌ Erreur reformulation: {e}")
            return self.format_result(tool_result)
    
    async def get_natural_response(self, user_query: str, tool_result: dict) -> str:
        return await asyncio.to_thread(self._sync_reformulate, user_query, tool_result)
    
    def format_result(self, result: dict) -> str:
        """Formate un résultat brut pour l'affichage (fallback)."""
        if not result: return "Aucun résultat."
        if isinstance(result, str): return result
        return json.dumps(result, indent=2, ensure_ascii=False)





# Avant le code de Gemini ci dessus du 07 01 2026 :
# import asyncio
# import json
# import time
# from typing import List, Dict
# import requests
# from .config import json_logger, MISTRAL_API_KEY

# class MistralAgent:
#     """Agent intelligent utilisant Mistral API pour orchestrer les outils MCP."""
    
#     def __init__(self, model: str):
#         self.model = model
#         self.api_key = MISTRAL_API_KEY
#         self.tools_info: List[dict] = []
#         self.resources_info: List[dict] = []
#         self.prompts_info: List[dict] = []
#         self.mistral_url = "https://api.mistral.ai/v1/chat/completions"
#         self.headers = {
#             "Authorization": f"Bearer {self.api_key}",
#             "Content-Type": "application/json"
#         }
    
#     def set_tools(self, tools: List[dict]):
#         """Configure la liste des outils disponibles."""
#         self.tools_info = tools
    
#     def set_resources(self, resources: List[dict]):
#         """Configure la liste des ressources disponibles."""
#         self.resources_info = resources

#     def set_prompts(self, prompts: List[dict]):
#         """Configure la liste des prompts disponibles."""
#         self.prompts_info = prompts
    
#     def _prepare_tool_payload(self) -> List[dict]:
#         """Convertit les outils MCP en format Mistral."""
#         mistral_tools = []
#         for tool in self.tools_info:
#             function_schema = {
#                 "name": tool['name'],
#                 "description": tool.get('description', 'Pas de description'),
#                 "parameters": tool.get('inputSchema', {"type": "object", "properties": {}})
#             }
#             mistral_tools.append({"type": "function", "function": function_schema})
#         return mistral_tools
    
#     def _build_system_prompt(self) -> str:
#         '''Construit le prompt système avec ressources ET prompts disponibles.'''
#         parts = []
        
#         # Ressources
#         if self.resources_info:
#             resources_text = "Ressources disponibles sur le serveur MCP:\\n"
#             for res in self.resources_info:
#                 uri = res.get('uri', '')
#                 name = res.get('name', uri.split('/')[-1])
#                 desc = res.get('description', 'Aucune description')
#                 resources_text += f"- {name} (URI: {uri}): {desc}\\n"
#             resources_text += "\\nSi l'utilisateur demande une ressource, réponds textuellement en mentionnant l'URI exacte."
#             parts.append(resources_text)
        
#         # Prompts
#         if self.prompts_info:
#             prompts_text = "\\nPrompts d'analyse disponibles :\\n"
#             for prompt in self.prompts_info:
#                 name = prompt.get('name', '')
#                 desc = prompt.get('description', 'Aucune description')
#                 prompts_text += f"- {name}: {desc}\\n"
#             prompts_text += "\\nSi l'utilisateur demande une analyse détaillée, tu peux mentionner qu'un prompt dédié existe."
#             parts.append(prompts_text)
        
#         return "\\n".join(parts)
    
#     def _call_mistral(self, messages: List[dict], tools: List[dict] = None, temperature: float = 0.3) -> dict:
#         """
#         Appelle l'API Mistral avec retry automatique.
        
#         Args:
#             messages: Liste des messages de conversation
#             tools: Liste des outils disponibles (optionnel)
#             temperature: Température pour la génération
            
#         Returns:
#             Réponse de Mistral
#         """
#         data = {
#             "model": self.model,
#             "messages": messages,
#             "temperature": temperature
#         }
        
#         if tools:
#             data["tools"] = tools
#             data["tool_choice"] = "auto"
        
#         json_logger.info(f"📢 REQ Mistral API: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
#         max_retries = 3
#         for attempt in range(max_retries):
#             try:
#                 response = requests.post(
#                     self.mistral_url,
#                     headers=self.headers,
#                     json=data,
#                     timeout=30
#                 )
                
#                 json_logger.info(f"📣 RESP Mistral API STATUT {response.status_code}: {response.text}")
                
#                 if response.status_code != 200:
#                     raise RuntimeError(f"Erreur API Mistral {response.status_code}: {response.text}")
                
#                 return response.json()
                
#             except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
#                 if attempt < max_retries - 1:
#                     wait_time = 2 ** attempt
#                     json_logger.warning(f"⚠️  Erreur réseau (tentative {attempt + 1}/{max_retries}), nouvelle tentative dans {wait_time}s...")
#                     time.sleep(wait_time)
#                 else:
#                     json_logger.error(f"❌ Erreur réseau après {max_retries} tentatives: {str(e)}")
#                     raise
    
#     def _sync_analyze(self, user_query: str) -> Dict:
#         """Analyse une requête utilisateur et détermine l'action à effectuer."""
#         tools_payload = self._prepare_tool_payload()
#         system_prompt = self._build_system_prompt()
        
#         messages = []
#         if system_prompt:
#             messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": user_query})
        
#         try:
#             response_data = self._call_mistral(messages, tools_payload)
#             choice = response_data["choices"][0]
            
#             if choice.get("finish_reason") == 'tool_calls':
#                 tool_call = choice["message"]["tool_calls"][0]["function"]
#                 return {
#                     "type": "tool",
#                     "tool": tool_call["name"],
#                     "arguments": json.loads(tool_call["arguments"]),
#                     "explanation": f"Utilisation de l'outil '{tool_call['name']}'"
#                 }
#             else:
#                 content = choice["message"].get("content", "Aucune réponse")
                
#                 # Vérifier si une ressource est mentionnée
#                 for res in self.resources_info:
#                     uri = res.get('uri', '')
#                     if uri in content or res.get('name', '') in content:
#                         return {
#                             "type": "resource",
#                             "resource_uri": uri,
#                             "explanation": content
#                         }
                
#                 return {
#                     "type": "text",
#                     "explanation": content
#                 }
        
#         except Exception as e:
#             json_logger.error(f"❌ Erreur lors de l'analyse: {str(e)}")
#             return {
#                 "type": "error",
#                 "explanation": f"Erreur: {str(e)}"
#             }
    
#     async def analyze_query(self, user_query: str) -> Dict:
#         """Version asynchrone de l'analyse."""
#         return await asyncio.to_thread(self._sync_analyze, user_query)
    
#     def _sync_reformulate(self, user_query: str, tool_result: dict) -> str:
#         """Reformule un résultat JSON en langage naturel."""
#         messages = [
#             {
#                 "role": "system",
#                 "content": "Tu es un assistant musical sympathique. Réponds de manière naturelle et concise aux questions sur les chansons et la guitare. Reformule les données JSON en phrases agréables à lire."
#             },
#             {
#                 "role": "user",
#                 "content": user_query
#             },
#             {
#                 "role": "assistant",
#                 "content": f"J'ai trouvé ces informations : {json.dumps(tool_result, ensure_ascii=False)}"
#             },
#             {
#                 "role": "user",
#                 "content": "Reformule ces informations de manière naturelle et conversationnelle."
#             }
#         ]
        
#         try:
#             response_data = self._call_mistral(messages, temperature=0.7)
#             return response_data["choices"][0]["message"]["content"]
#         except Exception as e:
#             json_logger.error(f"❌ Erreur reformulation: {e}")
#             return self.format_result(tool_result)
    
#     async def get_natural_response(self, user_query: str, tool_result: dict) -> str:
#         """Version asynchrone de la reformulation."""
#         return await asyncio.to_thread(self._sync_reformulate, user_query, tool_result)
    
#     def format_result(self, result: dict) -> str:
#         """Formate un résultat brut pour l'affichage."""
#         if not result:
#             return "Aucun résultat."
        
#         if isinstance(result, list):
#             return json.dumps(result, indent=2, ensure_ascii=False) if result else "Aucun résultat trouvé."
        
#         if 'response' in result and isinstance(result['response'], str):
#             return result['response']
        
#         if 'content' in result:
#             content = result['content']
#             if isinstance(content, list) and len(content) > 0 and 'text' in content[0]:
#                 return content[0]['text']
        
#         return json.dumps(result, indent=2, ensure_ascii=False)

