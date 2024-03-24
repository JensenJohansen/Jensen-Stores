from django.urls import path,include
from .views import *

urlpatterns = [
    path("goods_type/", GoodsTypeCreateAPIView.as_view(), name="goods_type"),
    path("goods_type/<int:id>/", GoodsTypeRetrieveUpdateDestroyAPIView.as_view(), name="goods_type_single"),
    path("store/", StoreListCreateAPIView.as_view(), name="store"),
    path("store/<int:id>/", StoreRetrieveUpdateDestroyAPIView.as_view(), name="store-details"),
    path("goods/", GoodsListCreateAPIView.as_view(), name="goods"),
    path("goods/<int:id>/", GoodsRetrieveUpdateDestroyAPIView.as_view(), name="goods-details"),
    path("stock_update/", UpdateStockListCreateAPIView.as_view(), name="stock-update"),
    path("stock_update/<int:goods>/", GoodsUpdateListAPIView.as_view(), name="stock-update-entry"),
    path("leakage/", LeakageListCreateView.as_view(), name="leakage"),
    path("leakage/<int:id>/", LeakageRetrieveDestroyAPIView.as_view(), name="edit_leakage"),
    path("least_goods_quantity/<int:threshold>/", LeastStockGoodsListAPIView.as_view(), name="least_goods_quantity"),
    path("order_issue_goods/", GoodsOrderIssueListView.as_view(), name="goods-issue"),
    path("order_issue_goods/<int:id>/", GoodsOrderIssueCreateAPIView.as_view(), name="issue"),
    path("temporary_goods_update/", TemporaryGoodsUpdateListCreateAPIView.as_view(), name="temporary_goods_update"),
    path("temporary_goods_update/<int:id>/", TemporaryGoodsUpdateRetrieveUpdateDestroyAPIView.as_view(), name="single_temporary_update"),
]