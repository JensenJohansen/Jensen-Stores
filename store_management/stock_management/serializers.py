from rest_framework import serializers
from .models import *
from django.db.models import F, Q,Sum
from datetime import date
from order_management.models import Order, GoodsOrder

class StoreSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(max_length=150)
    store_location = serializers.CharField(max_length=150)
    store_supervisor = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    added_by = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    date_added = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model=Store
        fields='__all__'

class GoodsSerializer(serializers.ModelSerializer):
    store_details=StoreSerializer(read_only=True,source='store')
    goods_type=serializers.SlugRelatedField(slug_field='goods_type',queryset=GoodsType.objects.all())
    store=serializers.SlugRelatedField(slug_field='store_name',queryset=Store.objects.all())
    goods_in_pending=serializers.IntegerField(read_only=True)
    goods_available_for_sales=serializers.IntegerField(read_only=True)
    
    class Meta:
        model=Goods
        fields='__all__'
        
    def to_representation(self, instance):
        try:
            goods_in_pending=Goods.objects.annotate(
                num_of_goods_pending=Sum(F('goods_ref__goods_quantity'),filter=Q(Q(goods_ref__issued_status=False) 
                                                                                & Q(goods_ref__date_added__contains = date.today())))).get(id=instance.id)
            if not goods_in_pending.num_of_goods_pending:
                goods_in_pending.num_of_goods_pending=0
        except Exception as e:
            raise(e)
        instance.goods_available_for_sales=instance.goods_quantity-goods_in_pending.num_of_goods_pending
        instance.goods_in_pending = goods_in_pending.num_of_goods_pending
        return super().to_representation(instance)

class UpdateStockSerializer(serializers.ModelSerializer):
    goods=serializers.PrimaryKeyRelatedField(queryset=Goods.objects.all())
    updated_by=serializers.SlugRelatedField(slug_field='username',queryset=get_user_model().objects.all())
    balance=serializers.IntegerField(read_only=True)
    
    class Meta:
        model=GoodsUpdate
        fields= '__all__'
        read_only_fields=('quantity_available',)

    def create(self, validated_data):
        """
        Purpose: update stock adds a goods or issue stock
        """
        user=validated_data.pop('updated_by')
        goods=validated_data.pop('goods')
        
        try:
            user=get_user_model().objects.get(username=user)
        except:
            raise get_user_model().DoesNotExist
        
        try:
            goods=Goods.objects.get(id=goods.id)
            quantity_available=goods.goods_quantity
        except:
            raise Goods.DoesNotExist
        try:
            updated_goods=GoodsUpdate.objects.create(**validated_data,goods=goods,updated_by=user,
                                            quantity_available=quantity_available)
            goods.goods_quantity=quantity_available+validated_data['quantity_added']
            goods.save()
        except Exception as e:
            raise e
        
        
        return updated_goods
    
    def to_representation(self, instance):
        instance.balance=instance.quantity_available+instance.quantity_added
        return super().to_representation(instance)
    # end def


class OrderIssueSerializer(serializers.Serializer):
    order_no = serializers.IntegerField(read_only=True)
    authorizer = serializers.SlugRelatedField(slug_field='username', read_only=True)
    authorization_status = serializers.CharField(max_length=50, read_only=True)
    creator = serializers.SlugRelatedField(slug_field='username', read_only=True)
    issued_status = serializers.BooleanField()
    order_discount = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Order
        fields = '__all__'


class GoodsIssueSerializer(serializers.ModelSerializer):
    issuer = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    class Meta:
        model = GoodsOrder
        fields = ['id','issued_status','issuer','goods']
        read_only_fields=['goods_quantity',]
        
    def update(self, instance, validated_data):
        instance.issuer = validated_data.get('issuer', instance.issuer)
        
        if not instance.issued_status:
            updated_stock = UpdateStockSerializer(data={"updated_by":instance.issuer, "goods":instance.goods.id, "quantity_added":-instance.goods_quantity})
            if updated_stock.is_valid():
                updated_stock.save()      
        
        instance.issued_status = validated_data.get('issued_status', instance.issued_status)
        instance.save()
        return instance

class GoodsTypeSerializer(serializers.ModelSerializer):
    goods_and_type=GoodsSerializer(many=True,read_only=True)
    class Meta:
        model=GoodsType
        fields='__all__'
