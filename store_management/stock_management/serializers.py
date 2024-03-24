from datetime import datetime
from rest_framework import serializers
from .models import *
from django.db.models import F, Q,Sum
from order_management.models import Order, GoodsOrder
from order_management import serializers as order_serializers
from user_management.models import Company
from django.db import transaction

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


class LeakageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leakage
        fields = "__all__"
        read_only_fields = ['added_by']
    
    def validate(self, attrs):
        amount_broken = attrs.get("amount_broken")
        good = attrs.get('goods')
        good = GoodsSerializer(good)
        goods_available = good['goods_available_for_sales']
        
        if amount_broken > goods_available.value:
            raise serializers.ValidationError({"amount":"The amount is higher than the available goods"})
        return attrs
    
    def create(self, validated_data):
        goods = validated_data.get('goods')
        amount_broken = validated_data.get('amount_broken')
        if validated_data['leakage_summary']:
            leakage_summary = validated_data.get('leakage_summary')
        added_by = validated_data.get("added_by")
        
        goods_update = UpdateStockSerializer(
                data={
                    
                        "goods":goods.id,
                        "quantity_added": -amount_broken,
                        "goods_update_reason":"broken_stock"
                    
                    }
                )
        if goods_update.is_valid(raise_exception=True):
                goods_update.save(updated_by=self.context.get('request').user)
        return super().create(validated_data)
    

class GoodsSerializer(serializers.ModelSerializer):
    broken=LeakageSerializer(many=True,read_only=True)
    store_details = StoreSerializer(read_only=True, source='store')
    goods_type = serializers.SlugRelatedField(slug_field='goods_type',queryset=GoodsType.objects.all())
    store = serializers.SlugRelatedField(slug_field='store_name',queryset=Store.objects.all())
    added_by = serializers.SlugRelatedField(slug_field="username",read_only=True)
    goods_in_pending = serializers.IntegerField(read_only=True)
    goods_available_for_sales = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Goods
        read_only_fields=['date_updated','time_updated',]
        exclude=['update_url']

    def to_representation(self, instance):
        if isinstance(instance, list):
            for goods in instance:
                self._annotate_goods_in_pending(goods)
        else:
            self._annotate_goods_in_pending(instance)

        return super().to_representation(instance)
    
    def _annotate_goods_in_pending(self, goods):
        try:
            goods_in_pending = Goods.objects.annotate(
                num_of_goods_pending=Sum(
                    F("goods_ref__goods_quantity"),
                    filter=Q(goods_ref__issued_status=False)
                )
            ).get(id=goods.id)
            goods.goods_available_for_sales = goods.goods_quantity - int(goods_in_pending.num_of_goods_pending if goods_in_pending.num_of_goods_pending is not None else 0)
            goods.goods_in_pending = goods_in_pending.num_of_goods_pending if goods_in_pending.num_of_goods_pending is not None else 0
        except Goods.DoesNotExist:
            goods.goods_available_for_sales = goods.goods_quantity
            goods.goods_in_pending = 0
    
    def get_fields(self):
        fields = super().get_fields()
        # Check if the serializer is being used for creating or updating
        if self.instance is None:
            # Serializer is used for creating objects
            fields['goods_quantity'].read_only = False
            
        else:
            # Serializer is used for updating objects
            fields['goods_quantity'].read_only = True
        return fields
      
    def update(self, instance, validated_data):
        '''Override update method to set date_updated and time_updated'''
        request = self.context.get('request')  # Get request object from context
        if request:
            request_url = request.build_absolute_uri()  # Get request URL
            instance.update_url = request_url
        instance.goods_name = validated_data.get('goods_name', instance.goods_name)
        instance.goods_type = validated_data.get('goods_type', instance.goods_type)
        instance.buying_price = validated_data.get('buying_price', instance.buying_price)
        instance.lower_price_margin = validated_data.get('lower_price_margin', instance.lower_price_margin)
        instance.store = validated_data.get('store', instance.store)
        instance.goods_number = validated_data.get('goods_number', instance.goods_number)
        instance.restricted_price = validated_data.get('restricted_price', instance.restricted_price)
        instance.alert_on_goods_quantity = validated_data.get('alert_on_goods_quantity', instance.alert_on_goods_quantity)
        # Set date_updated and time_updated to current datetime
        instance.date_updated = datetime.now().date()
        instance.time_updated = datetime.now().time()
        instance.save()
        return instance
        

