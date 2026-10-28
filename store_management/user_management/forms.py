from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import AppUser


class CustomUserCreationForm(UserCreationForm):

    class Meta:
        model = AppUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "user_company",
            "groups",
            "is_staff",
            "is_active",
        )


class CustomUserChangeForm(UserChangeForm):

    class Meta:
        model = AppUser
        fields = (
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "user_company",
            "groups",
            "is_staff",
            "is_active",
        )
