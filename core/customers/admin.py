from django.contrib import admin

from django.contrib import admin
from .models import User, Language, TypeChat, Chat

# ------------------ Admin Language ------------------
@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("id", "language")
    search_fields = ("language",)

# ------------------ Admin TypeChat ------------------
@admin.register(TypeChat)
class TypeChatAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

# ------------------ Admin User ------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id_user", "name", "phone_number", "language")
    search_fields = ("name", "phone_number")
    list_filter = ("language",)

# ------------------ Admin Chat ------------------
@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "typechat", "chat_id", "created_at")
    search_fields = ("chat_id", "user__name", "typechat__name")
    list_filter = ("typechat", "created_at")

