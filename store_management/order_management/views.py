from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny


class OrderStatusListCreateAPIView(ListCreateAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [ BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]


class OrderStatusRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class OrderListCreateAPIView(ListCreateAPIView):
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Order.objects.all().order_by("-date_added")
        return queryset
    

class OrderRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class GoodsOrderUpdateAPIView(RetrieveUpdateAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'