from rest_framework import serializers
from .models import *
from django.db.models import F, Q,Sum
from datetime import date
from order_management.models import Order, GoodsOrder
from user_management.models import Company
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

class StoreSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(max_length=150, read_only=True)
    company = serializers.SlugRelatedField(slug_field='company_name', read_only=True)
    store_location = serializers.CharField(max_length=150, read_only=True)
    store_supervisor = serializers.SlugRelatedField(slug_field='username', read_only=True)
    added_by = serializers.SlugRelatedField(slug_field='username', read_only=True)
    date_added = serializers.DateTimeField(read_only=True)
    store = serializers.JSONField(write_only=True)
    
    class Meta:
        model=Store
        fields='__all__'
    
    def create(self, validated_data):
        #store_name = validated_data['store_name']
        #store_location = validated_data['store_location']
        print(validated_data)
        
        added_by = validated_data['added_by']
        validated_data = validated_data['store']
        company = validated_data.pop('company')
        store_supervisor = validated_data.pop('store_supervisor')
        print(added_by)
        try:
            supervisor = get_user_model().objects.get(username=store_supervisor.title())
        except:
            raise get_user_model().DoesNotExist
        
        try:
            company = Company.objects.get(company_name=company)
        except:
            raise Company.DoesNotExist
        
        store = Store(store_supervisor=supervisor, company=company, added_by=added_by, **validated_data)
        store.save()
        return store


class GoodsSerializer(serializers.ModelSerializer):
    store_details=StoreSerializer(read_only=True,source='store')
    goods_type=serializers.SlugRelatedField(slug_field='goods_type', read_only=True)
    store=serializers.SlugRelatedField(slug_field='store_name', read_only=True)
    added_by = serializers.PrimaryKeyRelatedField(read_only=True,)
    goods = serializers.JSONField(write_only=True)
    
    class Meta:
        model=Goods
        fields='__all__'
        read_only_fields=['goods_name', 'goods_number', 'goods_quantity', 'lower_price_margin']
    
    def create(self, validated_data):
        goods = validated_data.pop('goods')
        added_by = validated_data['added_by']
        items = []
        for item in goods:
            goods_type = item.pop('goods_type')
            store = item.pop('store')
            try:
                goods_type = GoodsType.objects.get(goods_type=goods_type)
            except Exception as e:
                raise(e)
            try: 
                store = get_object_or_404(Store, store_name=store)
            except Exception as e:
                raise(e)
            
            item = Goods(
                goods_type=goods_type,
                store=store,
                added_by=added_by,
                **item
                )
            items.append(item)
        created_items = Goods.objects.bulk_create(items)
        return created_items

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
    issued_status = serializers.BooleanField()
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