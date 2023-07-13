from django.urls import path,include
from .views import *

urlpatterns = [
    path("create_order_status/", OrderStatusListCreateAPIView.as_view(), name="create_order_status"),
    path("create_order_status/<int:id>/", OrderStatusRetrieveUpdateDestroyAPIView.as_view(), name="single_order_status"),
    path("create_order/", OrderListCreateAPIView.as_view(), name="create_order"),
    path("create_order/<int:id>/", OrderRetrieveUpdateDestroyAPIView.as_view(), name="single_order"),
]