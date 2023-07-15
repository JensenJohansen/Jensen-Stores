from rest_framework import serializers
from .models import *

class GoodsTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model=GoodsType
        fields='__all__'


class StoreSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(max_length=150)
    store_location = serializers.CharField(max_length=150)
    store_supervisor = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    added_by = serializers.SlugRelatedField(slug_field='username', queryset=get_user_model().objects.all())
    date_added = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model=Store
        fields='__all__'


class StoreName(serializers.Serializer):
    def to_representation(self, instance):
        return instance.store_name

class GoodsSerializer(serializers.ModelSerializer):
    goods_size_details=GoodsTypeSerializer(read_only=True,source='goods_size')
    store_details=StoreSerializer(read_only=True,source='store')
    goods_size=serializers.SlugRelatedField(slug_field='goods_type', queryset=GoodsType.objects.all())
    store= serializers.SlugRelatedField(slug_field='store_name', queryset=Store.objects.all())
    goods_name = serializers.CharField(max_length=150)
    goods_number = serializers.CharField(max_length=150)
    goods_quantity = serializers.IntegerField()
    lower_price_margin = serializers.IntegerField()
    added_by = serializers.SlugRelatedField(slug_field='username' ,queryset=get_user_model().objects.all())
    
    class Meta:
        model=Goods
        fields='__all__'
<<<<<<< Updated upstream

=======
        
    def to_representation(self, instance):
        goods_in_pending=Goods.objects.annotate(
            num_of_goods_pending=Sum(
                F('goods_ref__goods_quantity'),
                filter=Q(Q(goods_ref__issued_status=False) | Q(goods_ref__date_added__contains = date.today())))).get(id=instance.id)
        instance.goods_available_for_sales=instance.goods_quantity-goods_in_pending.num_of_goods_pending
        return super().to_representation(instance)
    
>>>>>>> Stashed changes

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
    