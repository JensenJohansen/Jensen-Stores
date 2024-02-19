from django.shortcuts import render
from rest_framework.generics import *
from .serializers import *
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from user_management.permissions import *
from .permissions import *
from rest_framework.status import *
from rest_framework.response import Response


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
    
    def get_queryset(self):
        company = self.request.user.user_company
        user_company = get_user_model().objects.filter(user_company=company)
        queryset = Order.objects.filter(creator__in=user_company).order_by("-order_no")
        return queryset
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        pending = OrderStatus.objects.get(status="pending")
        return serializer.save(creator=self.request.user, authorization_status=pending)


class OrderRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='order_no'
    
    def get(self, request, order_no):
        queryset = self.get_queryset().filter(order_no=order_no)
        serializers = self.serializer_class(queryset, many=True)
        data = serializers.data
        
        return super().get(request)
    
    def perform_update(self, serializer):
        updater=self.request.user
        return serializer.save(authorizer=updater)


class GoodsOrderUpdateAPIView(RetrieveUpdateDestroyAPIView):
    queryset=GoodsOrder.objects.all()
    serializer_class=GoodsOrderSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopKeeper]
    lookup_field='id'
    
    def perform_update(self, serializer):
        return serializer.save(issuer=self.request.user)


class GoodsAvailableListView(ListAPIView):
    queryset = Goods.objects.all().order_by("-id")
    serializer_class = GoodsAvailableForSalesSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

class GoodsAvailableRetrieveAPIView(RetrieveAPIView):
    queryset = Goods.objects.all()
    serializer_class = GoodsAvailableForSalesSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"
    

class DeleteOrderCreateAPIView(CreateAPIView):
    serializer_class = DeleteOrderSerializer
    
    def post(self,request):
        data={
            "order_no":self.request.data['order_no'],
            "deleted_by":self.request.user.id
        }
        serializer=self.serializer_class(data=data)
        if serializer.is_valid():
            return_data=serializer.save()
        return Response(return_data,status=HTTP_200_OK)


