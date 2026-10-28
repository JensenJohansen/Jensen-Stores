from django.db import migrations, models


PLAN_DEFAULTS = {
    "TRIAL": {"name": "Trial", "duration_days": 30, "is_default": True, "is_active": True},
    "STANDARD": {"name": "Standard", "duration_days": 30, "is_default": False, "is_active": True},
    "PROFESSIONAL": {"name": "Professional", "duration_days": 30, "is_default": False, "is_active": True},
    "ULTIMATE": {"name": "Ultimate", "duration_days": 30, "is_default": False, "is_active": True},
}


def seed_subscription_types(apps, schema_editor):
    SubscriptionType = apps.get_model("user_management", "SubscriptionType")

    for code, meta in PLAN_DEFAULTS.items():
        subscription_type, created = SubscriptionType.objects.get_or_create(
            code=code,
            defaults=meta,
        )
        if not created:
            subscription_type.name = subscription_type.name or meta["name"]
            subscription_type.duration_days = subscription_type.duration_days or meta["duration_days"]
            subscription_type.is_active = meta["is_active"]
            subscription_type.is_default = meta["is_default"]
            subscription_type.save(
                update_fields=["name", "duration_days", "is_active", "is_default"]
            )

    SubscriptionType.objects.exclude(code="TRIAL").filter(is_default=True).update(is_default=False)


def unseed_subscription_types(apps, schema_editor):
    SubscriptionType = apps.get_model("user_management", "SubscriptionType")
    trial = SubscriptionType.objects.filter(code="TRIAL").first()
    if trial is not None:
        trial.delete()
    SubscriptionType.objects.filter(code="STANDARD").update(is_default=True)


class Migration(migrations.Migration):
    dependencies = [
        ("user_management", "0003_subscriptiontype_and_subscription_type_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptiontype",
            name="duration_days",
            field=models.PositiveIntegerField(default=30, verbose_name="duration days"),
        ),
        migrations.RunPython(seed_subscription_types, unseed_subscription_types),
    ]
