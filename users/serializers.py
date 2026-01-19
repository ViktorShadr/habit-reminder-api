from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.fields import CharField

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
