from rest_framework import permissions
from .models import Order

class IsPaidOrEditable(permissions.BasePermission):
    """
    Checking the authorization status, and prohibity editing if the obj has been already paid
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        authorization = Order.objects.get(order_no=obj.order.order_no)
        
        if not authorization.authorization_status:
            return True
        
        if authorization.authorization_status != 'paid':
            return True
        
        return False
