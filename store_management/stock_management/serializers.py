import csv
import io
from datetime import datetime
from rest_framework import serializers
from .models import *
from django.db.models import F, Q,Sum
from order_management.models import Order, GoodsOrder
from order_management import serializers as order_serializers
from user_management.models import Company
from django.db import transaction
from django.utils import timezone
from store_management.audit import create_audit_log

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
        company_name = str(validated_data.pop('company')).strip()
        store_supervisor = str(validated_data.pop('store_supervisor')).strip()
        try:
            supervisor = get_user_model().objects.get(username__iexact=store_supervisor)
        except get_user_model().DoesNotExist as exc:
            raise serializers.ValidationError(
                {"store_supervisor": "Selected supervisor does not exist."}
            ) from exc
        
        try:
            company = Company.objects.get(company_name__iexact=company_name)
        except Company.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"company": "Selected company does not exist."}
            ) from exc
        
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
        store_supervisor = validated_data.get("store_supervisor")
        if store_supervisor is not None:
            store_supervisor = str(store_supervisor).strip()
            if store_supervisor:
                try:
                    supervisor = get_user_model().objects.get(username__iexact=store_supervisor)
                except get_user_model().DoesNotExist as exc:
                    raise serializers.ValidationError(
                        {"store_supervisor": "Selected supervisor does not exist."}
                    ) from exc
                instance.store_supervisor = supervisor
        instance.save()
        return instance


class SupplierSerializer(serializers.ModelSerializer):
    company = serializers.SlugRelatedField(slug_field="company_name", read_only=True)
    added_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Supplier
        fields = "__all__"


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    line_total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = "__all__"
        read_only_fields = ["purchase_order", "date_added"]

    def get_line_total(self, obj):
        return obj.quantity * obj.unit_cost


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    items = PurchaseOrderItemSerializer(many=True, required=False)
    created_by = serializers.SlugRelatedField(slug_field="username", read_only=True)
    authorized_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = "__all__"
        read_only_fields = ["created_by", "authorized_by", "received_at", "date_added"]

    def validate(self, attrs):
        request = self.context.get("request")
        company = request.user.user_company if request else None

        supplier = attrs.get("supplier", getattr(self.instance, "supplier", None))
        store = attrs.get("store", getattr(self.instance, "store", None))
        items = attrs.get("items")

        if supplier and company and supplier.company_id != company.id:
            raise serializers.ValidationError({"supplier": "The supplier does not belong to your company."})

        if store and company and store.company_id != company.id:
            raise serializers.ValidationError({"store": "The destination store does not belong to your company."})

        if items is None and self.instance is None:
            raise serializers.ValidationError({"items": "At least one purchase order item is required."})

        if items is not None:
            if not items:
                raise serializers.ValidationError({"items": "At least one purchase order item is required."})

            seen_goods = set()
            for item in items:
                goods = item["goods"]
                if store and goods.store_id != store.id:
                    raise serializers.ValidationError(
                        {"items": f"Goods {goods.id} must belong to the selected destination store."}
                    )
                if company and goods.store.company_id != company.id:
                    raise serializers.ValidationError(
                        {"items": f"Goods {goods.id} does not belong to your company."}
                    )
                if goods.id in seen_goods:
                    raise serializers.ValidationError({"items": "Duplicate goods entries are not allowed."})
                seen_goods.add(goods.id)

        return attrs

    def _apply_receipt(self, purchase_order, acting_user):
        if purchase_order.status == "received" and purchase_order.received_at is not None:
            return purchase_order

        for item in purchase_order.items.select_related("goods").all():
            goods = Goods.objects.select_for_update().get(id=item.goods_id)
            quantity_available = goods.goods_quantity
            goods.goods_quantity = quantity_available + item.quantity
            goods.buying_price = item.unit_cost
            goods.save()
            GoodsUpdate.objects.create(
                goods=goods,
                updated_by=acting_user,
                authorized_by=acting_user,
                quantity_available=quantity_available,
                quantity_added=item.quantity,
                goods_update_reason="purchase_order_receipt",
            )

        purchase_order.status = "received"
        purchase_order.authorized_by = acting_user
        purchase_order.received_at = timezone.now()
        purchase_order.save(update_fields=["status", "authorized_by", "received_at"])
        return purchase_order

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        request = self.context.get("request")
        acting_user = request.user if request else None
        requested_status = validated_data.get("status", "draft")

        with transaction.atomic():
            purchase_order = PurchaseOrder.objects.create(
                created_by=acting_user,
                **validated_data,
            )
            PurchaseOrderItem.objects.bulk_create(
                [PurchaseOrderItem(purchase_order=purchase_order, **item) for item in items_data]
            )

            if requested_status == "received":
                self._apply_receipt(purchase_order, acting_user)

            create_audit_log(
                actor=acting_user,
                company=acting_user.user_company if acting_user else None,
                action="purchase_order.created",
                entity_type="PurchaseOrder",
                entity_id=purchase_order.id,
                description="Purchase order created",
                payload={"status": purchase_order.status, "item_count": len(items_data)},
            )

        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        request = self.context.get("request")
        acting_user = request.user if request else None
        new_status = validated_data.get("status", instance.status)

        if instance.status == "received" and new_status != "received":
            raise serializers.ValidationError({"status": "A received purchase order cannot change status."})

        with transaction.atomic():
            if items_data is not None:
                if instance.status != "draft":
                    raise serializers.ValidationError({"items": "Only draft purchase orders can update items."})
                instance.items.all().delete()
                PurchaseOrderItem.objects.bulk_create(
                    [PurchaseOrderItem(purchase_order=instance, **item) for item in items_data]
                )

            instance.supplier = validated_data.get("supplier", instance.supplier)
            instance.store = validated_data.get("store", instance.store)
            instance.notes = validated_data.get("notes", instance.notes)
            instance.status = new_status
            instance.save()

            if instance.status == "received" and instance.received_at is None:
                self._apply_receipt(instance, acting_user)

            create_audit_log(
                actor=acting_user,
                company=acting_user.user_company if acting_user else None,
                action="purchase_order.updated",
                entity_type="PurchaseOrder",
                entity_id=instance.id,
                description="Purchase order updated",
                payload={"status": instance.status},
            )

        return instance


class LeakageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leakage
        fields = "__all__"
        read_only_fields = ['added_by']
    
    def validate(self, attrs):
        request = self.context.get("request")
        amount_broken = attrs.get("amount_broken")
        goods = attrs.get("goods")

        if request and goods and goods.store.company_id != request.user.user_company_id:
            raise serializers.ValidationError(
                {"goods": "This goods item does not belong to your company."}
            )

        goods_data = GoodsSerializer(goods).data
        goods_available = goods_data.get("goods_available_for_sales", 0)
        
        if amount_broken > goods_available:
            raise serializers.ValidationError(
                {"amount_broken": "The amount is higher than the available goods."}
            )
        return attrs
    
    def create(self, validated_data):
        goods = validated_data.get("goods")
        amount_broken = validated_data.get("amount_broken")
        
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
    

class CompanyScopedGoodsTypeField(serializers.SlugRelatedField):
    def get_queryset(self):
        queryset = GoodsType.objects.all()
        request = self.context.get("request")

        if not request or not getattr(request.user, "is_authenticated", False):
            return queryset.none()

        return queryset.filter(company=request.user.user_company)


class GoodsSerializer(serializers.ModelSerializer):
    broken=LeakageSerializer(many=True,read_only=True)
    store_details = StoreSerializer(read_only=True, source='store')
    goods_type = CompanyScopedGoodsTypeField(slug_field='goods_type', queryset=GoodsType.objects.all())
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

    def validate(self, attrs):
        request = self.context.get("request")
        company = request.user.user_company if request else None
        goods_type = attrs.get("goods_type", getattr(self.instance, "goods_type", None))
        store = attrs.get("store", getattr(self.instance, "store", None))

        if company and store and store.company_id != company.id:
            raise serializers.ValidationError({"store": "This store does not belong to your company."})

        if company and goods_type and goods_type.company_id != company.id:
            raise serializers.ValidationError({"goods_type": "This goods type does not belong to your company."})

        return attrs
      
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
        

class BulkGoodsUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)

    required_columns = (
        "goods_name",
        "goods_number",
        "goods_quantity",
        "goods_type",
        "buying_price",
        "lower_price_margin",
        "store",
        "restricted_price",
        "alert_on_goods_quantity",
    )

    def validate(self, attrs):
        upload = attrs["file"]

        try:
            decoded_file = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise serializers.ValidationError({"file": "Upload a UTF-8 encoded CSV file."}) from exc

        reader = csv.DictReader(io.StringIO(decoded_file))
        if reader.fieldnames is None:
            raise serializers.ValidationError({"file": "The uploaded CSV file is missing a header row."})

        fieldnames = [field.strip() for field in reader.fieldnames]
        missing_columns = [column for column in self.required_columns if column not in fieldnames]
        if missing_columns:
            raise serializers.ValidationError(
                {"file": f"Missing required columns: {', '.join(missing_columns)}."}
            )

        rows = []
        duplicate_keys = set()
        seen_keys = set()

        for row_number, row in enumerate(reader, start=2):
            normalized_row = {
                column: (row.get(column) or "").strip()
                for column in self.required_columns
            }

            if not any(normalized_row.values()):
                continue

            row_key = (
                normalized_row["goods_number"].lower(),
                normalized_row["store"].lower(),
            )
            if row_key in seen_keys:
                duplicate_keys.add(
                    f"row {row_number}: goods_number '{normalized_row['goods_number']}' for store '{normalized_row['store']}'"
                )
            seen_keys.add(row_key)
            rows.append(normalized_row)

        if duplicate_keys:
            raise serializers.ValidationError(
                {"file": f"Duplicate goods entries found in the upload: {', '.join(sorted(duplicate_keys))}."}
            )

        if not rows:
            raise serializers.ValidationError({"file": "The uploaded CSV file does not contain any stock rows."})

        attrs["rows"] = rows
        return attrs

    def create(self, validated_data):
        request = self.context["request"]
        rows = validated_data["rows"]
        goods_serializer = GoodsSerializer(data=rows, many=True, context=self.context)

        if not goods_serializer.is_valid():
            row_errors = [
                {"row": row_number, "errors": errors}
                for row_number, errors in enumerate(goods_serializer.errors, start=2)
                if errors
            ]
            raise serializers.ValidationError({"rows": row_errors})

        with transaction.atomic():
            goods_records = goods_serializer.save(added_by=request.user)
            create_audit_log(
                actor=request.user,
                company=request.user.user_company,
                action="goods.bulk_upload",
                entity_type="Goods",
                entity_id=f"bulk:{len(goods_records)}",
                description="Bulk goods upload completed",
                payload={"count": len(goods_records)},
            )

        return {
            "count": len(goods_records),
            "status": 200,
            "result": GoodsSerializer(goods_records, many=True, context=self.context).data,
        }
        

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


class CategoriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categories
        fields = ["id", "category_name", "date_added"]


class CategoryObjectField(serializers.PrimaryKeyRelatedField):
    def use_pk_only_optimization(self):
        return False

    def to_representation(self, value):
        return CategoriesSerializer(value).data


