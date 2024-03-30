from rest_framework import serializers
from django.shortcuts import get_object_or_404
from .models import *
from django.db.models import Sum, F, Q
from datetime import date
from stock_management import serializers as stock_serializer

class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = "__all__"


class GoodsOrderReadSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        Purpose: get order instance
        """
        returned_instance = {
            "id": instance.id,
            "goods_name": instance.goods.goods_name,
            "goods_number": instance.goods.goods_number,
            "goods_quantity": instance.goods_quantity,
            "price": instance.price,
            "issued_status": instance.issued_status,
            "sum_per_goods": (instance.price * instance.goods_quantity),
        }
        return returned_instance

    # end def


class OrderSerializer(serializers.ModelSerializer):
    order_goods_details = GoodsOrderReadSerializer(
        many=True, source="order_goods", read_only=True
    )
    order_goods = serializers.JSONField(write_only=True, required=False)
    total_order_amount = serializers.JSONField(read_only=True)
    cash_authorizer = serializers.JSONField(read_only=True)
    creator = serializers.SlugRelatedField(slug_field="username", read_only=True)
    authorization_status = serializers.SlugRelatedField(
        slug_field="status", queryset=OrderStatus.objects.all(), required=False
    )

    class Meta:
        model = Order
        fields = "__all__"

    def payable_vat_calc(self, order_total: float):
        return order_total * (18 / 118)

    def validate(self, attrs):
        try:
            orders = attrs["order_goods"]
        except:
            orders = []

        attrs["order_goods"] = []
        for order in orders:
            goods = order.get("goods")
            ordered_quantity = order.get("goods_quantity")
            price = order.get("price")
            item = Goods.objects.get(id=goods)
            if ordered_quantity <= item.goods_quantity:
                attrs["order_goods"].append(order)
            else:
                raise serializers.ValidationError(
                    "Goods_quantity: you entered more orders than the quantity available"
                )
                
            #This check if you have limited your price to not go below lower price margin
            if price < item.lower_price_margin and item.restricted_price:
                raise serializers.ValidationError(
                    "Price: Please consider lower price margin"
                )

        return attrs

    def create(self, validated_data):
        """
        Purpose: Create Order
        """
        authorization_status = validated_data.pop("authorization_status")
        order_goods = validated_data.pop("order_goods")
        caption = validated_data.pop("order_caption")
        creator = validated_data["creator"]
        try:
            order_discount = validated_data.pop("order_discount")
        except:
            order_discount = 0.00

        order = Order.objects.create(
            creator=creator,
            order_caption=caption,
            order_discount=order_discount,
            authorization_status=authorization_status,
        )
        try:
            goods_handler = []
            for o_goods in order_goods:
                goods_id = o_goods.pop("goods")
                good = get_object_or_404(Goods, id=goods_id)
                goods_handler.append(GoodsOrder(order=order, goods=good, **o_goods))
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
                        match.goods_quantity = item.get(
                            "goods_quantity", match.goods_quantity
                        )
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
            try:
                changes = validated_data.get("authorization_status")
                if changes != instance.authorization_status:
                    instance.authorizer = validated_data["authorizer"]
            except:
                pass
            instance.authorization_status = validated_data.get(
                "authorization_status", instance.authorization_status
            )
        instance.save()
        return instance

    def to_representation(self, instance):
        try:
            instance.cash_authorizer = instance.authorizer.username
        except:
            instance.cash_authorizer = None
        try:
            order_total = GoodsOrder.objects.filter(order=instance).aggregate(
                total=Sum(F("price") * F("goods_quantity"))
            )
            if order_total["total"] is not None:
                order_total = order_total["total"] - instance.order_discount
                instance.total_order_amount = {
                    "order_total": order_total,
                    "VAT": round(self.payable_vat_calc(order_total=order_total), 2),
                }
        except Exception as error:
            raise error
        return super().to_representation(instance)


class GoodsOrderSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(read_only=True)
    goods_issue = serializers.JSONField(write_only=True, allow_null=True)

    class Meta:
        model = GoodsOrder
        fields = "__all__"
        read_only_fields = [
            "goods_quantity",
            "price",
            "issued_status",
            "goods",
            "issuer",
        ]
        
    def update(self, instance, validated_data):
        # Extract goods_issue data from validated_data
        goods_issue_data = validated_data.pop('goods_issue', None)
        if goods_issue_data:
            issuer = self.instance.issuer if self.instance.issuer is not None else self.context.get('request').user
            
            # Get issued_status from goods_issue_data or use the current instance's value
            issued_status = goods_issue_data.get('issued_status', instance.issued_status)
            if instance.issued_status != issued_status:
                # Update instance's issued_status and goods_quantity if changed
                instance.issued_status = issued_status
                instance.goods_quantity = goods_issue_data.get('goods_quantity', instance.goods_quantity)

                # Update stock quantity based on the issued_status change
                if instance.issued_status:
                    goods=stock_serializer.GoodsSerializer(get_object_or_404(Goods,id=instance.goods.id)).data
                    
                    if instance.goods_quantity <= goods['goods_quantity']:
                        quantity = -instance.goods_quantity
                    else:
                        raise ValueError("The number exceed the amount available")
                    
                    instance.issuer=issuer
                else:
                    quantity = instance.goods_quantity
                instance.save()
                # Serialize stock update data and save it
                stock_data = {'updated_by':issuer,'goods': instance.goods.id, 'quantity_added': quantity,'goods_update_reason':'issued_order'}
                stock_serial = stock_serializer.UpdateStockSerializer(data=stock_data)
                
                if stock_serial.is_valid():
                    stock_serial.save(authorized_by=issuer)

                # Update order issued status based on all items' issued_status in the order
                order = instance.order
                order.issued_status = all(item.issued_status for item in order.order_goods.all())
                order.save()

        # Update other fields if not issued and the order is not paid
        if not instance.issued_status and instance.order.authorization_status.status != 'paid':
            instance.price = validated_data.get('price', instance.price)

        # Call the superclass's update method to save the instance with updated data
        instance.save()  # Save the instance to persist the changes to the database
        return instance
    


class DeletedOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeletedOrder
        fields = "__all__"


class DeleteOrderSerializer(serializers.Serializer):
    order_no = serializers.IntegerField()
    deleted_by = serializers.IntegerField()
    delete_response = serializers.CharField(read_only=True, max_length=200)

    def create(self, data):
        order = data["order_no"]
        goods_to_be_updated = []
        goods_object = []
        try:
            order = Order.objects.get(order_no=order)
        except Order.DoesNotExist:
            order = None
        if order is not None:
            order_no = order.order_no
            try:
                try:
                    order_goods = GoodsOrder.objects.filter(order=order)
                except GoodsOrder.DoesNotExist:
                    order_goods = None

                for goods in order_goods:
                    if goods.issued_status:
                        goods_to_be_updated.append(
                            stock_serializer.GoodsUpdate(
                                goods=goods.goods,
                                updated_by=get_user_model().objects.get(id=data["deleted_by"]),
                                quantity_available=goods.goods.goods_quantity+goods.goods_quantity,
                                quantity_added=goods.goods_quantity,
                                goods_update_reason="deleted_order",
                            )
                        )
                        try:
                            updated_good=Goods.objects.get(id=goods.goods.id)
                            updated_good.goods_quantity=goods.goods.goods_quantity+goods.goods_quantity
                            updated_good.save()
                        except:
                            print('failed to update the goods number')
                        
                    goods_object.append(goods)

                try:
                    # saving an update to stock
                    stock_updates = stock_serializer.GoodsUpdate.objects.bulk_create(
                        goods_to_be_updated
                    )
                    
                    # deleting an order
                    order.delete()
                    # saving deleted order
                    serialized_goods_object = GoodsOrderSerializer(
                        goods_object, many=True
                    ).data

                    serializer = DeletedOrderSerializer(
                        data={
                            "order_no": order_no,
                            "deleted_by": data["deleted_by"],
                            "goods_object": serialized_goods_object,
                        }
                    )
                    if serializer.is_valid():
                        serializer.save()

                    data['delete_response']="Order deleted successfully"
                    return data
                except Exception as e:
                    raise e
            except Exception as e:
                print(e)
        data['delete_response']="Order was not delete, there might be a failure!"
        return data
