from django.urls import path,include
from .views import *

urlpatterns = [
    path("create_order_status/", OrderStatusListCreateAPIView.as_view(), name="create_order_status"),
    path("create_order_status/<int:id>/", OrderStatusRetrieveUpdateDestroyAPIView.as_view(), name="single_order_status"),
    path("create_order/", OrderListCreateAPIView.as_view(), name="create_order"),
    path("create_order/<int:order_no>/", OrderRetrieveUpdateDestroyAPIView.as_view(), name="single_order"),
    path("update_goods_order/<int:id>/", GoodsOrderUpdateAPIView.as_view(), name="single_goods_order")
]
