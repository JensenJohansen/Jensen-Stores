from django.shortcuts import render
from rest_framework.generics import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.db.models import F
from .serializers import *

class GoodsTypeCreateAPIView(CreateAPIView):
    queryset = GoodsType.objects.all().order_by('id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
class GoodsTypeRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = GoodsType.objects.all().order_by('id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'
    
class StoreListCreateAPIView(ListCreateAPIView):
    queryset = Store.objects.all().order_by('id')
    serializer_class = StoreSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]

class StoreRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Store.objects.all().order_by('id')
    serializer_class = StoreSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class GoodsListCreateAPIView(ListCreateAPIView):
    queryset = Goods.objects.all().order_by('id')
    serializer_class = GoodsSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]


class GoodsRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Goods.objects.all().order_by('id')
    serializer_class = GoodsSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'


class UpdateStockListCreateAPIView(ListCreateAPIView):
    queryset = GoodsUpdate.objects.all().order_by('id')
    serializer_class = UpdateStockSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    

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
    serializer_class = GoodsSerializer
    lookup_field='goods_quantity'
    
    def get_queryset(self):
        queryset=Goods.objects.values().filter(goods_quantity__lte=self.kwargs['number_of_goods']).order_by('id')
        return queryset
    


