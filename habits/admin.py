from django.contrib import admin

from habits.models import Habit


@admin.register(Habit)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('user', 'place', 'time', 'action', 'is_pleasant', 'frequency', 'reward', 'duration', 'is_public', 'created_at', 'updated_at')

