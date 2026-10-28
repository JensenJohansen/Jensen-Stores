from rest_framework.generics import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import (
    IsAuthenticated,
)
from django.http import HttpResponse
try:
    from drf_yasg import openapi
    from drf_yasg.utils import swagger_auto_schema
except ImportError:
    openapi = None
    def swagger_auto_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.status import *
from django.db.models import F
from .serializers import *
from user_management.permissions import *
from rest_framework.response import Response
from rest_framework import status
from store_management.swagger import (
    counted_response_schema,
    counted_status_response_schema,
    delete_goods_by_user_request_schema,
    message_response_schema,
    store_nested_write_schema,
)


class GoodsTypeCreateAPIView(ListCreateAPIView):
    queryset = GoodsType.objects.all().order_by("-id")
    serializer_class = GoodsTypeSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.user_company)

    def perform_create(self, serializer):
        return serializer.save(company=self.request.user.user_company)


class CategoriesListCreateAPIView(ListCreateAPIView):
    queryset = Categories.objects.all().order_by("-id")
    serializer_class = CategoriesSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]


class CategoriesRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Categories.objects.all().order_by("id")
    serializer_class = CategoriesSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field = "id"


class SupplierListCreateAPIView(ListCreateAPIView):
    queryset = Supplier.objects.all().order_by("-id")
    serializer_class = SupplierSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.user_company)

    def perform_create(self, serializer):
        serializer.save(company=self.request.user.user_company, added_by=self.request.user)


class SupplierRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.user_company)


class PurchaseOrderListCreateAPIView(ListCreateAPIView):
    queryset = PurchaseOrder.objects.all().order_by("-id")
    serializer_class = PurchaseOrderSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def get_queryset(self):
        return self.queryset.filter(store__company=self.request.user.user_company)


class PurchaseOrderRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(store__company=self.request.user.user_company)


class GoodsTypeRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = GoodsType.objects.all().order_by("id")
    serializer_class = GoodsTypeSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(company=self.request.user.user_company)


class StoreListCreateAPIView(ListCreateAPIView):
    queryset = Store.objects.all().order_by("-id")
    serializer_class = StoreSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List stores for the authenticated company",
        responses={200: counted_response_schema()},
    )
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        filtered_data = self.get_queryset().filter(company=user_company)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response({"count": len(serialized_data), "result": serialized_data})

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Create a store",
        operation_description="The payload is nested under the `store` key.",
        request_body=store_nested_write_schema,
        responses={201: StoreSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class StoreRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Store.objects.all().order_by("-id")
    serializer_class = StoreSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field = "id"


class GoodsListCreateAPIView(ListCreateAPIView):
    queryset = Goods.objects.all().order_by("-id")
    serializer_class = GoodsSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List goods available to the authenticated company",
        responses={200: counted_response_schema()},
    )
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        stores = Store.objects.filter(company=user_company)
        filtered_data = self.get_queryset().filter(store__in=stores)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response({"count": len(serialized_data), "result": serialized_data})

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Create one or more goods records",
        operation_description="This endpoint accepts either a single goods object or a list of goods objects.",
        request_body=GoodsSerializer,
        responses={201: counted_status_response_schema()},
    )
    def post(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=is_many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "count": len(serializer.data),
                "status": status.HTTP_200_OK,
                "result": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class GoodsBulkTemplateAPIView(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    required_permissions_by_method = {
        "GET": ["stock_management.view_goods"],
    }

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Download the CSV template for bulk stock upload",
        responses={200: "CSV template downloaded successfully."},
    )
    def get(self, request, *args, **kwargs):
        csv_lines = [
            "goods_name,goods_number,goods_quantity,goods_type,buying_price,lower_price_margin,store,restricted_price,alert_on_goods_quantity",
            "Blue Band 500g,BB-500,120,Groceries,2400,2800,Main Store,true,20",
        ]
        response = HttpResponse("\n".join(csv_lines), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="goods_bulk_upload_template.csv"'
        return response


bulk_upload_parameters = None
if openapi is not None:
    bulk_upload_parameters = [
        openapi.Parameter(
            name="file",
            in_=openapi.IN_FORM,
            type=openapi.TYPE_FILE,
            required=True,
            description="UTF-8 CSV file matching the bulk goods upload template.",
        )
    ]


class GoodsBulkUploadAPIView(APIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    required_permissions_by_method = {
        "POST": ["stock_management.add_goods"],
    }
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Upload goods in bulk from a CSV file",
        operation_description=(
            "Upload a UTF-8 CSV file using the template from `goods/bulk-template/`. "
            "Each row creates one goods record for the authenticated user's company."
        ),
        manual_parameters=bulk_upload_parameters,
        responses={201: counted_status_response_schema()},
    )
    def post(self, request, *args, **kwargs):
        serializer = BulkGoodsUploadSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(payload, status=status.HTTP_201_CREATED)


class GoodsRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Goods.objects.all().order_by("id")
    serializer_class = GoodsSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field = "id"


class UpdateStockListCreateAPIView(ListCreateAPIView):
    queryset = GoodsUpdate.objects.all().order_by("-id")
    serializer_class = UpdateStockSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List stock updates for the authenticated company",
        responses={200: counted_response_schema("results")},
    )
    def get(self, request, *args, **kwargs):
        request_user = request.user
        user_company = request_user.user_company
        users = get_user_model().objects.filter(user_company=user_company)
        filtered_data = self.get_queryset().filter(updated_by__in=users)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response({"count": len(serialized_data), "results": serialized_data})

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Create one or more stock updates",
        operation_description="This endpoint accepts either a single update object or a list of update objects.",
        request_body=UpdateStockSerializer,
        responses={201: counted_status_response_schema()},
    )
    def post(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=is_many)
        if serializer.is_valid(raise_exception=True):
            serializer.save(goods_update_reason='updated_stock')
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "count": len(serializer.data),
                "status": status.HTTP_200_OK,
                "result": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class GoodsUpdateListAPIView(ListAPIView):
    serializer_class = UpdateStockSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "goods"

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List stock updates for a specific goods item",
        responses={200: UpdateStockSerializer(many=True)},
    )
    def get_queryset(self):
        queryset = (
            GoodsUpdate.objects.filter(goods__id=self.kwargs["goods"])
            .annotate(balance=(F("quantity_added") + F("quantity_available")))
            .order_by("-id")
        )
        return queryset


