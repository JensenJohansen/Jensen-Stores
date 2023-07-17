from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny


class OrderStatusListCreateAPIView(ListCreateAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]


class OrderStatusRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class OrderListCreateAPIView(ListCreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]

class OrderRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class GoodsOrderUpdateAPIView(RetrieveUpdateAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'