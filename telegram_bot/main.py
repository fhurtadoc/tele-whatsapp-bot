from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import requests

app = FastAPI()

DJANGO_API = "http://core:8000/apiCustomers/"  # endpoint in Django


@app.post("/telegram_bot")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        message = data.get("message", {})

        # 1 Getting  chat_id and message_id
        chat_id = message.get("chat", {}).get("id")
        message_id = message.get("message_id")
        print(chat_id)
        if not chat_id:
            return JSONResponse({"status": "error", "detail": "chat_id missing"}, status_code=400)
       
        # 3 Consultar si el usuario existe en Django
        search_response = requests.get(f"{DJANGO_API}search/", params={"chat_id": chat_id})

        if search_response.status_code == 200:
            print(f"User was ready created: {search_response.json()}")
        elif search_response.status_code == 404:
            # 4 Usuario no existe → crear
            create_response = requests.post(f"{DJANGO_API}new/", json=data)
            if create_response.status_code == 201:
                print(f" New User and the chat_id is {chat_id}")
            else:
                print(" Error when it try to created:", create_response.text)
        else:
            print(" Error getting in Django:", search_response.text)

        return JSONResponse({"status": "ok"}, status_code=200)

    except Exception as e:
        print(" Error:", str(e))
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    run_server()
