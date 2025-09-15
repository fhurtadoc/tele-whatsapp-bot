import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Language, TypeChat, Chat

# -------- Adaptador ----------
def adapt_request(data):
    """Convierte el JSON externo al formato interno de User/Chat"""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    phone_number = data.get("phone")

    # nombre completo
    name = f"{first_name}-{last_name}".strip()

    # mapear language
    lang_map = {"es": 1, "en": 2}
    language_id = lang_map.get(data.get("language"))

    # mapear plataforma
    platform_map = {"telegram": 1, "whatsapp": 2}
    typechat_id = platform_map.get(data.get("platform"))

    return {
        "phone_number": phone_number,
        "name": name,
        "language_id": language_id,
        "typechat_id": typechat_id,
    }

# -------- Vista API ----------
@csrf_exempt
def create_user(request):
    if request.method == "POST":
        try:
            raw_data = json.loads(request.body)
            adapted = adapt_request(raw_data)

            # validar datos mínimos
            if not (adapted["phone_number"] and adapted["name"] and adapted["language_id"]):
                return JsonResponse({"error": "Missing fields"}, status=400)

            # buscar lenguaje
            try:
                language = Language.objects.get(id=adapted["language_id"])
            except Language.DoesNotExist:
                return JsonResponse({"error": "Language not found"}, status=404)

            # crear usuario
            user = User.objects.create(
                phone_number=adapted["phone_number"],
                name=adapted["name"],
                language=language
            )

            # crear chat asociado
            if adapted["typechat_id"]:
                try:
                    typechat = TypeChat.objects.get(id=adapted["typechat_id"])
                    Chat.objects.create(
                        user=user,
                        typechat=typechat,
                        chat_id=adapted["phone_number"]  # o el ID externo de la plataforma
                    )
                except TypeChat.DoesNotExist:
                    pass  # si no existe, ignoramos

            return JsonResponse({
                "id_user": user.id_user,
                "phone_number": user.phone_number,
                "name": user.name,
                "language": user.language.id
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)
