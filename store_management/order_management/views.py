from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework.generics import *
from .serializers import *
try:
    from drf_yasg.utils import swagger_auto_schema
except ImportError:
    def swagger_auto_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from user_management.permissions import *
from .permissions import *
from rest_framework.status import *
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.utils.dateparse import parse_date
from django.db.models import Sum, F, Q, Case, When, Value, IntegerField
from user_management.models import Company
from store_management.swagger import (
    delete_order_request_schema,
    delete_order_response_schema,
    goods_issue_write_schema,
    order_write_schema,
)
from stock_management.models import Goods, Leakage, SalesReturn, StockTransfer


class OrderListCreateAPIView(ListCreateAPIView):
    queryset = Order.objects.all().order_by("-order_no")
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSalesPerson]
    
    def get_queryset(self):
        return get_visible_order_queryset_for_user(
            self.request.user,
            self.queryset,
        ).order_by("-order_no")
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        return serializer.save(
            creator=self.request.user,
            authorization_status=OrderAuthorizationStatus.PENDING,
        )

    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Create an order with one or more goods lines",
        request_body=order_write_schema,
        responses={201: OrderSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class OrderRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='order_no'

    def get_queryset(self):
        return get_visible_order_queryset_for_user(self.request.user, self.queryset)
    
    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Retrieve a single order by order number",
        responses={200: OrderSerializer},
    )
    def get(self, request, order_no):
        queryset = self.get_queryset().filter(order_no=order_no)
        serializers = self.serializer_class(queryset, many=True)
        data = serializers.data
        
        return super().get(request)
    
    def perform_update(self, serializer):
        sync_user_group_permissions(self.request.user)
        if not self.request.user.has_perm("order_management.change_order"):
            raise PermissionDenied("You do not have permission to update orders.")
        updater=self.request.user
        return serializer.save(authorizer=updater)

    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Update an order and optionally its goods lines",
        request_body=order_write_schema,
        responses={200: OrderSerializer},
    )
    def put(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Partially update an order",
        request_body=order_write_schema,
        responses={200: OrderSerializer},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class GoodsOrderUpdateAPIView(RetrieveUpdateDestroyAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'

    def get_queryset(self):
        return get_visible_goods_order_queryset_for_user(self.request.user, self.queryset)
    
    def perform_update(self, serializer):
        return serializer.save(issuer=self.request.user)

    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Update issuance state for an order line",
        request_body=goods_issue_write_schema,
        responses={200: GoodsOrderSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Partially update issuance state for an order line",
        request_body=goods_issue_write_schema,
        responses={200: GoodsOrderSerializer},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class DeleteOrderCreateAPIView(CreateAPIView):
    serializer_class = DeleteOrderSerializer
    
    @swagger_auto_schema(
        tags=["Orders"],
        operation_summary="Delete an order and restore issued stock when needed",
        request_body=delete_order_request_schema,
        responses={200: delete_order_response_schema},
    )
    def post(self,request):
        data={
            "order_no":self.request.data['order_no'],
            "deleted_by":self.request.user.id
        }
        serializer=self.serializer_class(data=data)
        if serializer.is_valid():
            return_data=serializer.save()
        return Response(return_data,status=HTTP_200_OK)


class PaymentListCreateAPIView(ListCreateAPIView):
    queryset = Payment.objects.all().order_by("-id")
    serializer_class = PaymentSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsCashier]

    def get_queryset(self):
        return self.queryset.filter(order__creator__user_company=self.request.user.user_company)


class PaymentRetrieveAPIView(RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(order__creator__user_company=self.request.user.user_company)


class AuditLogListAPIView(ListAPIView):
    queryset = AuditLog.objects.all().order_by("-created_at")
    serializer_class = AuditLogSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.user_company)


class DashboardSummaryAPIView(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    required_permissions_by_method = {
        "GET": ["order_management.view_auditlog"],
    }

    def get(self, request):
        company = request.user.user_company
        start_date = parse_date(request.query_params.get("start_date", "")) if request.query_params.get("start_date") else None
        end_date = parse_date(request.query_params.get("end_date", "")) if request.query_params.get("end_date") else None

        orders = Order.objects.filter(creator__user_company=company)
        payments = Payment.objects.filter(order__creator__user_company=company)
        goods = Goods.objects.filter(store__company=company)
        leakages = Leakage.objects.filter(goods__store__company=company)
        returns = SalesReturn.objects.filter(goods_order__goods__store__company=company)
        transfers = StockTransfer.objects.filter(from_store__company=company)

        if start_date:
            orders = orders.filter(date_added__date__gte=start_date)
            payments = payments.filter(date_added__date__gte=start_date)
            leakages = leakages.filter(broken_date__date__gte=start_date)
            returns = returns.filter(date_added__date__gte=start_date)
            transfers = transfers.filter(date_added__date__gte=start_date)
        if end_date:
            orders = orders.filter(date_added__date__lte=end_date)
            payments = payments.filter(date_added__date__lte=end_date)
            leakages = leakages.filter(broken_date__date__lte=end_date)
            returns = returns.filter(date_added__date__lte=end_date)
            transfers = transfers.filter(date_added__date__lte=end_date)

        sales_total = orders.aggregate(total=Sum(F("order_goods__price") * F("order_goods__goods_quantity")))["total"] or 0
        total_discount = orders.aggregate(total=Sum("order_discount"))["total"] or 0
        sales_total = float(sales_total - total_discount)
        total_paid = float(payments.filter(status="completed").aggregate(total=Sum("amount"))["total"] or 0)
        inventory_value = float(goods.aggregate(total=Sum(F("goods_quantity") * F("buying_price")))["total"] or 0)
        low_stock_count = goods.filter(goods_quantity__lte=F("alert_on_goods_quantity")).count()
        leakage_total = leakages.aggregate(total=Sum("amount_broken"))["total"] or 0
        returns_total = returns.aggregate(total=Sum("returned_quantity"))["total"] or 0
        transfer_total = transfers.aggregate(total=Sum("quantity"))["total"] or 0
        top_goods = list(
            Goods.objects.filter(store__company=company)
            .annotate(
                sold_quantity=Sum(
                    "goods_ref__goods_quantity",
                    filter=Q(goods_ref__order__creator__user_company=company)
                )
            )
            .order_by("-sold_quantity", "goods_name")
            .values("id", "goods_name", "goods_number", "sold_quantity")[:5]
        )

        response = {
            "period": {"start_date": start_date, "end_date": end_date},
            "orders": {
                "count": orders.count(),
                "sales_total": sales_total,
                "paid_total": total_paid,
                "outstanding_total": max(sales_total - total_paid, 0),
                "pending_count": orders.filter(authorization_status=OrderAuthorizationStatus.PENDING).count(),
                "approved_count": orders.filter(authorization_status=OrderAuthorizationStatus.APPROVED).count(),
                "paid_count": orders.filter(authorization_status=OrderAuthorizationStatus.PAID).count(),
            },
            "inventory": {
                "goods_count": goods.count(),
                "inventory_value": inventory_value,
                "low_stock_count": low_stock_count,
                "leakage_quantity": leakage_total,
            },
            "operations": {
                "returns_quantity": returns_total,
                "transfers_quantity": transfer_total,
                "payments_count": payments.count(),
            },
            "top_goods": top_goods,
        }
        return Response(response, status=HTTP_200_OK)
