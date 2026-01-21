from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics, viewsets
from rest_framework.permissions import IsAuthenticated

from habits.models import Habit
from habits.serializers import HabitPublicSerializer, HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Список привычек пользователя",
        operation_description="Возвращает список привычек текущего пользователя.",
        tags=["Habits"],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Создать привычку",
        operation_description="Создает новую привычку для текущего пользователя.",
        tags=["Habits"],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Получить привычку",
        operation_description="Возвращает данные привычки по ID.",
        tags=["Habits"],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Обновить привычку",
        operation_description="Полностью обновляет привычку по ID.",
        tags=["Habits"],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Частично обновить привычку",
        operation_description="Частично обновляет привычку по ID.",
        tags=["Habits"],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Удалить привычку",
        operation_description="Удаляет привычку по ID.",
        tags=["Habits"],
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Habit.objects.none()

        if not self.request.user.is_authenticated:
            return Habit.objects.none()

        return Habit.objects.filter(user=self.request.user)


class PublicListAPIView(generics.ListAPIView):
    queryset = Habit.objects.filter(is_public=True)
    serializer_class = HabitPublicSerializer
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Публичные привычки",
        operation_description="Возвращает список публичных привычек.",
        tags=["Habits"],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
