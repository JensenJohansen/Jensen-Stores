from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *


class OrderStatusListCreateAPIView(ListCreateAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer


class OrderStatusRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    lookup_field='id'

class OrderListCreateAPIView(ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

class OrderRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    lookup_field='id'


class GoodsOrderedListAPIView(ListAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsOrderSerializer


class GoodsAvailableListAPIView(ListAPIView):
    queryset = Goods.objects.all()
    serializer_class = GoodsAvailableForSalesSerializer