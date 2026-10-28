from django.urls import path,include
from .views import *

urlpatterns = [
    path("categories/", CategoriesListCreateAPIView.as_view(), name="categories"),
    path("categories/<int:id>/", CategoriesRetrieveUpdateDestroyAPIView.as_view(), name="category_single"),
    path("goods_type/", GoodsTypeCreateAPIView.as_view(), name="goods_type"),
    path("goods_type/<int:id>/", GoodsTypeRetrieveUpdateDestroyAPIView.as_view(), name="goods_type_single"),
    path("suppliers/", SupplierListCreateAPIView.as_view(), name="suppliers"),
    path("suppliers/<int:id>/", SupplierRetrieveUpdateDestroyAPIView.as_view(), name="supplier_single"),
    path("purchase_orders/", PurchaseOrderListCreateAPIView.as_view(), name="purchase_orders"),
    path("purchase_orders/<int:id>/", PurchaseOrderRetrieveUpdateAPIView.as_view(), name="purchase_order_single"),
    path("store/", StoreListCreateAPIView.as_view(), name="store"),
    path("store/<int:id>/", StoreRetrieveUpdateDestroyAPIView.as_view(), name="store-details"),
    path("goods/", GoodsListCreateAPIView.as_view(), name="goods"),
    path("goods/bulk-template/", GoodsBulkTemplateAPIView.as_view(), name="goods-bulk-template"),
    path("goods/bulk-upload/", GoodsBulkUploadAPIView.as_view(), name="goods-bulk-upload"),
    path("goods/<int:id>/", GoodsRetrieveUpdateDestroyAPIView.as_view(), name="goods-details"),
    path("stock_update/", UpdateStockListCreateAPIView.as_view(), name="stock-update"),
    path("stock_update/<int:goods>/", GoodsUpdateListAPIView.as_view(), name="stock-update-entry"),
    path("leakage/", LeakageListCreateView.as_view(), name="leakage"),
    path("leakage/<int:id>/", LeakageRetrieveDestroyAPIView.as_view(), name="edit_leakage"),
    path("least_goods_quantity/<int:threshold>/", LeastStockGoodsListAPIView.as_view(), name="least_goods_quantity"),
    path("order_issue_goods/", GoodsOrderIssueListView.as_view(), name="goods-issue"),
    path("order_issue_goods/<int:id>/", GoodsOrderIssueCreateAPIView.as_view(), name="issue"),
    path("sales_returns/", SalesReturnListCreateAPIView.as_view(), name="sales_returns"),
    path("sales_returns/<int:id>/", SalesReturnRetrieveAPIView.as_view(), name="sales_return_single"),
    path("stock_transfers/", StockTransferListCreateAPIView.as_view(), name="stock_transfers"),
    path("stock_transfers/<int:id>/", StockTransferRetrieveAPIView.as_view(), name="stock_transfer_single"),
    path("temporary_goods_update/", TemporaryGoodsUpdateListCreateAPIView.as_view(), name="temporary_goods_update"),
    path("temporary_goods_update/<int:id>/", TemporaryGoodsUpdateRetrieveUpdateDestroyAPIView.as_view(), name="single_temporary_update"),
    path("delete_goods_by_user/", DeleteGoodsByUserView.as_view(), name="user_goods_delete")
]
