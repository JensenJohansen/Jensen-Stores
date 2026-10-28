from django.db import migrations, models


def copy_order_status_to_text(apps, schema_editor):
    Order = apps.get_model("order_management", "Order")

    for order in Order.objects.select_related("authorization_status").all():
        status = "pending"
        if order.authorization_status_id:
            related_status = getattr(order, "authorization_status", None)
            if related_status and getattr(related_status, "status", None):
                status = related_status.status
        order.authorization_status_value = status
        order.save(update_fields=["authorization_status_value"])


class Migration(migrations.Migration):

    dependencies = [
        ("order_management", "0005_order_customer_and_customer_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="authorization_status_value",
            field=models.CharField(
                blank=True,
                default="pending",
                max_length=20,
                verbose_name="Authorized status",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(copy_order_status_to_text, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="order",
            name="authorization_status",
        ),
        migrations.DeleteModel(
            name="OrderStatus",
        ),
        migrations.RenameField(
            model_name="order",
            old_name="authorization_status_value",
            new_name="authorization_status",
        ),
        migrations.AlterField(
            model_name="order",
            name="authorization_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("approved", "Approved"),
                    ("partially_paid", "Partially paid"),
                    ("paid", "Paid"),
                    ("rejected", "Rejected"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
                verbose_name="Authorized status",
            ),
        ),
    ]
