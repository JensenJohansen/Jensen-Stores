from rest_framework import permissions
from django.contrib.auth.models import Group


class IsShopOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.values('name').get(user=request.user.id)
        user_group = user_group['name']
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'shopowner':
            return True
        return False


class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.values('name').get(user=request.user.id)
        user_group = user_group['name']
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'cashier':
            return True
        return False


class IsShopKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.values('name').get(user=request.user.id)
        user_group = user_group['name']
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'storekeeper':
            return True
        return False