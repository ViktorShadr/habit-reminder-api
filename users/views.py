from django.conf import settings
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from users.serializers import (TelegramConfirmSerializer, TelegramLinkCreateSerializer, UserCreateSerializer,
                               UserSerializer)


class UserCreateAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Регистрация пользователя",
        operation_description="Создает нового пользователя.",
        tags=["Users"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class UserRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Данные текущего пользователя",
        operation_description="Возвращает профиль текущего пользователя.",
        tags=["Users"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class UserUpdateAPIView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Обновление профиля",
        operation_description="Обновляет данные текущего пользователя.",
        tags=["Users"],
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Частичное обновление профиля",
        operation_description="Частично обновляет данные текущего пользователя.",
        tags=["Users"],
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        return self.request.user


class UserDestroyAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Удаление пользователя",
        operation_description="Деактивирует текущего пользователя.",
        tags=["Users"],
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class TelegramConfirmAPIView(APIView):
    permission_classes = [AllowAny]  # мы защищаемся секретом, а не JWT

    @swagger_auto_schema(
        operation_summary="Подтверждение привязки Telegram",
        operation_description="Подтверждает привязку Telegram по секрету бота и коду.",
        request_body=TelegramConfirmSerializer,
        manual_parameters=[
            openapi.Parameter(
                "X-BOT-SECRET",
                openapi.IN_HEADER,
                description="Секрет бота для подтверждения запроса.",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        responses={
            200: openapi.Response("Telegram успешно привязан."),
            403: openapi.Response("Forbidden."),
            400: openapi.Response("Ошибка валидации."),
        },
        tags=["Telegram"],
    )
    def post(self, request):
        secret = request.headers.get("X-BOT-SECRET")
        if not secret or secret != settings.TELEGRAM_BOT_SECRET:
            return Response({"detail": "Forbidden."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TelegramConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            result = serializer.save()

        return Response(result, status=status.HTTP_200_OK)


class TelegramLinkCreateAPIView(generics.CreateAPIView):
    serializer_class = TelegramLinkCreateSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Получить код привязки Telegram",
        operation_description="Генерирует код для привязки Telegram.",
        tags=["Telegram"],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
