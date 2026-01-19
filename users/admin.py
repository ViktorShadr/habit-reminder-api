from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from users.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User

    # чтобы в списке пользователей было видно группы (как текст)
    list_display = ("id", "email", "first_name", "last_name", "is_staff", "groups_list")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # чтобы в форме редактирования появилось поле Groups
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone_number", "city", "avatar")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_active", "is_staff", "is_superuser", "groups"),
            },
        ),
    )

    filter_horizontal = ("groups", "user_permissions")

    def groups_list(self, obj):
        return ", ".join(g.name for g in obj.groups.all())

    groups_list.short_description = "Groups"



