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
            'issued_status': instance.issued_status,
            'sum_per_goods':(instance.price*instance.goods_quantity)
        }
        return returned_instance
    # end def


class OrderSerializer(serializers.ModelSerializer):
    order_goods_details=GoodsOrderReadSerializer(many=True,source='order_goods', read_only=True)
    order_goods=serializers.JSONField(write_only=True, required=False)
    total_order_amount = serializers.JSONField(read_only=True)
    creator = serializers.SlugRelatedField(slug_field='username', read_only=True)
    authorization_status = serializers.SlugRelatedField(slug_field='status', queryset=OrderStatus.objects.all())
    class Meta:
        model=Order
        fields='__all__'
        
    def payable_vat_calc(self,order_total:float):
        return (order_total*(18/118))
    
    def validate(self, attrs):
        try:
            orders = attrs['order_goods']
        except:
            orders = []
        
        
        attrs['order_goods'] = []
        for order in orders:
            goods = order.get('goods')
            ordered_quantity = order.get('goods_quantity')
            price = order.get('price')
            item = Goods.objects.get(id=goods)
            if ordered_quantity < item.goods_quantity:
                attrs['order_goods'].append(order)
            else:
                raise serializers.ValidationError("Goods_quantity: you entered more orders than the quantity available")
            
            if price < item.lower_price_margin:
                raise serializers.ValidationError("Price: Please consider lower price margin")
            
        return attrs
    
    def create(self, validated_data):
        """
        Purpose: Create Order
        """
        order_goods=validated_data.pop('order_goods')
        caption = validated_data.pop('order_caption')
        order_discount = validated_data.pop('order_discount')
        creator = validated_data['creator']
        if order_discount:
            pass
        else:
            order_discount=0.00
            
        order=Order.objects.create(
            creator=creator, 
            order_caption=caption,
            order_discount=order_discount
            )
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
    
    def update(self, instance, validated_data):
        """
        purpose: Editing order, especially adding new goods and authorization status
        """
        order = instance.order_no
        if instance.authorization_status != "paid":
            if validated_data["order_goods"]:
                order_goods_details = instance.order_goods
                for item in validated_data["order_goods"]:
                    goods = item.get("goods")
                    try:
                        match = order_goods_details.get(goods_id=goods)
                        match.price = item.get("price", match.price)
                        match.goods_quantity = item.get("goods_quantity", match.goods_quantity)
                        match.save()
                    except:
                        good = get_object_or_404(Goods, id=goods)
                        updated_goods = GoodsOrder(
                            order=instance,
                            goods=good,
                            goods_quantity=item.get("goods_quantity"),
                            price=item.get("price"),
                        )
                        updated_goods.save()
            instance.authorization_status = validated_data.get("authorization_status", instance.authorization_status) 
        instance.save()
        return instance
    
    def to_representation(self, instance):
        try:
            order_total=GoodsOrder.objects.filter(order=instance).aggregate(total=Sum(F('price')*F('goods_quantity')))
            if order_total['total'] is not None:
                order_total=order_total['total']-instance.order_discount
                instance.total_order_amount={'order_total':order_total,
                                        'VAT':round(self.payable_vat_calc(order_total=order_total),2)}
        except Exception as error:
            raise error
        return super().to_representation(instance)

class GoodsOrderSerializer(serializers.ModelSerializer):
    order=serializers.PrimaryKeyRelatedField(read_only=True)
    goods_issue = serializers.JSONField(write_only=True, allow_null=True)
    class Meta:
        model=GoodsOrder
        fields='__all__'
        read_only_fields = ['goods_quantity', 'price', 'issued_status', 'goods', 'issuer']
    
    def update(self, instance, validated_data):
        instance.issuer = validated_data.get('issuer', instance.issuer)
        validated_data = validated_data['goods_issue']
        issued_status = validated_data.get('issued_status')
        
        if instance.issued_status != issued_status:
            instance.goods_quantity = validated_data.get('goods_quantity', instance.goods_quantity)
            quantity = instance.goods_quantity
            
            if issued_status:
                quantity = -quantity
            else:
                quantity = quantity
            
            updated_stock = UpdateStockSerializer(
                data={
                    "update": [
                        {
                        "goods":instance.goods.id,
                        "quantity_added": quantity
                        }
                        ]
                    }
                )
            
            
            if updated_stock.is_valid(raise_exception=True):
                updated_stock.save(updater=instance.issuer.username)
            
            instance.issued_status = issued_status
        
        if not instance.issued_status:
            instance.price = validated_data.get("price", instance.price)
            instance.goods_quantity = validated_data.get("goods_quantity", instance.goods_quantity)
            
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
