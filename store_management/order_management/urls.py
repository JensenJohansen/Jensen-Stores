from django.urls import path,include
from .views import *

urlpatterns = [
    path("create_order/", OrderListCreateAPIView.as_view(), name="create_order"),
    path("create_order/<int:order_no>/", OrderRetrieveUpdateDestroyAPIView.as_view(), name="single_order"),
    path("payments/", PaymentListCreateAPIView.as_view(), name="payments"),
    path("payments/<int:id>/", PaymentRetrieveAPIView.as_view(), name="payment_single"),
    path("audit_logs/", AuditLogListAPIView.as_view(), name="audit_logs"),
    path("dashboard/", DashboardSummaryAPIView.as_view(), name="dashboard"),
    path("update_goods_order/<int:id>/", GoodsOrderUpdateAPIView.as_view(), name="single_goods_order"),
    path("delete_order/", DeleteOrderCreateAPIView.as_view(), name="delete_order")
]