class UpdateStockSerializer(serializers.ModelSerializer):
    """
    A serializer for updating stock(goods) when issuing or adding new stock
    """
    goods = serializers.PrimaryKeyRelatedField(queryset=Goods.objects.all())
    updated_by = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    balance = serializers.IntegerField(read_only=True)
    authorized_by=serializers.SlugRelatedField(slug_field='username',read_only=True)
    
    class Meta:
        model = GoodsUpdate
        fields = '__all__'
        read_only_fields=['quantity_available','authorized_by',]
        
    def create(self, validated_data):
        goods = validated_data.pop('goods')
        # get request user
        request=self.context.get('request')
        
        if request and 'updated_by' not in validated_data:
            request_user=request.user
        else:
            request_user=validated_data['updated_by']
            
        if request:
            authorizer=request.user
        else:
            authorizer=validated_data['authorized_by']
        
        try:
            goods = Goods.objects.get(id=goods.id)
            quantity_available = goods.goods_quantity
        except Goods.DoesNotExist:
            raise serializers.ValidationError({"goods": "The goods you entered do not exist."})
        
        try:
            with transaction.atomic():
                goods_quantity = quantity_available + validated_data['quantity_added']
                goods.goods_quantity = goods_quantity
                goods.save()
                
                goods_update = GoodsUpdate.objects.create(
                    goods=goods,
                    updated_by=request_user,
                    authorized_by=authorizer,
                    quantity_available=quantity_available,
                    quantity_added=validated_data['quantity_added'],
                    goods_update_reason=validated_data['goods_update_reason'] if validated_data['goods_update_reason'] else "updated_stock"
                )
        except Exception as e:
                raise e
        return goods_update
    def to_representation(self, instance):
        instance.balance=instance.quantity_available+instance.quantity_added
        return super().to_representation(instance)
    

class GoodsIssueSerializer(serializers.ModelSerializer):
    issuer = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    class Meta:
        model = GoodsOrder
        fields = ['id','issued_status','issuer','goods']
        read_only_fields=['goods_quantity',]
    
    def update(self, instance, validated_data):
        instance.issuer = validated_data.get('issuer', instance.issuer)
        
        if not instance.issued_status:
            updated_stock = UpdateStockSerializer(data={"updated_by":instance.issuer,"goods":instance.goods.id, "quantity_added":-instance.goods_quantity,"goods_update_reason":"issued_order"})
            if updated_stock.is_valid():
                updated_stock.save(authorized_by=instance.issuer)      
        
        instance.issued_status = validated_data.get('issued_status', instance.issued_status)
        instance.save()
        return instance


class GoodsTypeSerializer(serializers.ModelSerializer):
    goods_and_type=GoodsSerializer(many=True,read_only=True)
    class Meta:
        model=GoodsType
        fields='__all__'
        

class TemporaryGoodsUpdateSerializer(serializers.ModelSerializer):
    quantity_available=serializers.IntegerField(read_only=True)
    class Meta:
        model = TemporaryGoodsUpdate
        fields = '__all__'
        read_only_fields=['updated_by',]
        
    def create(self, validated_data):
        goods = validated_data.pop('goods')
        # get request user
        request=self.context.get('request')
        
        if request:
            request_user=request.user
        else:
            request_user=validated_data['updated_by']
        
        try:
            goods = Goods.objects.get(id=goods.id)
        except Goods.DoesNotExist:
            raise serializers.ValidationError({"goods": "The goods you entered do not exist."})
        
        try:
            goods_update = self.Meta.model.objects.create(
                goods=goods,
                updated_by=request_user,
                quantity_added=validated_data['quantity_added'],
                )
        except Exception as e:
                raise e
        return goods_update
    
    def to_representation(self, instance):
        instance.quantity_available=instance.goods.goods_quantity
        return super().to_representation(instance)