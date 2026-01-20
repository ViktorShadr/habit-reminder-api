import secrets
import string
from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.fields import CharField

from users.models import TelegramLink
from users.models import User


class UserCreateSerializer(serializers.ModelSerializer):
    password = CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ["email", "password", "phone_number", "city", "avatar"]

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "phone_number", "city", "avatar"]


class TelegramLinkCreateSerializer(serializers.Serializer):
    # Это поля ОТВЕТА (read-only). В запросе тело может быть пустым.
    code = serializers.CharField(read_only=True)
    expires_at = serializers.DateTimeField(read_only=True)
    start_command = serializers.CharField(read_only=True)

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user

        # 1) “Гасим” прошлые неиспользованные коды, чтобы был один активный.
        TelegramLink.objects.filter(
            user=user,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        ).update(expires_at=timezone.now())

        # 2) Генерим код (без спецсимволов, чтобы удобно вставлять в /start)
        alphabet = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(alphabet) for _ in range(10))

        # 3) Истекает через 15 минут
        expires_at = timezone.now() + timedelta(minutes=15)

        link = TelegramLink.objects.create(
            user=user,
            code=code,
            expires_at=expires_at,
        )

        # 4) Возвращаем “payload” для ответа
        return {
            "code": link.code,
            "expires_at": link.expires_at,
            "start_command": f"/start {link.code}",
        }


class TelegramConfirmSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)
    chat_id = serializers.IntegerField(min_value=1)

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        return value

    def save(self, **kwargs):
        code = self.validated_data["code"]
        chat_id = self.validated_data["chat_id"]

        # select_for_update требует транзакцию — сделаем её во view
        link = (
            TelegramLink.objects.select_for_update()
            .select_related("user")
            .filter(code=code)
            .first()
        )

        if not link:
            raise serializers.ValidationError({"code": "Код привязки не найден."})

        if link.is_used:
            raise serializers.ValidationError({"code": "Этот код уже был использован. Запросите новый код."})

        if link.is_expired:
            raise serializers.ValidationError({"code": "Срок действия кода истёк. Запросите новый код."})

        user = link.user
        user.telegram_chat_id = chat_id
        user.save(update_fields=["telegram_id"])

        link.used_at = timezone.now()
        link.save(update_fields=["used_at"])

        return {"detail": "Telegram успешно привязан."}
