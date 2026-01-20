from rest_framework import viewsets, generics
from rest_framework.permissions import IsAuthenticated

from habits.models import Habit
from habits.serializers import HabitSerializer, HabitPublicSerializer


class HabitViewSet(viewsets.ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]

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
