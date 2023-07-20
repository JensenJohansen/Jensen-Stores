from rest_framework import serializers
from django.shortcuts import get_object_or_404
from .models import *
from django.db.models import Sum,F,Q,Case,When,Value
from datetime import date
from stock_management.serializers import UpdateStockSerializer


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
    order=serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    class Meta:
        model=GoodsOrder
        fields='__all__'
    
    def update(self, instance, validated_data):
        issued_status = validated_data.get('issued_status')
        instance.issuer = validated_data.get('issuer', instance.issuer)
        instance.goods_quantity = validated_data.get('goods_quantity', instance.goods_quantity)
        
        if instance.issued_status != issued_status:
            quantity = instance.goods_quantity
            
            if issued_status:
                quantity = -quantity
            else:
                quantity = quantity
            
            updated_stock = UpdateStockSerializer(
                data={
                    "updated_by":instance.issuer, 
                    "goods":instance.goods.id,
                    "quantity_added": quantity
                    }
                )
            if updated_stock.is_valid():
                updated_stock.save()
            
        instance.issued_status = issued_status
        instance.save()
        return instance

"""class GoodsAvailableForSalesSerializer(serializers.ModelSerializer):
    goods_in_pending=serializers.IntegerField(read_only=True)
    goods_available_for_sales=serializers.IntegerField(read_only=True)
    class Meta:
        model=Goods
        fields='__all__'
        
    def to_representation(self, instance):
        goods_in_pending=Goods.objects.annotate(
            num_of_goods_pending=Sum(
                F('goods_ref__goods_quantity'),
                filter=Q(Q(goods_ref__issued_status=False) | Q(goods_ref__date_added__contains = date.today())))).get(id=instance.id)
        if not goods_in_pending.num_of_goods_pending:
            goods_in_pending.num_of_goods_pending = 0 
        instance.goods_available_for_sales=instance.goods_quantity-goods_in_pending.num_of_goods_pending
        instance.goods_in_pending = goods_in_pending.num_of_goods_pending
        return super().to_representation(instance)"""
