from django.shortcuts import render
from rest_framework.generics import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny, IsAuthenticatedOrReadOnly
from django.db.models import F
from .serializers import *
from .permissions import *

class GoodsTypeCreateAPIView(ListCreateAPIView):
    queryset = GoodsType.objects.all().order_by('id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]


class GoodsTypeRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = GoodsType.objects.all().order_by('id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'


class StoreListCreateAPIView(ListCreateAPIView):
    queryset = Store.objects.all().order_by('id')
    serializer_class = StoreSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

class StoreRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Store.objects.all().order_by('id')
    serializer_class = StoreSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field='id'


class GoodsListCreateAPIView(ListCreateAPIView):
    queryset = Goods.objects.all().order_by('id')
    serializer_class = GoodsSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    
    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)


class GoodsRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Goods.objects.all().order_by('id')
    serializer_class = GoodsSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'


class UpdateStockListCreateAPIView(ListCreateAPIView):
    queryset = GoodsUpdate.objects.all().order_by('id')
    serializer_class = UpdateStockSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]


class GoodsUpdateListAPIView(ListAPIView):
    serializer_class = UpdateStockSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='goods'
    
    def get_queryset(self):
        queryset=GoodsUpdate.objects.filter(goods__id=self.kwargs['goods']).annotate(
            balance=(F('quantity_added')+F('quantity_available'))
        ).order_by('id')
        return queryset
    

class LeastStockGoodsListAPIView(ListAPIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GoodsSerializer
    lookup_field='goods_quantity'
    
    def get_queryset(self):
        queryset=Goods.objects.filter(goods_quantity__lte=self.kwargs['threshold']).order_by('id')
        return queryset


class OrderIssueCreateAPIView(CreateAPIView):
    QuerySet = Order.objects.all()
    serializer_class = OrderIssueSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]


class GoodsOrderIssueListView(ListAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]


class GoodsOrderIssueCreateAPIView(RetrieveUpdateAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    lookup_field='id'

