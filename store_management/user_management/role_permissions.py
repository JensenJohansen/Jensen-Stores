from django.contrib.auth.models import Group, Permission


ROLE_PERMISSION_MODELS = {
    "shopowner": {
        ("stock_management", "goodstype"): ("add", "change", "delete", "view"),
        ("stock_management", "categories"): ("add", "change", "delete", "view"),
        ("stock_management", "supplier"): ("add", "change", "delete", "view"),
        ("stock_management", "purchaseorder"): ("add", "change", "delete", "view"),
        ("stock_management", "store"): ("add", "change", "delete", "view"),
        ("user_management", "appuser"): ("add", "change", "delete", "view"),
        ("order_management", "orderstatus"): ("add", "change", "delete", "view"),
        ("order_management", "auditlog"): ("view",),
        ("stock_management", "goods"): ("add", "change", "delete", "view"),
        ("stock_management", "goodsupdate"): ("add", "change", "delete", "view"),
        ("stock_management", "leakage"): ("add", "change", "delete", "view"),
        ("stock_management", "salesreturn"): ("add", "change", "delete", "view"),
        ("stock_management", "stocktransfer"): ("add", "change", "delete", "view"),
        ("order_management", "goodsorder"): ("add", "change", "delete", "view"),
        ("order_management", "payment"): ("add", "change", "delete", "view"),
        ("order_management", "order"): ("add", "change", "delete", "view"),
    },
    "storekeeper": {
        ("stock_management", "store"): ("view",),
        ("order_management", "order"): ("view",),
        ("stock_management", "goods"): ("add", "change", "delete", "view"),
        ("stock_management", "goodsupdate"): ("add", "change", "delete", "view"),
        ("stock_management", "leakage"): ("add", "change", "delete", "view"),
        ("stock_management", "salesreturn"): ("add", "change", "delete", "view"),
        ("stock_management", "stocktransfer"): ("add", "change", "delete", "view"),
        ("order_management", "goodsorder"): ("add", "change", "delete", "view"),
    },
    "cashier": {
        ("order_management", "payment"): ("add", "change", "delete", "view"),
        ("order_management", "order"): ("view", "change"),
    },
    "salesperson": {
        ("stock_management", "store"): ("view",),
        ("stock_management", "goods"): ("view",),
        ("order_management", "order"): ("add", "change", "delete", "view"),
    },
}


def _get_permission_codenames_for_group(group_name):
    permission_map = ROLE_PERMISSION_MODELS.get(group_name.lower(), {})
    return {
        (app_label, model_name, f"{action}_{model_name}")
        for (app_label, model_name), actions in permission_map.items()
        for action in actions
    }


def sync_group_permissions(group):
    permission_specs = _get_permission_codenames_for_group(group.name)
    if not permission_specs:
        return group

    app_labels = {app_label for app_label, _, _ in permission_specs}
    model_names = {model_name for _, model_name, _ in permission_specs}
    codenames = {codename for _, _, codename in permission_specs}

    permissions = Permission.objects.filter(
        content_type__app_label__in=app_labels,
        content_type__model__in=model_names,
        codename__in=codenames,
    ).select_related("content_type")

    expected_pairs = {
        (app_label, model_name, codename)
        for app_label, model_name, codename in permission_specs
    }
    filtered_permissions = [
        permission
        for permission in permissions
        if (
            permission.content_type.app_label,
            permission.content_type.model,
            permission.codename,
        )
        in expected_pairs
    ]

    if filtered_permissions:
        group.permissions.add(*filtered_permissions)

    return group


def sync_user_group_permissions(user):
    if not getattr(user, "is_authenticated", False):
        return user

    for group in user.groups.all():
        sync_group_permissions(group)

    for cache_name in ("_perm_cache", "_group_perm_cache", "_user_perm_cache"):
        if hasattr(user, cache_name):
            delattr(user, cache_name)

    return user


def get_or_create_configured_group(group_name):
    group, _ = Group.objects.get_or_create(name=group_name.lower())
    return sync_group_permissions(group)
