from django.conf import settings
from django.db import transaction
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


class UserRetrieveAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserUpdateAPIView(generics.UpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserDestroyAPIView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class TelegramConfirmAPIView(APIView):
    permission_classes = [AllowAny]  # мы защищаемся секретом, а не JWT

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
