from rest_framework import serializers
from .models import *
from django.db.models import F, Q,Sum
from datetime import date
from order_management.models import Order, GoodsOrder
from order_management import serializers as order_serializers
from user_management.models import Company
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework import status

class StoreSerializer(serializers.ModelSerializer):
    """
    A Serializer to handle store operations inluding adding and editing store
    """
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
        added_by = validated_data['added_by']
        validated_data = validated_data['store']
        company = validated_data.pop('company')
        store_supervisor = validated_data.pop('store_supervisor')
        try:
            supervisor = get_user_model().objects.get(username=store_supervisor.title())
        except:
            raise get_user_model().DoesNotExist
        
        try:
            company = Company.objects.get(company_name=company)
        except:
            raise Company.DoesNotExist
        
        if not validated_data['store_name']:
            raise serializers.ValidationError({"store_name": "This field is required"})
        
        if Store.objects.filter(store_name=validated_data['store_name']).exists():
            raise serializers.ValidationError({"store_name": "store name already in use by another store"})
        
        store = Store(store_supervisor=supervisor, company=company, added_by=added_by, **validated_data)
        store.save()
        return store
    
    def update(self, instance, validated_data):
        validated_data = validated_data['store']
        instance.store_name = validated_data.get('store_name', instance.store_name)
        instance.store_location = validated_data.get("store_location", instance.store_location)
        instance.save()
        return instance


class GoodsSerializer(serializers.ModelSerializer):
    """
    A serializer for adding goods to the specific store for the first time
    """
    store_details=StoreSerializer(read_only=True,source='store')
    goods_type=serializers.SlugRelatedField(slug_field='goods_type', read_only=True)
    store=serializers.SlugRelatedField(slug_field='store_name', read_only=True)
    added_by = serializers.SlugRelatedField(slug_field="username", read_only=True,)
    goods = serializers.JSONField(write_only=True)
    goods_in_pending = serializers.IntegerField(read_only=True)
    goods_available_for_sales = serializers.IntegerField(read_only=True)
    
    class Meta:
        model=Goods
        fields='__all__'
        read_only_fields=['goods_name', 'goods_number', 'goods_quantity', 'lower_price_margin', 'buying_price']
    
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
            
            try:
                added_goods = Goods.objects.get(goods_number=item.goods_number)
            except:
                pass
            
            item = Goods(
                goods_type=goods_type,
                store=store,
                added_by=added_by,
                **item
                )
            items.append(item)
        created_items = Goods.objects.bulk_create(items)
        return created_items

    
    def to_representation(self, instance):
        try:
            inst=[]
            for goods in instance:
                goods_in_pending = Goods.objects.annotate(
                    num_of_goods_pending=Sum(
                        F("goods_ref__goods_quantity"),
                        filter=
                            Q(goods_ref__issued_status=False)
                    )
                ).get(id=goods.id)
                if not goods_in_pending.num_of_goods_pending:
                    goods_in_pending.num_of_goods_pending = 0
                goods.goods_available_for_sales = (
                    goods.goods_quantity - goods_in_pending.num_of_goods_pending
                )
                goods.goods_in_pending = goods_in_pending.num_of_goods_pending   
                inst.append(goods)
            instance=inst
        except:
            goods_in_pending = Goods.objects.annotate(
                num_of_goods_pending=Sum(
                    F("goods_ref__goods_quantity"),
                    filter=
                        Q(goods_ref__issued_status=False)
                )
            ).get(id=instance.id)
            if not goods_in_pending.num_of_goods_pending:
                goods_in_pending.num_of_goods_pending = 0
            instance.goods_available_for_sales = (
                instance.goods_quantity - goods_in_pending.num_of_goods_pending
            )
            instance.goods_in_pending = goods_in_pending.num_of_goods_pending
            
   
        return super().to_representation(instance)
    
class GoodsUSerializer(serializers.ModelSerializer):
    store=serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    goods_type=serializers.PrimaryKeyRelatedField(queryset=GoodsType.objects.all())
    added_by=serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    class Meta:
        model = Goods
        fields = '__all__'
        read_only_fields=['goods_quantity',]
        

class UpdateStockSerializer(serializers.ModelSerializer):
    """
    A serializer for updating stock(goods) when issuing or adding new stock
    """
    goods=serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by=serializers.SlugRelatedField(slug_field='username', read_only=True)
    balance=serializers.IntegerField(read_only=True)
    update = serializers.JSONField(write_only=True)
    
    class Meta:
        model=GoodsUpdate
        fields= '__all__'
        read_only_fields=('quantity_available', 'quantity_added',)
        
    """def to_representation(self, instance):
        if isinstance(instance, list):
            return instance
        instance.balance=instance.quantity_available+instance.quantity_added    
        return instance"""
    
    def create(self, validated_data):
        """
        Purpose: update stock adds a goods or issue stock
        """
        user=validated_data.pop('updater')
        validated_data = validated_data['update']
        
        goods_update = []
        for item in validated_data:
            goods=item.pop('goods')
            
            try:
                goods=Goods.objects.get(id=goods)
                quantity_available=goods.goods_quantity
            except Goods.DoesNotExist:
                raise serializers.ValidationError({"goods":"goods you entered Does not Exist"})
            try:
                updated_goods=GoodsUpdate(
                    **item,
                    goods=goods,
                    updated_by=get_user_model().objects.get(username=user),
                    quantity_available=quantity_available
                    )
                goods.goods_quantity=quantity_available+item['quantity_added']
                goods.save()
                goods_update.append(updated_goods)
            except Exception as e:
                raise e
        goods_update = GoodsUpdate.objects.bulk_create(goods_update)
        return goods_update


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
        

class LeakageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leakage
        fields = "__all__"
        read_only_fields = ['added_by']
    
    def validate(self, attrs):
        amount_broken = attrs.get("amount_broken")
        good = attrs.get('goods')
        good = order_serializers.GoodsAvailableForSalesSerializer(good)
        goods_available = good['goods_available_for_sales']
        
        if amount_broken <= goods_available.value:
            raise serializers.ValidationError({"amount_broken":"The amount is higher than the available goods"})
        return attrs
    
    def create(self, validated_data):
        goods = validated_data.get('goods')
        amount_broken = validated_data.get('amount_broken')
        leakage_summery = validated_data.get('leakage_summery')
        added_by = validated_data.get("added_by")
        
        goods_update = UpdateStockSerializer(
                data={
                    "update": [
                        {
                        "goods":goods.id,
                        "quantity_added": -amount_broken
                        }
                        ]
                    }
                )
        if goods_update.is_valid(raise_exception=True):
                goods_update.save(updater=added_by.username)
        return super().create(validated_data)