# --- Actualizar repositorios y herramientas básicas ---
!apt-get update -y
!apt-get install -y ffmpeg

# --- Instalar Python packages ---
!pip install --upgrade pip
!pip install whisper gTTS flask pyngrok nest_asyncio

# --- Imports ---
import os
from flask import Flask, request, send_file, jsonify
from pyngrok import ngrok
import whisper
from gtts import gTTS

# --- Configurar ngrok ---
NGROK_AUTH_TOKEN = "TU_TOKEN_NGROK_AQUI"
if not ngrok.get_tunnels():  # Solo autenticamos si no hay túneles
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

# --- Inicializar modelos ---
# Whisper (STT)
whisper_model = whisper.load_model("small")

# --- Configurar Flask ---
app = Flask(__name__)

# --- Endpoint STT (voz a texto) ---
@app.route("/stt", methods=["POST"])
def stt_endpoint():
    if "file" not in request.files:
        return jsonify({"error": "Falta archivo de audio"}), 400

    audio_file = request.files["file"]
    audio_path = "temp_audio.wav"
    audio_file.save(audio_path)

    # Transcribir con Whisper
    result = whisper_model.transcribe(audio_path, language="es")
    return jsonify({"texto": result["text"]})

# --- Endpoint TTS (texto a voz) ---
@app.route("/tts", methods=["POST"])
def tts_endpoint():
    texto = None

    if request.is_json:
        data = request.get_json()
        texto = data.get("texto")
    else:
        texto = request.data.decode("utf-8")

    if not texto:
        return jsonify({"error": "Falta texto en el request"}), 400

    # Generar audio con gTTS
    tts_audio = gTTS(text=texto, lang="es")
    output_path = "voz.mp3"
    tts_audio.save(output_path)

    return send_file(output_path, mimetype="audio/mpeg")

# --- Exponer servidor con ngrok ---
port = 5000
public_url = ngrok.connect(port)
print("Servidor público:", public_url)

# --- Ejecutar Flask ---
app.run(port=port)