class GoodsTypeSerializer(serializers.ModelSerializer):
    goods_and_type=GoodsSerializer(many=True,read_only=True)
    company = serializers.SlugRelatedField(slug_field="company_name", read_only=True)
    categories = CategoryObjectField(
        queryset=Categories.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model=GoodsType
        fields='__all__'

    def validate_goods_type(self, value):
        request = self.context.get("request")
        company = request.user.user_company if request else getattr(self.instance, "company", None)
        value = value.strip()

        if not company:
            return value

        queryset = GoodsType.objects.filter(company=company, goods_type__iexact=value)
        if self.instance is not None:
            queryset = queryset.exclude(id=self.instance.id)

        if queryset.exists():
            raise serializers.ValidationError("This goods type already exists for your company.")

        return value
        

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


class SalesReturnSerializer(serializers.ModelSerializer):
    goods_order = serializers.PrimaryKeyRelatedField(queryset=GoodsOrder.objects.all())
    returned_by = serializers.SlugRelatedField(slug_field="username", read_only=True)
    authorized_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = SalesReturn
        fields = "__all__"
        read_only_fields = ["returned_by", "authorized_by", "date_added"]

    def validate(self, attrs):
        request = self.context.get("request")
        company = request.user.user_company if request else None
        goods_order = attrs["goods_order"]
        returned_quantity = attrs["returned_quantity"]

        if company and goods_order.goods.store.company_id != company.id:
            raise serializers.ValidationError({"goods_order": "This order item does not belong to your company."})

        if not goods_order.issued_status:
            raise serializers.ValidationError({"goods_order": "Only issued order items can be returned."})

        previous_returns = goods_order.sales_returns.aggregate(total=Sum("returned_quantity"))["total"] or 0
        if previous_returns + returned_quantity > goods_order.goods_quantity:
            raise serializers.ValidationError({"returned_quantity": "Return quantity exceeds the sold quantity."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        acting_user = request.user if request else None
        goods_order = validated_data["goods_order"]
        returned_quantity = validated_data["returned_quantity"]

        with transaction.atomic():
            goods = Goods.objects.select_for_update().get(id=goods_order.goods_id)
            quantity_available = goods.goods_quantity
            goods.goods_quantity = quantity_available + returned_quantity
            goods.save()

            sales_return = SalesReturn.objects.create(
                returned_by=acting_user,
                authorized_by=acting_user,
                **validated_data,
            )

            GoodsUpdate.objects.create(
                goods=goods,
                updated_by=acting_user,
                authorized_by=acting_user,
                quantity_available=quantity_available,
                quantity_added=returned_quantity,
                goods_update_reason="sales_return",
            )

            create_audit_log(
                actor=acting_user,
                company=acting_user.user_company if acting_user else None,
                action="sales_return.created",
                entity_type="SalesReturn",
                entity_id=sales_return.id,
                description="Sales return created",
                payload={"goods_order": goods_order.id, "returned_quantity": returned_quantity},
            )

        return sales_return


class StockTransferSerializer(serializers.ModelSerializer):
    goods = serializers.PrimaryKeyRelatedField(queryset=Goods.objects.all())
    from_store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    to_store = serializers.PrimaryKeyRelatedField(queryset=Store.objects.all())
    transferred_by = serializers.SlugRelatedField(slug_field="username", read_only=True)
    authorized_by = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = StockTransfer
        fields = "__all__"
        read_only_fields = ["transferred_by", "authorized_by", "status", "date_added"]

    def validate(self, attrs):
        request = self.context.get("request")
        company = request.user.user_company if request else None
        goods = attrs["goods"]
        from_store = attrs["from_store"]
        to_store = attrs["to_store"]
        quantity = attrs["quantity"]

        if from_store.id == to_store.id:
            raise serializers.ValidationError({"to_store": "Transfer destination must be different from source store."})

        if goods.store_id != from_store.id:
            raise serializers.ValidationError({"goods": "Selected goods must belong to the source store."})

        if company:
            if from_store.company_id != company.id or to_store.company_id != company.id:
                raise serializers.ValidationError({"store": "Both stores must belong to your company."})

        if quantity > goods.goods_quantity:
            raise serializers.ValidationError({"quantity": "Transfer quantity exceeds available stock."})

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        acting_user = request.user if request else None
        quantity = validated_data["quantity"]
        from_store = validated_data["from_store"]
        to_store = validated_data["to_store"]
        goods = validated_data["goods"]

        with transaction.atomic():
            source_goods = Goods.objects.select_for_update().get(id=goods.id)
            quantity_available = source_goods.goods_quantity
            source_goods.goods_quantity = quantity_available - quantity
            source_goods.save()

            GoodsUpdate.objects.create(
                goods=source_goods,
                updated_by=acting_user,
                authorized_by=acting_user,
                quantity_available=quantity_available,
                quantity_added=-quantity,
                goods_update_reason="store_transfer_out",
            )

            target_goods = Goods.objects.select_for_update().filter(
                store=to_store,
                goods_number=source_goods.goods_number,
            ).first()
            if target_goods is None:
                target_goods = Goods.objects.create(
                    goods_name=source_goods.goods_name,
                    goods_number=source_goods.goods_number,
                    goods_quantity=0,
                    goods_type=source_goods.goods_type,
                    buying_price=source_goods.buying_price,
                    lower_price_margin=source_goods.lower_price_margin,
                    store=to_store,
                    added_by=acting_user,
                    restricted_price=source_goods.restricted_price,
                    alert_on_goods_quantity=source_goods.alert_on_goods_quantity,
                )

            target_available = target_goods.goods_quantity
            target_goods.goods_quantity = target_available + quantity
            target_goods.save()

            GoodsUpdate.objects.create(
                goods=target_goods,
                updated_by=acting_user,
                authorized_by=acting_user,
                quantity_available=target_available,
                quantity_added=quantity,
                goods_update_reason="store_transfer_in",
            )

            stock_transfer = StockTransfer.objects.create(
                transferred_by=acting_user,
                authorized_by=acting_user,
                status="completed",
                **validated_data,
            )

            create_audit_log(
                actor=acting_user,
                company=acting_user.user_company if acting_user else None,
                action="stock_transfer.created",
                entity_type="StockTransfer",
                entity_id=stock_transfer.id,
                description="Stock transferred between stores",
                payload={"goods": source_goods.id, "from_store": from_store.id, "to_store": to_store.id, "quantity": quantity},
            )

        return stock_transfer
    

class GoodsDeleteByUserSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()

    def delete_goods(self):
        user_id = self.validated_data.get('user_id')
        user=get_user_model().objects.get(id=user_id)
        goods_deleted = Goods.objects.filter(added_by=user).delete()
        return goods_deleted
