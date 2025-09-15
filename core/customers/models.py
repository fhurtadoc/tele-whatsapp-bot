from django.db import models

# ------------------ entity Type Chat ----------------------- 

class TypeChat(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    name = models.TextField()
 
    class Meta:
        db_table = "type_chats"
 
    def __str__(self):
        return self.name


# ------------------ entity Language ----------------------- 

class Language(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    language = models.TextField()
 
    class Meta:
        db_table = "languages"
 
    def __str__(self):
        return self.language

# ------------------ entity User -----------------------         


class User(models.Model):
    id_user = models.AutoField(primary_key=True, unique=True)
    phone_number = models.DecimalField(max_digits=15, decimal_places=0)
    name = models.TextField()
    language = models.ForeignKey(
        Language,
        on_delete=models.DO_NOTHING,
        db_column="language",
        related_name="users"
    )
 
    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["language"], name="USERS_index_0")
        ]
 
    def __str__(self):
        return f"{self.name} ({self.phone_number})"


# ------------------ entity Chat -----------------------         

class Chat(models.Model):
    id = models.AutoField(primary_key=True, unique=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chats"
    )
    typechat = models.ForeignKey(
        TypeChat,
        on_delete=models.DO_NOTHING,
        related_name="chats"
    )
    chat_id = models.CharField(max_length=100)  # Telegram/WhatsApp ID
    created_at = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        db_table = "chats"
        unique_together = ("chat_id", "typechat")  # evita duplicados
        indexes = [
            models.Index(fields=["typechat"], name="chat_typechat_idx")  # índice por typechat
        ]
 
    def __str__(self):
        return f"{self.typechat.name} - {self.chat_id} ({self.user.name})"
