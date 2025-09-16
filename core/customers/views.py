import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import User, Language, TypeChat, Chat
from .adapters import adapt_request


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
                    pass  

            return JsonResponse({
                "id_user": user.id_user,
                "phone_number": user.phone_number,
                "name": user.name,
                "language": user.language.id
            }, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Method not allowed"}, status=405)

@csrf_exempt
def get_user_by_chat(request, chat_id):
    if request.method == "GET":
        try:
            chat = Chat.objects.select_related("user", "user__language", "typechat").get(chat_id=chat_id)
            user = chat.user
            return JsonResponse({
                "id_user": user.id_user,
                "name": user.name,
                "phone_number": str(user.phone_number),
                "language": user.language.language,
                "chat_id": chat.chat_id,
                "chat_type": chat.typechat.name,
            }, status=200)
        except Chat.DoesNotExist:
            return JsonResponse({"error": "Chat ID not found"}, status=404)
    else:
        return JsonResponse({"error": "Only GET allowed"}, status=405)

