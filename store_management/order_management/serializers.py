from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from .models import *
from django.db.models import Sum, F, Q
from django.db import transaction
from datetime import date
from django.utils import timezone
from stock_management import serializers as stock_serializer
from store_management.audit import create_audit_log
from user_management.role_permissions import sync_user_group_permissions


WORKFLOW_ALLOWED_TRANSITIONS = {
    OrderAuthorizationStatus.PENDING: {
        OrderAuthorizationStatus.APPROVED,
        OrderAuthorizationStatus.REJECTED,
        OrderAuthorizationStatus.CANCELLED,
    },
    OrderAuthorizationStatus.APPROVED: {
        OrderAuthorizationStatus.PARTIALLY_PAID,
        OrderAuthorizationStatus.PAID,
        OrderAuthorizationStatus.CANCELLED,
    },
    OrderAuthorizationStatus.PARTIALLY_PAID: {
        OrderAuthorizationStatus.PAID,
        OrderAuthorizationStatus.CANCELLED,
    },
    OrderAuthorizationStatus.PAID: set(),
    OrderAuthorizationStatus.REJECTED: set(),
    OrderAuthorizationStatus.CANCELLED: set(),
}

KNOWN_ORDER_STATUSES = {choice for choice, _label in OrderAuthorizationStatus.choices}


def is_storekeeper_user(user):
    return bool(
        getattr(user, "is_authenticated", False)
        and user.groups.filter(name__iexact="storekeeper").exists()
    )


def get_visible_order_queryset_for_user(user, queryset=None):
    base_queryset = queryset if queryset is not None else Order.objects.all()
    company = getattr(user, "user_company", None)
    if company is None:
        return base_queryset.none()

    scoped = base_queryset.filter(creator__user_company=company).distinct()
    if is_storekeeper_user(user):
        return scoped.filter(order_goods__goods__store__store_supervisor=user).distinct()
    return scoped


def get_visible_goods_order_queryset_for_user(user, queryset=None):
    base_queryset = queryset if queryset is not None else GoodsOrder.objects.all()
    company = getattr(user, "user_company", None)
    if company is None:
        return base_queryset.none()

    scoped = base_queryset.filter(goods__store__company=company).select_related(
        "goods",
        "goods__store",
        "order",
        "issuer",
    )
    if is_storekeeper_user(user):
        return scoped.filter(goods__store__store_supervisor=user)
    return scoped


def calculate_order_total(order):
    order_total = GoodsOrder.objects.filter(order=order).aggregate(
        total=Sum(F("price") * F("goods_quantity"))
    )["total"] or 0
    return float(order_total - order.order_discount)


def calculate_completed_payments(order):
    return float(
        order.payments.filter(status="completed").aggregate(total=Sum("amount"))["total"] or 0
    )


def sync_order_payment_status(order, actor=None):
    total = calculate_order_total(order)
    paid = calculate_completed_payments(order)
    current_status = order.authorization_status or OrderAuthorizationStatus.PENDING

    if paid <= 0:
        if current_status in {OrderAuthorizationStatus.PARTIALLY_PAID, OrderAuthorizationStatus.PAID}:
            order.authorization_status = OrderAuthorizationStatus.APPROVED
            order.paid_at = None
    elif paid < total:
        order.authorization_status = OrderAuthorizationStatus.PARTIALLY_PAID
        order.paid_at = None
    else:
        order.authorization_status = OrderAuthorizationStatus.PAID
        order.paid_at = timezone.now()

    if actor is not None:
        order.authorizer = actor
        order.save(update_fields=["authorization_status", "paid_at", "authorizer"])
    else:
        order.save(update_fields=["authorization_status", "paid_at"])
    return order

class GoodsOrderReadSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """
        Purpose: get order instance
        """
        goods = instance.goods if instance.goods_id else None
        store = goods.store if goods is not None and getattr(goods, "store_id", None) else None
        price = instance.price or 0
        quantity = instance.goods_quantity or 0
        returned_instance = {
            "id": instance.id,
            "goods": goods.id if goods is not None else None,
            "goods_name": goods.goods_name if goods is not None else None,
            "goods_number": goods.goods_number if goods is not None else None,
            "store_name": store.store_name if store is not None else None,
            "goods_quantity": quantity,
            "price": price,
            "issued_status": instance.issued_status,
            "issuer": instance.issuer.username if instance.issuer_id else None,
            "sum_per_goods": price * quantity,
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
    total_amount_paid = serializers.FloatField(read_only=True)
    outstanding_balance = serializers.FloatField(read_only=True)
    creator = serializers.SlugRelatedField(slug_field="username", read_only=True)
    customer_phone = serializers.SerializerMethodField(read_only=True)
    authorization_status = serializers.ChoiceField(
        choices=OrderAuthorizationStatus.choices, required=False
    )
    approval_note = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Order
        fields = "__all__"

    def payable_vat_calc(self, order_total: float):
        return order_total * (18 / 118)

    def get_customer_phone(self, instance):
        if instance.customer_id and instance.customer is not None:
            return str(instance.customer.customer_phone)
        return None

    def _normalize_customer_fields(self, attrs, creator=None):
        customer = attrs.get("customer")
        customer_name = attrs.get("customer_name")
        company = getattr(creator, "user_company", None)

        if customer is not None:
            if company is not None and customer.customer_company_id != company.id:
                raise serializers.ValidationError(
                    {"customer": "Selected customer does not belong to your company."}
                )
            attrs["customer_name"] = customer.customer_username
            return attrs

        if customer_name is None:
            attrs["customer_name"] = None
            return attrs

        normalized_name = str(customer_name).strip()
        attrs["customer_name"] = normalized_name or None
        return attrs

    def validate(self, attrs):
        request = self.context.get("request")
        creator = attrs.get("creator") or getattr(self.instance, "creator", None)
        if creator is None and request is not None:
            creator = request.user

        self._normalize_customer_fields(attrs, creator=creator)

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
        authorization_status = validated_data.pop(
            "authorization_status",
            OrderAuthorizationStatus.PENDING,
        )
        order_goods = validated_data.pop("order_goods", [])
        caption = validated_data.pop("order_caption", None)
        creator = validated_data["creator"]
        customer = validated_data.pop("customer", None)
        customer_name = validated_data.pop("customer_name", None)
        try:
            order_discount = validated_data.pop("order_discount")
        except:
            order_discount = 0.00

        with transaction.atomic():
            order = Order.objects.create(
                creator=creator,
                customer=customer,
                customer_name=customer_name,
                order_caption=caption,
                order_discount=order_discount,
                authorization_status=authorization_status,
            )
            goods_handler = []
            for o_goods in order_goods:
                goods_id = o_goods.pop("goods")
                good = get_object_or_404(Goods, id=goods_id)
                goods_handler.append(GoodsOrder(order=order, goods=good, **o_goods))
            GoodsOrder.objects.bulk_create(goods_handler)
            create_audit_log(
                actor=creator,
                company=creator.user_company,
                action="order.created",
                entity_type="Order",
                entity_id=order.order_no,
                description="Order created",
                payload={"status": order.authorization_status, "items": len(goods_handler)},
            )
        return order

    def update(self, instance, validated_data):
        """
        purpose: Editing order, especially adding new goods and authorization status
        """
        request = self.context.get("request")
        actor = request.user if request else None
        new_goods = validated_data.pop("order_goods", [])
        new_status = validated_data.get("authorization_status", instance.authorization_status)
        approval_note = validated_data.get("approval_note", instance.approval_note)
        current_status_name = instance.authorization_status or OrderAuthorizationStatus.PENDING
        next_status_name = new_status or current_status_name

        with transaction.atomic():
            if new_goods:
                if current_status_name != "pending":
                    raise serializers.ValidationError("Only pending orders can update goods lines.")
                order_goods_details = instance.order_goods
                for item in new_goods:
                    goods = item.get("goods")
                    try:
                        match = order_goods_details.get(goods_id=goods)
                        match.price = item.get("price", match.price)
                        match.goods_quantity = item.get("goods_quantity", match.goods_quantity)
                        match.save()
                    except GoodsOrder.DoesNotExist:
                        good = get_object_or_404(Goods, id=goods)
                        GoodsOrder.objects.create(
                            order=instance,
                            goods=good,
                            goods_quantity=item.get("goods_quantity"),
                            price=item.get("price"),
                        )

            if next_status_name != current_status_name:
                if actor is not None:
                    sync_user_group_permissions(actor)

                if actor and not (
                    actor.has_perm("order_management.add_payment")
                    or actor.has_perm("order_management.change_payment")
                ):
                    raise serializers.ValidationError(
                        {"authorization_status": "Only users with payment permissions can change order approval status."}
                    )
                allowed = WORKFLOW_ALLOWED_TRANSITIONS.get(current_status_name, set())
                if next_status_name not in allowed:
                    raise serializers.ValidationError(
                        {"authorization_status": f"Cannot change order status from {current_status_name} to {next_status_name}."}
                    )
                instance.authorizer = actor
                instance.authorization_status = new_status
                instance.approval_note = approval_note
                if next_status_name == OrderAuthorizationStatus.APPROVED:
                    instance.approved_at = timezone.now()
                    instance.rejected_at = None
                elif next_status_name == OrderAuthorizationStatus.REJECTED:
                    instance.rejected_at = timezone.now()
                elif next_status_name == OrderAuthorizationStatus.PAID:
                    instance.paid_at = timezone.now()

            instance.order_caption = validated_data.get("order_caption", instance.order_caption)
            instance.approval_note = validated_data.get("approval_note", instance.approval_note)
            if "customer" in validated_data:
                instance.customer = validated_data.get("customer")
            elif "customer_name" in validated_data:
                instance.customer = None
            if "customer_name" in validated_data or "customer" in validated_data:
                if instance.customer is not None:
                    instance.customer_name = instance.customer.customer_username
                else:
                    customer_name = validated_data.get("customer_name", instance.customer_name)
                    instance.customer_name = str(customer_name).strip() or None if customer_name is not None else None
            instance.order_discount = validated_data.get("order_discount", instance.order_discount)
            instance.save()

            create_audit_log(
                actor=actor,
                company=actor.user_company if actor else None,
                action="order.updated",
                entity_type="Order",
                entity_id=instance.order_no,
                description="Order updated",
                payload={"status": instance.authorization_status},
            )
        return instance

    def to_representation(self, instance):
        try:
            instance.cash_authorizer = instance.authorizer.username
        except:
            instance.cash_authorizer = None
        try:
            order_total = calculate_order_total(instance)
            if order_total is not None:
                instance.total_amount_paid = calculate_completed_payments(instance)
                instance.outstanding_balance = max(order_total - instance.total_amount_paid, 0)
                instance.total_order_amount = {
                    "order_total": order_total,
                    "VAT": round(self.payable_vat_calc(order_total=order_total), 2),
                }
        except Exception as error:
            raise error
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user is not None and is_storekeeper_user(user):
            allowed_ids = set(
                instance.order_goods.filter(goods__store__store_supervisor=user).values_list("id", flat=True)
            )
            data["order_goods_details"] = [
                line for line in data.get("order_goods_details", []) if line.get("id") in allowed_ids
            ]
        return data


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
        request = self.context.get("request")
        actor = getattr(request, "user", None)
        if actor is not None and is_storekeeper_user(actor):
            if instance.goods.store.store_supervisor_id != actor.id:
                raise PermissionDenied("You can only issue goods for your assigned store.")

        # Extract goods_issue data from validated_data
        goods_issue_data = validated_data.pop('goods_issue', None)
        status_changed = False
        if goods_issue_data:
            issuer = self.instance.issuer if self.instance.issuer is not None else actor
            
            # Get issued_status from goods_issue_data or use the current instance's value
            issued_status = goods_issue_data.get('issued_status', instance.issued_status)
            status_changed = bool(instance.issued_status) != bool(issued_status)
            if status_changed:
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
                
                # Serialize stock update data and save it
                stock_data = {'updated_by':instance.issuer.id,'goods': instance.goods.id, 'quantity_added': quantity,'goods_update_reason':'issued_order'}
                stock_serial = stock_serializer.UpdateStockSerializer(data=stock_data)
                
                if stock_serial.is_valid():
                    stock_serial.save(authorized_by=instance.issuer)

                instance.save()
                # Update order issued status based on all items' issued_status in the order
                order = instance.order
                order.issued_status = all(item.issued_status for item in order.order_goods.all())
                order.save()
                create_audit_log(
                    actor=issuer,
                    company=issuer.user_company if issuer else None,
                    action="order_item.issued",
                    entity_type="GoodsOrder",
                    entity_id=instance.id,
                    description="Order item issuance state updated",
                    payload={"issued_status": instance.issued_status, "goods_quantity": instance.goods_quantity},
                )

        # Price and quantity edits arrive inside goods_issue. Quantity only changes
        # while the order is still pending and this line has not been issued.
        editable_line = (
            not instance.issued_status
            and instance.order.authorization_status == OrderAuthorizationStatus.PENDING
        )
        if editable_line and goods_issue_data and not status_changed:
            if goods_issue_data.get("goods_quantity") is not None:
                instance.goods_quantity = goods_issue_data.get("goods_quantity")
            if goods_issue_data.get("price") is not None:
                instance.price = goods_issue_data.get("price")
        elif (
            not instance.issued_status
            and instance.order.authorization_status != OrderAuthorizationStatus.PAID
        ):
            instance.price = validated_data.get("price", instance.price)

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

                    deleted_by_user = get_user_model().objects.get(id=data["deleted_by"])
                    create_audit_log(
                        actor=deleted_by_user,
                        company=deleted_by_user.user_company,
                        action="order.deleted",
                        entity_type="Order",
                        entity_id=order_no,
                        description="Order deleted",
                        payload={"goods_count": len(goods_object)},
                    )

                    data['delete_response']="Order deleted successfully"
                    return data
                except Exception as e:
                    raise e
            except Exception as e:
                print(e)
        data['delete_response']="Order was not delete, there might be a failure!"
        return data


class PaymentSerializer(serializers.ModelSerializer):
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())
    recorded_by = serializers.SlugRelatedField(slug_field="username", read_only=True)
    approved_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = ["recorded_by", "approved_by", "paid_at", "date_added"]

    def validate(self, attrs):
        request = self.context.get("request")
        company = request.user.user_company if request else None
        order = attrs["order"]
        status = attrs.get("status", "completed")
        amount = attrs["amount"]

        if amount <= 0:
            raise serializers.ValidationError({"amount": "Payment amount must be greater than zero."})

        if company and order.creator.user_company_id != company.id:
            raise serializers.ValidationError({"order": "This order does not belong to your company."})

        if order.authorization_status in {
            OrderAuthorizationStatus.REJECTED,
            OrderAuthorizationStatus.CANCELLED,
        }:
            raise serializers.ValidationError({"order": "Payments cannot be recorded for rejected or cancelled orders."})

        if status == "completed":
            existing_paid = calculate_completed_payments(order)
            total = calculate_order_total(order)
            if existing_paid + amount > total:
                raise serializers.ValidationError({"amount": "Payment exceeds the order balance."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        actor = request.user if request else None
        status = validated_data.get("status", "completed")

        with transaction.atomic():
            payment = Payment.objects.create(
                recorded_by=actor,
                approved_by=actor if status == "completed" else None,
                paid_at=timezone.now() if status == "completed" else None,
                **validated_data,
            )
            if payment.status == "completed":
                sync_order_payment_status(payment.order, actor=actor)

            create_audit_log(
                actor=actor,
                company=actor.user_company if actor else None,
                action="payment.created",
                entity_type="Payment",
                entity_id=payment.id,
                description="Payment recorded",
                payload={"order_no": payment.order_id, "amount": payment.amount, "method": payment.method, "status": payment.status},
            )

        return payment


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.SlugRelatedField(slug_field="username", read_only=True)
    company = serializers.SlugRelatedField(slug_field="company_name", read_only=True)

    class Meta:
        model = AuditLog
        fields = "__all__"
