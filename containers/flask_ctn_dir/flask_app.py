import os
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import asyncio

# Import depuis ton package client_mcp
from client_mcp import MCPHTTPClient, MistralAgent, MCP_SERVER_URL, MISTRAL_MODEL, json_logger, user_logger

app = Flask(__name__)

# --- CONFIGURATION ---
# Dossier où seront stockées les vidéos uploadées
# On utilise /app/badia_files car c'est probablement un volume monté (persistant)
UPLOAD_FOLDER = '/app/badia_files/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Création automatique du dossier s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialisation de l'agent
agent = MistralAgent(model=MISTRAL_MODEL)


# --- ROUTES PRINCIPALES ---

@app.route("/")
def index():
    """Page d'accueil avec le Chatbot."""
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
async def chat():
    """Route API appelée par le JavaScript du Chatbot."""
    data = request.json
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "Message vide"}), 400

    try:
        # 1. Connexion au serveur MCP
        async with MCPHTTPClient(MCP_SERVER_URL) as mcp_client:
            
            # 2. Récupération des outils et ressources
            tools = await mcp_client.list_tools()
            resources = await mcp_client.list_resources()
            
            # 3. Configuration de l'agent
            agent.set_tools(tools)
            agent.set_resources(resources)
            
            # 4. Analyse Mistral de la requête utilisateur
            analysis = await agent.analyze_query(user_message)
            
            response_text = ""

            # CAS A : L'agent décide d'utiliser un outil (ex: preparer_analyse_video)
            if analysis.get('type') == 'tool':
                tool_result = await mcp_client.call_tool(
                    analysis['tool'],
                    analysis.get('arguments', {})
                )
                
                # Extraction du résultat structuré
                structured = tool_result.get('structuredContent', {}).get('result', tool_result)
                
                # --- LOGIQUE DE REDIRECTION ---
                # Si l'outil renvoie l'action spécifique, on ordonne au front-end de changer de page
                if structured.get("action") == "redirect_to_upload":
                    return jsonify({
                        "response": structured.get("message"),
                        "redirect": "/upload_video"  # URL vers la route définie plus bas
                    })
                # ------------------------------

                # Sinon, on reformule simplement la réponse de l'outil
                response_text = await agent.get_natural_response(user_message, structured)

            # CAS B : L'agent a trouvé une ressource (ex: documentation texte)
            elif analysis.get('type') == 'resource':
                res_content = await mcp_client.read_resource(analysis['resource_uri'])
                response_text = agent.format_result(res_content)

            # CAS C : Simple discussion textuelle
            elif analysis.get('type') == 'text':
                response_text = analysis['explanation']
            
            else:
                response_text = "Je n'ai pas compris la réponse de l'agent."

            return jsonify({"response": response_text})

    except Exception as e:
        user_logger.error(f"Erreur Chat: {e}")
        return jsonify({"error": str(e)}), 500


# --- ROUTES VIDEO / UPLOAD ---

@app.route("/upload_video")
def upload_page():
    """Affiche la page HTML pour l'upload de vidéo."""
    return render_template("upload_video.html")

@app.route("/api/upload_video", methods=["POST"])
async def handle_video_upload():
    """Reçoit le fichier vidéo envoyé par le formulaire JS."""
    if 'video' not in request.files:
        return jsonify({"error": "Aucun fichier vidéo reçu"}), 400
    
    file = request.files['video']
    
    if file.filename == '':
        return jsonify({"error": "Nom de fichier vide"}), 400
        
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(filepath)
            user_logger.info(f"📹 Vidéo sauvegardée : {filepath}")
            
            # TODO: Ici, tu pourras appeler ta fonction de Computer Vision
            # await analyze_badminton(filepath)
            
            return jsonify({
                "success": True, 
                "message": "Vidéo reçue et sauvegardée.", 
                "filename": filename
            })
        except Exception as e:
            user_logger.error(f"Erreur sauvegarde vidéo: {e}")
            return jsonify({"error": "Erreur lors de la sauvegarde sur le serveur"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)