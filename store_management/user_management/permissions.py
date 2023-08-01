from rest_framework import permissions
from django.contrib.auth.models import Group


class IsShopOwner(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.get(user=request.user.id)
        user_group = user_group.name.lower()
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'shop owner':
            return True
        return False


class IsCashier(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.get(user=request.user.id)
        user_group = user_group.name.lower()
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'cashier' or user_group == 'shop owner':
            return True
        return False


class IsShopKeeper(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.get(user=request.user.id)
        user_group = user_group.name.lower()
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'store keeper' or user_group == 'shop owner':
            return True
        return False
    

class IsSalesPerson(permissions.BasePermission):
    def has_permission(self, request, view):
        user_group = Group.objects.get(user=request.user.id)
        user_group = user_group.name.lower()
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if user_group == 'salesperson' or user_group == 'shop owner':
            return True
        return False