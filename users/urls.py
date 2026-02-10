from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.apps import UsersConfig
from users.views import (TelegramConfirmAPIView, TelegramLinkCreateAPIView, UserCreateAPIView, UserDestroyAPIView,
                         UserRetrieveAPIView, UserUpdateAPIView)

app_name = UsersConfig.name

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", UserCreateAPIView.as_view(), name="user_register"),
    path("detail/me/", UserRetrieveAPIView.as_view(), name="user_detail"),
    path("update/me/", UserUpdateAPIView.as_view(), name="user_update"),
    path("delete/me/", UserDestroyAPIView.as_view(), name="user_delete"),
    path("telegram/link/", TelegramLinkCreateAPIView.as_view(), name="telegram_link"),
    path("telegram/confirm/", TelegramConfirmAPIView.as_view(), name="telegram_confirm"),
]
