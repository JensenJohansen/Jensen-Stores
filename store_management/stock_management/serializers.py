from rest_framework import serializers
from .models import *

class GoodsTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model=GoodsType
        fields='__all__'
        

class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model=Store
        fields='__all__'


class GoodsSerializer(serializers.ModelSerializer):
    goods_size_details=GoodsTypeSerializer(read_only=True,source='goods_size')
    store_details=StoreSerializer(read_only=True,source='store')
    goods_size=serializers.PrimaryKeyRelatedField(queryset=GoodsType.objects.all())
    store=serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    class Meta:
        model=Goods
        fields='__all__'


class BalanceOnUpdate(serializers.Serializer):
    def to_representation(self, instance):
        return instance.values
        """goods = instance.get('goods')
        updated_quantity = instance.get('quantity_added')
        
        try:
            prev_goods = Goods.objects.get(id=goods.id)
            prev_quantity = prev_goods.goods_quantity
        except:
            raise Goods.DoesNotExist
        
        balance = prev_quantity + updated_quantity
        return balance"""


class UpdateStockSerializer(serializers.ModelSerializer):
    goods=serializers.PrimaryKeyRelatedField(queryset=Goods.objects.all())
    updated_by=serializers.SlugRelatedField(slug_field='username',queryset=get_user_model().objects.all())
    balance=BalanceOnUpdate(read_only=True)
    class Meta:
        model=GoodsUpdate
        fields='__all__'
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
        return validated_data
    # end def
    