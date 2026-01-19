from django.conf import settings
from django.db import models


class Habit(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='Пользователь')
    place = models.CharField(max_length=100, verbose_name='Место')
    time = models.TimeField(verbose_name='Время выполнения привычки')
    action = models.CharField(max_length=100, verbose_name='Действие')
    is_pleasant = models.BooleanField(default=False, verbose_name='Позитивная привычка')
    related_habit = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='linked_habit', verbose_name='Связанная привычка')
    frequency = models.PositiveSmallIntegerField(default=1, verbose_name='Периодичность выполнения привычки')
    reward = models.CharField(max_length=100, null=True, blank=True, verbose_name='Награда')
    duration = models.PositiveSmallIntegerField(default=60, verbose_name='Длительность')
    is_public = models.BooleanField(default=False, verbose_name='Публичная привычка')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.action}"

    class Meta:
        verbose_name = 'Привычка'
        verbose_name_plural = 'Привычки'
