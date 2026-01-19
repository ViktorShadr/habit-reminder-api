from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from habits.models import Habit
from habits.serializers import HabitSerializer


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Habit.objects.filter(user=self.request.user)
