# ================================================================================================
# FILE: flask_app.py
# ================================================================================================

import os
import json
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import asyncio

# Import depuis ton package client_mcp
from client_mcp import MCPHTTPClient, MistralAgent, MCP_SERVER_URL, MISTRAL_MODEL, user_logger

app = Flask(__name__)

# --- CONFIGURATION ---
# Volume mappé : assure-toi que ce chemin correspond à ton docker-compose
UPLOAD_FOLDER = '/app/badia_files/uploads' 
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Création récursive du dossier s'il n'existe pas (Fail Fast)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    user_logger.info(f"✅ Dossier d'upload prêt : {UPLOAD_FOLDER}")
except Exception as e:
    user_logger.critical(f"❌ Impossible de créer le dossier {UPLOAD_FOLDER}: {e}")
    # On ne quitte pas forcément (exit(1)) pour ne pas tuer le conteneur en boucle, 
    # mais l'upload ne marchera pas.
    
# Initialisation de l'agent
agent = MistralAgent(model=MISTRAL_MODEL)


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
async def chat():
    """Route API principale du Chatbot."""
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    try:
        # 1. Connexion (Context Manager asynchrone)
        async with MCPHTTPClient(MCP_SERVER_URL) as mcp_client:
            
            # 2. Introspection du serveur MCP
            tools = await mcp_client.list_tools()
            resources = await mcp_client.list_resources()
            
            # 3. Configuration de l'agent avec le contexte actuel
            agent.set_tools(tools)
            agent.set_resources(resources)
            
            # 4. Décision de l'agent
            analysis = await agent.analyze_query(user_message)
            
            response_text = ""

            # --- CAS : APPEL D'OUTIL (TOOL) ---
            if analysis.get('type') == 'tool':
                tool_name = analysis['tool']
                tool_args = analysis.get('arguments', {})

                # === A. INTERCEPTION : Outil virtuel de lecture ===
                # C'est ici qu'on capture l'outil "imaginaire" injecté dans mistral_agent.py
                if tool_name == "read_mcp_resource":
                    uri = tool_args.get('uri')
                    user_logger.info(f"📖 Lecture native MCP via outil virtuel : {uri}")
                    
                    try:
                        # Appel de la méthode NATIVE du protocole (resources/read)
                        resource_content = await mcp_client.read_resource(uri)
                        
                        # Extraction du texte (Format standard MCP: {contents: [{text: "..."}]})
                        text_content = "Contenu vide ou illisible."
                        if resource_content and "contents" in resource_content and len(resource_content["contents"]) > 0:
                            text_content = resource_content["contents"][0].get("text", "")
                        
                        # Reformulation par l'agent pour répondre à l'utilisateur
                        response_text = await agent.get_natural_response(
                            f"Voici le contenu de la fiche technique demandée. Utilise-le pour répondre précisément à la question : '{user_message}'", 
                            {"content": text_content}
                        )
                    except Exception as e:
                        user_logger.error(f"❌ Erreur lors de la lecture ressource : {e}")
                        response_text = "Désolé, je n'ai pas réussi à accéder à cette fiche technique pour le moment."

                # === B. OUTILS STANDARD (Exécutés sur le serveur MCP) ===
                else:
                    user_logger.info(f"🛠️  Appel outil serveur : {tool_name}")
                    
                    tool_result = await mcp_client.call_tool(
                        tool_name,
                        tool_args
                    )
                    
                    # Gestion du contenu structuré de FastMCP
                    structured_content = tool_result.get('content', [])
                    actual_result = tool_result
                    
                    # Tentative de parsing JSON si le résultat est dans une string
                    try:
                        if isinstance(structured_content, list) and len(structured_content) > 0:
                            text_val = structured_content[0].get('text', '{}')
                            actual_result = json.loads(text_val)
                    except:
                        pass # Ce n'était pas du JSON, on garde le brut
                    
                    # REDIRECTION : Si l'outil demande explicitement l'upload
                    if isinstance(actual_result, dict) and actual_result.get("action") == "redirect_to_upload":
                        return jsonify({
                            "response": actual_result.get("message", "Ok, passons à l'upload."),
                            "redirect": "/upload_video"
                        })

                    # Reformulation humaine du résultat de l'outil
                    response_text = await agent.get_natural_response(user_message, tool_result)

            # --- CAS : LECTURE DE RESSOURCE (Fallback texte) ---
            # Ce cas arrive si Mistral mentionne l'URI dans le texte sans appeler l'outil
            elif analysis.get('type') == 'resource':
                user_logger.info(f"📖 Lecture ressource (Fallback) : {analysis['resource_uri']}")
                res_content = await mcp_client.read_resource(analysis['resource_uri'])
                
                # Extraction propre du texte pour le fallback aussi
                text_content = str(res_content)
                if isinstance(res_content, dict) and "contents" in res_content:
                     text_content = res_content["contents"][0].get("text", "")

                response_text = await agent.get_natural_response(
                    f"Résume-moi cette fiche technique : {analysis['explanation']}", 
                    {"content": text_content}
                )

            # --- CAS : CONVERSATION SIMPLE ---
            elif analysis.get('type') == 'text':
                response_text = analysis['explanation']
            
            else:
                response_text = "Je n'ai pas compris (Erreur interne)."

            return jsonify({"response": response_text})

    except Exception as e:
        user_logger.error(f"Erreur Chat Loop: {e}")
        return jsonify({"error": "Désolé, une erreur technique est survenue."}), 500


# --- ROUTES VIDEO ---

@app.route("/upload_video")
def upload_page():
    return render_template("upload_video.html")

@app.route("/api/upload_video", methods=["POST"])
async def handle_video_upload():
    if 'video' not in request.files:
        return jsonify({"error": "Aucun fichier"}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            user_logger.info(f"📹 Vidéo reçue : {filepath}")
            # TODO: Déclencher l'analyse OpenCV ici plus tard
            return jsonify({
                "success": True, 
                "message": "Vidéo bien reçue ! L'analyse va commencer.", 
                "filename": filename
            })
        except Exception as e:
            user_logger.error(f"Erreur save: {e}")
            return jsonify({"error": "Erreur écriture disque"}), 500
            
    return jsonify({"error": "Format non supporté"}), 400

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)