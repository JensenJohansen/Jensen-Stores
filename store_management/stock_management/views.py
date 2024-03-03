from django.shortcuts import render
from rest_framework.generics import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.status import *
from django.db.models import F, Count
from .serializers import *
from user_management.permissions import *

class GoodsTypeCreateAPIView(ListCreateAPIView):
    queryset = GoodsType.objects.all().order_by('-id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        filtered_data =  self.get_queryset().filter(company=user_company)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response(serialized_data)


class GoodsTypeRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = GoodsType.objects.all().order_by('id')
    serializer_class = GoodsTypeSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'


class StoreListCreateAPIView(ListCreateAPIView):
    queryset = Store.objects.all().order_by('-id')
    serializer_class = StoreSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    
    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)
    
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        filtered_data =  self.get_queryset().filter(company=user_company)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response({
            "count": len(serialized_data),
            "result": serialized_data
        })


class StoreRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Store.objects.all().order_by('-id')
    serializer_class = StoreSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    lookup_field='id'


class GoodsListCreateAPIView(ListCreateAPIView):
    queryset = Goods.objects.all().order_by('-id')
    serializer_class = GoodsSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]
    
    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)
    
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        stores = Store.objects.filter(company=user_company)
        filtered_data =  self.get_queryset().filter(store__in=stores)
        serializer = self.serializer_class(filtered_data,many=True)
        serialized_data = serializer.data
        return Response({
            "count": len(serialized_data),
            "result": serialized_data
        })


class GoodsRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Goods.objects.all().order_by('id')
    serializer_class = GoodsSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'
        


class UpdateStockListCreateAPIView(ListCreateAPIView):
    queryset = GoodsUpdate.objects.all().order_by('-id')
    serializer_class = UpdateStockSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]

    def perform_create(self, serializer):
        return serializer.save(updater=self.request.user.username)
    
    def get(self, request, *args, **kwargs):
        request_user = request.user
        user_company = request_user.user_company
        users = get_user_model().objects.filter(user_company=user_company)
        filtered_data = self.get_queryset().filter(updated_by__in=users)
        serializer = self.serializer_class(filtered_data,many=True)
        serialized_data = serializer.data
        return Response({
            "count": len(serialized_data),
            "results": serialized_data
        })


class GoodsUpdateListAPIView(ListAPIView):
    serializer_class = UpdateStockSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='goods'
    
    def get_queryset(self):
        queryset=GoodsUpdate.objects.filter(goods__id=self.kwargs['goods']).annotate(
            balance=(F('quantity_added')+F('quantity_available'))
        ).order_by('id')
        return queryset
    

class LeastStockGoodsListAPIView(ListAPIView):
    authentication_classes = [BasicAuthentication,TokenAuthentication]
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
    authentication_classes = [BasicAuthentication,TokenAuthentication]


class GoodsOrderIssueListView(ListAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [BasicAuthentication,TokenAuthentication]


class GoodsOrderIssueCreateAPIView(RetrieveUpdateAPIView):
    queryset = GoodsOrder.objects.all()
    serializer_class = GoodsIssueSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    lookup_field='id'


class LeakageListCreateView(ListCreateAPIView):
    queryset = Leakage.objects.all().order_by("-id")
    serializer_class = LeakageSerializer
    permission_classes = [IsAuthenticated,]
    authentication_classes = [TokenAuthentication]
    
    def perform_create(self, serializer):
        return serializer.save(added_by=self.request.user)
    

class GoodsUpdateAPIView(UpdateAPIView):
    queryset = Goods.objects.all()
    serializer_class = GoodsUSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    lookup_field='id'


