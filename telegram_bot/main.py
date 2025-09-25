from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import uvicorn
import os
import json
from minio import Minio
from minio.error import S3Error
from datetime import datetime
import io


MINIO_CLIENT = Minio(
    os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
    secure=os.getenv("MINIO_SECURE", "False").lower() == "true"
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN no está definido en las variables de entorno")


COLAB_URL=os.getenv("URL_OF_COLAB")
TELEGRAM_API_URL = "https://api.telegram.org"
DJANGO_API = "http://core:8000/apiCustomers/"

app = FastAPI()
user_states = {}  # estado temporal por chat_id

# 📤 Enviar mensaje simple a Telegram
def send_telegram_message(chat_id: int, text: str):
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    print("📤 Respuesta Telegram (mensaje):", response.status_code, response.text)


def send_telegram_voice(chat_id: int, audio_bytes: bytes, filename: str = "audio.ogg"):
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendVoice"
    files = {"voice": (filename, io.BytesIO(audio_bytes))}
    data = {"chat_id": chat_id}
    response = requests.post(url, data=data, files=files)
    print("📤 Respuesta Telegram (voz):", response.status_code, response.text)




# 📤 Enviar menú con opciones
def send_telegram_menu(chat_id: int):
    url = f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "👉 ¿Qué deseas hacer hoy?",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🎙 Texto → Voz", "callback_data": "text_to_voice"},
                    {"text": "🗣 Voz → Texto", "callback_data": "voice_to_text"}
                ]
            ]
        }
    }
    response = requests.post(url, json=payload)
    print("📤 Respuesta Telegram (menu):", response.status_code, response.text)



# 🔎 Validar usuario en Django
def validate_user(chat_id: int, data: dict) -> bool:
    search_response = requests.get(f"{DJANGO_API}search/{chat_id}")

    if search_response.status_code == 200:
        print(f"✅ Usuario ya creado: {search_response.json()}")
        send_telegram_message(chat_id, "👋 Hola, ya estás registrado.")
        return True

    elif search_response.status_code == 404:
        create_response = requests.post(f"{DJANGO_API}new/", json=data)
        if create_response.status_code == 201:
            print(f"🆕 Usuario creado con chat_id: {chat_id}")
            send_telegram_message(chat_id, "✅ Te acabo de registrar.")
            return False
        else:
            print("❌ Error al crear usuario:", create_response.text)
            raise Exception("Error creando usuario")

    else:
        print("❌ Error al consultar Django:", search_response.text)
        raise Exception("Error consultando usuario")




def handle_message(chat_id: int, message: dict):
    state = user_states.get(chat_id)

    # --- Caso 1: Texto → Voz ---
    if state == "waiting_text" and "text" in message:
        text = message["text"].strip()

        if len(text) > 100:
            send_telegram_message(chat_id, "⚠️ El texto no puede superar los 100 caracteres.")
            user_states[chat_id] = None
            return

        send_telegram_message(chat_id, "Procesando tu texto → voz 🎙")

        try:
            url = f"{COLAB_URL}/tts"
            payload = {"texto": text}
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                audio_bytes = response.content

                # 🔹 Guardar en MinIO
                file_name = generate_filename(chat_id, ".mp3")
                upload_to_minio("colab", file_name, audio_bytes, "audio/mpeg")

                send_telegram_message(chat_id, "✅ Conversión de texto a voz completada.")
                # aquí podrías enviar el audio como archivo a Telegram
                send_telegram_voice(chat_id, audio_bytes, file_name)

            else:
                send_telegram_message(chat_id, f"❌ Error en Colab: {response.text}")
        except requests.RequestException as e:
            send_telegram_message(chat_id, f"❌ No pude conectar con Colab: {str(e)}")

        user_states[chat_id] = None
        return

    # --- Caso 2: Voz → Texto ---
    if state == "waiting_audio":
        if "voice" in message or "audio" in message:
            send_telegram_message(chat_id, "Procesando tu audio → texto 🗣")

            file_id = message["voice"]["file_id"] if "voice" in message else message["audio"]["file_id"]

            # 🔹 Descargar el archivo de Telegram
            file_info = requests.get(f"{TELEGRAM_API_URL}/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = file_info["result"]["file_path"]
            file_url = f"{TELEGRAM_API_URL}/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

            audio_bytes = requests.get(file_url).content

            # 🔹 Guardar en MinIO
            file_name = generate_filename(chat_id, ".ogg")
            upload_to_minio("telegram", file_name, audio_bytes, "audio/ogg")

            try:
                url = f"{COLAB_URL}/stt"
                payload = {"file_name": file_name, "bucket": "telegram"}
                response = requests.post(url, json=payload, timeout=60)

                if response.status_code == 200:
                    text_result = response.json().get("texto", "")
                    send_telegram_message(chat_id, f"✅ Transcripción: {text_result}")
                else:
                    send_telegram_message(chat_id, f"❌ Error en Colab: {response.text}")
            except requests.RequestException as e:
                send_telegram_message(chat_id, f"❌ No pude conectar con Colab: {str(e)}")

        else:
            send_telegram_message(chat_id, "⚠️ Por favor envía un archivo de audio válido (no video, imagen o documento).")

        user_states[chat_id] = None
        return

    send_telegram_menu(chat_id)



def upload_to_minio(bucket: str, file_name: str, data: bytes, content_type="application/octet-stream") -> str:
    try:
        MINIO_CLIENT.put_object(
            bucket,
            file_name,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type
        )
        print(f"✅ Subido a MinIO: {bucket}/{file_name}")
        return file_name
    except S3Error as e:
        print(f"❌ Error al subir a MinIO: {e}")
        return None


def generate_filename(chat_id: int, extension: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{chat_id}_{timestamp}{extension}"

# 🎯 Procesar botones del teclado
def handle_callback(chat_id: int, option: str):
    if option == "text_to_voice":
        user_states[chat_id] = "waiting_text"
        send_telegram_message(chat_id, "✍️ Envía el texto que quieres convertir a voz.")

    elif option == "voice_to_text":
        user_states[chat_id] = "waiting_audio"
        send_telegram_message(chat_id, "🎤 Envía el archivo de audio para convertirlo a texto.")


# 📩 Webhook principal
@app.post("/telegram_bot")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        # Obtener chat_id
        chat_id = None
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
        elif "callback_query" in data:
            chat_id = data["callback_query"]["message"]["chat"]["id"]

        if not chat_id:
            return JSONResponse({"status": "error", "detail": "chat_id missing"}, status_code=400)

        # --- 1. Validar usuario ---
        validate_user(chat_id, data)

        # --- 2. Manejar evento ---
        if "message" in data:
            handle_message(chat_id, data["message"])
        elif "callback_query" in data:
            handle_callback(chat_id, data["callback_query"]["data"])

        return JSONResponse({"status": "ok"})

    except Exception as e:
        print("❌ Error:", str(e))
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    run_server()
