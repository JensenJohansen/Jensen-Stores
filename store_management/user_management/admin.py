from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import AppUser,Company, Subscription, Customer, SubscriptionType


class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = AppUser
    list_display = ("username", "first_name", "last_name", "phone_number", "user_company", "is_staff", "is_active")
    list_filter = ("username", "user_company", "is_staff", "is_active")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number", "email", "user_company")}),
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
                "username", "first_name", "last_name", "phone_number", "email",
                "user_company", "password1", "password2", "is_staff",
                "is_active", "groups", "user_permissions"
            )}
        ),
    )
    search_fields = ("username", "first_name", "last_name", "phone_number", "email", "user_company__company_name")
    ordering = ("username",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("company_name", "company_location", "company_tin", "date_added")
    search_fields = ("company_name", "company_location", "company_tin")
    ordering = ("company_name",)


admin.site.register(AppUser, CustomUserAdmin)


@admin.register(SubscriptionType)
class SubscriptionTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "duration_days", "is_active", "is_default")
    list_filter = ("is_active", "is_default")
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("company", "type", "status", "date_activated", "expire_date")
    list_filter = ("status", "type")
    search_fields = ("company__company_name", "type__code", "type__name")
    autocomplete_fields = ("company", "type")


admin.site.register(Customer)
