from django.urls import path
from .views import create_user, get_user_by_chat

urlpatterns = [
    path("new/", create_user, name="create_user_api"),
    path("search/<int:chat_id>/", get_user_by_chat, name="get_user_ api"),
]
