from django.apps import apps


def create_audit_log(*, actor=None, company=None, action, entity_type, entity_id, description=None, payload=None):
    AuditLog = apps.get_model("order_management", "AuditLog")
    AuditLog.objects.create(
        actor=actor,
        company=company,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        description=description,
        payload=payload,
    )
