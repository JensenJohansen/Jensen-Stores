from rest_framework import serializers
from django.shortcuts import get_object_or_404
from .models import *
from django.db.models import Sum,F


class OrderStatusSerializer(serializers.ModelSerializer):
    
    class Meta:
        model=OrderStatus
        fields='__all__'
    

class GoodsOrderReadSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        Purpose: get order instance
        """
        returned_instance={
            'id':instance.id,
            'goods_name':instance.goods.goods_name,
            'goods_number':instance.goods.goods_number,
            'goods_quantity':instance.goods_quantity,
            'price':instance.price,
            'sum_per_goods':(instance.price*instance.goods_quantity)
        }
        return returned_instance
    # end def

class GoodsOrderReadSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        Purpose: get order instance
        """
        returned_instance={
            'id':instance.id,
            'goods_name':instance.goods.goods_name,
            'goods_number':instance.goods.goods_number,
            'goods_quantity':instance.goods_quantity,
            'price':instance.price,
            'sum_per_goods':(instance.price*instance.goods_quantity)
        }
        return returned_instance
    # end def

class OrderSerializer(serializers.ModelSerializer):
    order_goods_details=GoodsOrderReadSerializer(many=True,read_only=True,source='order_goods')
    order_goods=serializers.JSONField(write_only=True)
    total_order_amount = serializers.JSONField(read_only=True)
    class Meta:
        model=Order
        fields='__all__'
        
    def payable_vat_calc(self,order_total:float):
        return (order_total*(18/118))
    
    def create(self, validated_data):
        """
        Purpose: Create Order
        """
        order_goods=validated_data.pop('order_goods')
        creator=get_user_model().objects.get(id=validated_data['creator'].id)
        order=Order.objects.create(creator=creator)
        try:
            goods_handler=[]
            for o_goods in order_goods:
                goods_id=o_goods.pop('goods')
                good=get_object_or_404(Goods,id=goods_id)
                goods_handler.append(GoodsOrder(order=order,goods=good,**o_goods))
            GoodsOrder.objects.bulk_create(goods_handler)
        except Exception as e:
            raise (e)

        return order
    # end def
    def to_representation(self, instance):
        try:
            order_total=GoodsOrder.objects.filter(order=instance).aggregate(total=Sum(F('price')*F('goods_quantity')))
            if order_total['total'] is not None:
                order_total=order_total['total']-instance.order_discount
                instance.total_order_amount={'order_total':order_total,
                                        'VAT':self.payable_vat_calc(order_total=order_total)}
        except Exception as error:
            raise error
        return super().to_representation(instance)

class GoodsOrderSerializer(serializers.ModelSerializer):
    order=serializers.PrimaryKeyRelatedField(queryset=Order.objects.all(),many=True)
    class Meta:
        model=GoodsOrder
        fields='__all__'