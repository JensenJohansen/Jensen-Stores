from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from stock_management.permissions import *
from .permissions import *


class OrderStatusListCreateAPIView(ListCreateAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]


class OrderStatusRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field='id'


class OrderListCreateAPIView(ListCreateAPIView):
    queryset = Order.objects.all().order_by("-order_no")
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSalesPerson]


class OrderRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSalesPerson]
    lookup_field='order_no'


class GoodsOrderUpdateAPIView(RetrieveUpdateAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsSalesPerson, IsPaidOrEditable]
    lookup_field='id'