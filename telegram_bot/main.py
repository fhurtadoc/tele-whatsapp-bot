from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import json

app = FastAPI()

DJANGO_API = "http://django_app:8000/api/users/"  # 👈 endpoint en tu Django

@app.post("/telegram_bot")
async def telegram_webhook(request: Request):
    try:
        if request.method == "POST":
        data = json.loads(request.body.decode("utf-8"))
        print("📩 Nuevo mensaje de Telegram:", data)
        return JsonResponse({"status": "ok"})
    return JsonResponse({"status": "not allowed"}, status=405)
    except Exception as e:
        print("❌ Error:", str(e))
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=400)


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    run_server()
