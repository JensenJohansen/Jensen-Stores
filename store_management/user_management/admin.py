from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import AppUser,Company, Subscription, Customer


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = AppUser
    list_display = ("username", "first_name", "last_name","phone_number",)
    list_filter = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "groups", "user_permissions")}),
    )
    
    """
    In fields below, i had to replace email with username, as email never defined in the model before 
    but also username was selected to be the login credential.
    """
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username", "password1", "password2", "is_staff",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    search_fields = ("username",)
    ordering = ("username",)


admin.site.register(AppUser, CustomUserAdmin)
admin.site.register(Company)
admin.site.register(Subscription)
admin.site.register(Customer)