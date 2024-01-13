from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from user_management.permissions import *
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
    
    def perform_create(self, serializer):
        pending = OrderStatus.objects.get(status="pending")
        return serializer.save(creator=self.request.user)


class OrderRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='order_no'
    
    def perform_update(self, serializer):
        user_group = Group.objects.get(appuser=self.request.user.id)  
        print(user_group.name)
        return serializer.save()


class GoodsOrderUpdateAPIView(RetrieveUpdateAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'
    
    def perform_update(self, serializer):
        return serializer.save(issuer=self.request.user)