from rest_framework import permissions
from .role_permissions import sync_user_group_permissions


def _get_view_model(view):
    queryset = getattr(view, "queryset", None)
    if queryset is not None and hasattr(queryset, "model"):
        return queryset.model

    serializer_class = getattr(view, "serializer_class", None)
    meta = getattr(serializer_class, "Meta", None)
    if meta is not None:
        return getattr(meta, "model", None)

    return None


def _get_required_action(method):
    if method == "POST":
        return "add"
    if method in ("PUT", "PATCH"):
        return "change"
    if method == "DELETE":
        return "delete"
    if method in permissions.SAFE_METHODS:
        return "view"

    return ""


def _get_explicit_view_permissions(view, method):
    permission_map = getattr(view, "required_permissions_by_method", None)
    if isinstance(permission_map, dict):
        return permission_map.get(method) or permission_map.get("*") or []

    permissions = getattr(view, "required_permissions", None)
    if permissions is None:
        return []

    return permissions if isinstance(permissions, (list, tuple, set)) else [permissions]


def _user_has_model_permission(user, view, method):
    if not getattr(user, "is_authenticated", False):
        return False

    sync_user_group_permissions(user)
    explicit_permissions = _get_explicit_view_permissions(view, method)
    if explicit_permissions:
        return all(user.has_perm(permission_name) for permission_name in explicit_permissions)

    action = _get_required_action(method)
    model = _get_view_model(view)
    if not action or model is None:
        return False

    permission_codename = f"{model._meta.app_label}.{action}_{model._meta.model_name}"
    return user.has_perm(permission_codename)


class IsShopOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        return _user_has_model_permission(
            request.user,
            view,
            request.method,
        )


class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        return _user_has_model_permission(
            request.user,
            view,
            request.method,
        )


class IsShopKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        return _user_has_model_permission(
            request.user,
            view,
            request.method,
        )
    

class IsSalesPerson(permissions.BasePermission):
    def has_permission(self, request, view):
        return _user_has_model_permission(
            request.user,
            view,
            request.method,
        )
