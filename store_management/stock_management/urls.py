from django.urls import path,include
from .views import *

urlpatterns = [
    path("goods_type/", GoodsTypeCreateAPIView.as_view(), name="goods_type"),
    path("goods_type/<int:id>/", GoodsTypeRetrieveUpdateDestroyAPIView.as_view(), name="goods_type_single"),
    path("store/", StoreListCreateAPIView.as_view(), name="store"),
    path("store/<int:id>/", StoreRetrieveUpdateDestroyAPIView.as_view(), name="store_single"),
    path("goods/", GoodsListCreateAPIView.as_view(), name="goods"),
    path("goods/<int:id>/", GoodsRetrieveUpdateDestroyAPIView.as_view(), name="goods_single"),
    path("stock_update/", UpdateStockListCreateAPIView.as_view(), name="update_stock"),
    path("goods_update_entry/<int:goods>/", GoodsUpdateListAPIView.as_view(), name="goods_update_entry"),
    path("least_goods_quantity/<int:threshold>/", LeastStockGoodsListAPIView.as_view(), name="least_goods_quantity")
]