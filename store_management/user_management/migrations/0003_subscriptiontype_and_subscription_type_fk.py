# Generated manually to make subscription types admin-managed.

from django.db import migrations, models
import django.db.models.deletion


DEFAULT_TYPES = {
    "STANDARD": {"name": "Standard", "is_default": True},
    "PROFESSIONAL": {"name": "Professional", "is_default": False},
    "ULTIMATE": {"name": "Ultimate", "is_default": False},
}


def normalize_code(value):
    return (value or "").strip().upper()


def default_name_for(code):
    return DEFAULT_TYPES.get(code, {}).get("name") or code.replace("_", " ").title()


def forwards(apps, schema_editor):
    Subscription = apps.get_model("user_management", "Subscription")
    SubscriptionType = apps.get_model("user_management", "SubscriptionType")

    created_types = {}
    for code, meta in DEFAULT_TYPES.items():
        created_types[code], _ = SubscriptionType.objects.get_or_create(
            code=code,
            defaults={
                "name": meta["name"],
                "is_active": True,
                "is_default": meta["is_default"],
            },
        )

    for subscription in Subscription.objects.all():
        code = normalize_code(subscription.type)
        if code not in created_types:
            created_types[code], _ = SubscriptionType.objects.get_or_create(
                code=code,
                defaults={
                    "name": default_name_for(code),
                    "is_active": True,
                    "is_default": False,
                },
            )
        subscription.subscription_type = created_types[code]
        subscription.save(update_fields=["subscription_type"])


def backwards(apps, schema_editor):
    Subscription = apps.get_model("user_management", "Subscription")

    for subscription in Subscription.objects.select_related("subscription_type"):
        subscription.type = subscription.subscription_type.code
        subscription.save(update_fields=["type"])


class Migration(migrations.Migration):

    dependencies = [
        ("user_management", "0002_alter_appuser_groups"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=50, unique=True, verbose_name="subscription code")),
                ("name", models.CharField(max_length=100, unique=True, verbose_name="subscription name")),
                ("is_active", models.BooleanField(default=True, verbose_name="is active")),
                ("is_default", models.BooleanField(default=False, verbose_name="default plan")),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddField(
            model_name="subscription",
            name="subscription_type",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subscriptions",
                to="user_management.subscriptiontype",
                verbose_name="subscription type",
            ),
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="subscription",
            name="subscription_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="subscriptions",
                to="user_management.subscriptiontype",
                verbose_name="subscription type",
            ),
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="type",
        ),
        migrations.RenameField(
            model_name="subscription",
            old_name="subscription_type",
            new_name="type",
        ),
    ]