class LeastStockGoodsListAPIView(ListAPIView):
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GoodsSerializer
    lookup_field = "goods_quantity"

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List goods at or below the provided stock threshold",
        responses={200: GoodsSerializer(many=True)},
    )
    def get_queryset(self):
        queryset = Goods.objects.filter(
            goods_quantity__lte=self.kwargs["threshold"]
        ).order_by("id")
        return queryset


class GoodsOrderIssueListView(ListAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [BasicAuthentication, TokenAuthentication]


class GoodsOrderIssueCreateAPIView(RetrieveUpdateAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    lookup_field = "id"


class LeakageListCreateView(ListCreateAPIView):
    queryset = Leakage.objects.all().order_by("-id")
    serializer_class = LeakageSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]

    def get_queryset(self):
        return self.queryset.filter(goods__store__company=self.request.user.user_company)

    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)


class LeakageRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Leakage.objects.all()
    serializer_class = LeakageSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(goods__store__company=self.request.user.user_company)


class TemporaryGoodsUpdateListCreateAPIView(ListCreateAPIView):
    queryset = TemporaryGoodsUpdate.objects.all()
    serializer_class = TemporaryGoodsUpdateSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]

    def perform_create(self, serializer):
        return serializer.save(updated_by=self.request.user)

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="List temporary stock updates for the authenticated company",
        responses={200: counted_response_schema("results")},
    )
    def get(self, request, *args, **kwargs):
        request_user = request.user
        user_company = request_user.user_company
        users = get_user_model().objects.filter(user_company=user_company)
        filtered_data = self.get_queryset().filter(updated_by__in=users)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response({"count": len(serialized_data), "results": serialized_data})

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Create one or more temporary stock updates",
        operation_description="This endpoint accepts either a single update object or a list of update objects.",
        request_body=TemporaryGoodsUpdateSerializer,
        responses={201: counted_status_response_schema()},
    )
    def post(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=is_many)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "count": len(serializer.data),
                "status": status.HTTP_200_OK,
                "result": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class TemporaryGoodsUpdateRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = TemporaryGoodsUpdate.objects.all()
    serializer_class = TemporaryGoodsUpdateSerializer
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]
    lookup_field = "id"


class SalesReturnListCreateAPIView(ListCreateAPIView):
    queryset = SalesReturn.objects.all().order_by("-id")
    serializer_class = SalesReturnSerializer
    permission_classes = [IsAuthenticated, IsShopKeeper]
    authentication_classes = [BasicAuthentication, TokenAuthentication]

    def get_queryset(self):
        return self.queryset.filter(goods_order__goods__store__company=self.request.user.user_company)


class SalesReturnRetrieveAPIView(RetrieveAPIView):
    queryset = SalesReturn.objects.all()
    serializer_class = SalesReturnSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(goods_order__goods__store__company=self.request.user.user_company)


class StockTransferListCreateAPIView(ListCreateAPIView):
    queryset = StockTransfer.objects.all().order_by("-id")
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated, IsShopKeeper]
    authentication_classes = [BasicAuthentication, TokenAuthentication]

    def get_queryset(self):
        return self.queryset.filter(from_store__company=self.request.user.user_company)


class StockTransferRetrieveAPIView(RetrieveAPIView):
    queryset = StockTransfer.objects.all()
    serializer_class = StockTransferSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    lookup_field = "id"

    def get_queryset(self):
        return self.queryset.filter(from_store__company=self.request.user.user_company)


class DeleteGoodsByUserView(APIView):
    permission_classes = [
        IsAuthenticated,
    ]
    authentication_classes = [
        BasicAuthentication,
        TokenAuthentication,
    ]

    @swagger_auto_schema(
        tags=["Inventory"],
        operation_summary="Delete all goods created by a specific user",
        request_body=delete_goods_by_user_request_schema,
        responses={200: message_response_schema},
    )
    def post(self, request):
        serializer = GoodsDeleteByUserSerializer(data=request.data)
        if serializer.is_valid():
            goods_deleted = serializer.delete_goods()
            return Response({'message': f'Successfully deleted {goods_deleted[0]} goods'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
