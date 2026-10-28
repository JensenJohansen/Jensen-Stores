from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("user_management", "0004_subscriptiontype_trial_default_and_duration"),
        ("order_management", "0004_alter_orderstatus_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="customer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="orders",
                to="user_management.customer",
                verbose_name="registered customer",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="customer_name",
            field=models.CharField(
                blank=True,
                max_length=150,
                null=True,
                verbose_name="Customer name",
            ),
        ),
    ]
