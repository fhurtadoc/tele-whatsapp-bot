def adapt_request(data, keys_to_extract=None):
    """
    Convierte un JSON externo al formato interno de User/Chat.
    Se asigna un phone_number falso si no viene.
    """
    if keys_to_extract is None:
        keys_to_extract = ["name", "language", "typechat", "chat_id", "phone_number"]

    result = {}
    message = data.get("message", {})
    user_info = message.get("from", {})
    chat_info = message.get("chat", {})

    first_name = user_info.get("first_name", "")
    last_name = user_info.get("last_name", "")
    chat_id = chat_info.get("id")

    lang_map = {"es": 2, "en": 1}
    platform_map = {"telegram": 1, "whatsapp": 2}

    if "name" in keys_to_extract:
        result["name"] = f"{first_name} {last_name}".strip()

    if "language" in keys_to_extract:
        language_code = user_info.get("language_code")
        result["language_id"] = lang_map.get(language_code, 2)  # default a 'es'

    if "typechat" in keys_to_extract:
        result["typechat_id"] = platform_map.get("telegram", 1)  # default Telegram

    if "chat_id" in keys_to_extract:
        result["chat_id"] = chat_id

    if "phone_number" in keys_to_extract:
        # Temporal: usamos chat_id como phone_number falso
        result["phone_number"] = chat_id or 1000000000

    return result
