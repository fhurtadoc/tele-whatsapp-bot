from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import uvicorn
import os
import json

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

        # Validación: longitud máxima
        if len(text) > 100:
            send_telegram_message(chat_id, "⚠️ El texto no puede superar los 100 caracteres.")
            user_states[chat_id] = None
            return

        # Notificación al usuario
        send_telegram_message(chat_id, "Procesando tu texto → voz 🎙")

        # Llamada a Colab
        try:
            url = f"{COLAB_URL}/tts"
            payload = {"texto": text}
            response = requests.post(url, json=payload, timeout=30)

            if response.status_code == 200:
                # Aquí podrías devolver un archivo de audio al usuario
                send_telegram_message(chat_id, "✅ Conversión de texto a voz completada.")
                send_telegram_message(chat_id, response)
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

            # Obtener file_id del audio
            file_id = message["voice"]["file_id"] if "voice" in message else message["audio"]["file_id"]

            try:
                url = f"{COLAB_URL}/stt"
                payload = {"file_id": file_id}
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

    # --- Caso 3: Sin estado definido ---
    send_telegram_menu(chat_id)



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
