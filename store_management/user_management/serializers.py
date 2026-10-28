from django.db import transaction
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, F
from django.utils import timezone
from rest_framework import serializers
from .models import Company, AppUser, Subscription, Customer, SubscriptionType
from django.contrib.auth import authenticate, login, models, get_user_model
from rest_framework.response import Response
from .role_permissions import get_or_create_configured_group, sync_user_group_permissions


def _get_group_names(user):
    if not getattr(user, "is_authenticated", False):
        return set()

    return {name.lower() for name in user.groups.values_list("name", flat=True)}


def _get_direct_user_permissions(user):
    if not getattr(user, "is_authenticated", False):
        return set()

    return {
        f"{permission.content_type.app_label}.{permission.codename}"
        for permission in user.user_permissions.select_related("content_type").all()
    }


def _get_group_permissions(user):
    if not getattr(user, "is_authenticated", False):
        return set()

    sync_user_group_permissions(user)
    return set(user.get_group_permissions())


def _get_all_effective_permissions(user):
    if not getattr(user, "is_authenticated", False):
        return set()

    return _get_direct_user_permissions(user) | _get_group_permissions(user)


def _get_role_permission_flags(user):
    permission_values = _get_all_effective_permissions(user)

    def has_any(*permission_names):
        return any(permission_name in permission_values for permission_name in permission_names)

    can_manage_users = has_any(
        "user_management.add_appuser",
        "user_management.change_appuser",
        "user_management.delete_appuser",
        "user_management.view_appuser",
    )
    can_manage_goods_types = has_any(
        "stock_management.add_goodstype",
        "stock_management.change_goodstype",
        "stock_management.delete_goodstype",
        "stock_management.view_goodstype",
        "stock_management.add_categories",
        "stock_management.change_categories",
        "stock_management.delete_categories",
        "stock_management.view_categories",
    )
    can_manage_suppliers = has_any(
        "stock_management.add_supplier",
        "stock_management.change_supplier",
        "stock_management.delete_supplier",
        "stock_management.view_supplier",
    )
    can_manage_purchase_orders = has_any(
        "stock_management.add_purchaseorder",
        "stock_management.change_purchaseorder",
        "stock_management.delete_purchaseorder",
        "stock_management.view_purchaseorder",
    )
    can_manage_stores = has_any(
        "stock_management.add_store",
        "stock_management.change_store",
        "stock_management.delete_store",
        "stock_management.view_store",
    )
    can_view_audit_logs = has_any("order_management.view_auditlog")
    can_manage_inventory = has_any(
        "stock_management.add_goods",
        "stock_management.change_goods",
        "stock_management.delete_goods",
        "stock_management.view_goods",
        "stock_management.add_goodsupdate",
        "stock_management.change_goodsupdate",
        "stock_management.delete_goodsupdate",
        "stock_management.view_goodsupdate",
        "stock_management.add_leakage",
        "stock_management.change_leakage",
        "stock_management.delete_leakage",
        "stock_management.view_leakage",
    )
    can_manage_stock_returns = has_any(
        "stock_management.add_salesreturn",
        "stock_management.change_salesreturn",
        "stock_management.delete_salesreturn",
        "stock_management.view_salesreturn",
    )
    can_manage_stock_transfers = has_any(
        "stock_management.add_stocktransfer",
        "stock_management.change_stocktransfer",
        "stock_management.delete_stocktransfer",
        "stock_management.view_stocktransfer",
    )
    can_create_orders = has_any(
        "order_management.add_order",
        "order_management.change_order",
        "order_management.delete_order",
        "order_management.view_order",
    )
    can_manage_payments = has_any(
        "order_management.add_payment",
        "order_management.change_payment",
        "order_management.delete_payment",
        "order_management.view_payment",
    )
    is_shop_owner = all(
        (
            can_manage_users,
            can_manage_goods_types,
            can_manage_suppliers,
            can_manage_purchase_orders,
            can_manage_stores,
            can_view_audit_logs,
        )
    )
    is_cashier = can_manage_payments
    is_storekeeper = can_manage_inventory or can_manage_stock_returns or can_manage_stock_transfers
    is_salesperson = can_create_orders

    return {
        "is_shop_owner": is_shop_owner,
        "is_cashier": is_cashier,
        "is_storekeeper": is_storekeeper,
        "is_salesperson": is_salesperson,
        "can_manage_users": can_manage_users,
        "can_manage_goods_types": can_manage_goods_types,
        "can_manage_suppliers": can_manage_suppliers,
        "can_manage_purchase_orders": can_manage_purchase_orders,
        "can_verify_purchase_orders": can_manage_purchase_orders,
        "can_manage_stores": can_manage_stores,
        "can_view_audit_logs": can_view_audit_logs,
        "can_view_dashboard": is_shop_owner,
        "can_manage_inventory": can_manage_inventory,
        "can_manage_stock_returns": can_manage_stock_returns,
        "can_manage_stock_transfers": can_manage_stock_transfers,
        "can_create_orders": can_create_orders,
        "can_manage_payments": can_manage_payments,
    }


class PermissionFieldsMixin:
    def get_permissions(self, instance):
        return sorted(_get_all_effective_permissions(instance))

    def get_all_permissions(self, instance):
        return sorted(_get_all_effective_permissions(instance))

    def get_user_permissions(self, instance):
        return sorted(_get_direct_user_permissions(instance))

    def get_group_permissions(self, instance):
        return sorted(_get_group_permissions(instance))

    def get_role_permissions(self, instance):
        return _get_role_permission_flags(instance)


class CompanyUserListingField(serializers.Serializer):
    def to_representation(self, user_company):
        """
        Purpose: This displays company and their owners.
        """
        company_owner = AppUser.objects.values('id','first_name','last_name','username').get(id=user_company.id)
        return company_owner
    # end def


class UserGroupField(serializers.Serializer):
    def to_representation(self, instance):
        groups = Group.objects.values('name').get(id=instance.id)
        return groups


class SubscriptionSerializer(serializers.ModelSerializer):
    status = serializers.BooleanField(read_only=True)
    type = serializers.SlugRelatedField(
        queryset=SubscriptionType.objects.filter(is_active=True),
        slug_field="code",
    )

    class Meta:
        model = Subscription
        fields = '__all__'
        read_only_fields = ("status",)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        company = attrs.get("company") or getattr(self.instance, "company", None)
        date_activated = attrs.get("date_activated", getattr(self.instance, "date_activated", None))
        expire_date = attrs.get("expire_date", getattr(self.instance, "expire_date", None))
        subscription_type = attrs.get("type", getattr(self.instance, "type", None))

        if request and getattr(request.user, "is_authenticated", False) and not request.user.is_superuser:
            user_company = getattr(request.user, "user_company", None)
            if user_company is None:
                raise serializers.ValidationError({"company": "Authenticated user is not assigned to a company."})
            if company and company.pk != user_company.pk:
                raise serializers.ValidationError({"company": "You can only manage subscriptions for your company."})

        candidate = Subscription(
            company=company,
            type=subscription_type,
            date_activated=date_activated,
            expire_date=expire_date,
        )
        if self.instance is not None:
            candidate.pk = self.instance.pk

        try:
            candidate.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc

        return attrs


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'
        
    def create(self, validated_data):
        customer_username = validated_data.get("customer_username").title()
        customer_phone = validated_data.get("customer_phone")
        customer_company = validated_data.get("customer_company")
        
        customer = Customer(
            customer_username=customer_username, 
            customer_phone=customer_phone, 
            customer_company=customer_company
            )
        
        if customer:
            customer.save()
        
        return customer
        


class CompanySerializer(serializers.ModelSerializer):
    owner = serializers.JSONField(write_only=True, required=True)
    class Meta:
        model = Company
        fields = '__all__'
    
    def validate(self, attrs):
        owner = attrs.get("owner")
        if not isinstance(owner, dict):
            raise serializers.ValidationError({"owner": "Owner details are required."})

        required_owner_fields = ("username", "first_name", "last_name", "phone_number", "password")
        missing_fields = [field for field in required_owner_fields if not str(owner.get(field, "")).strip()]
        if missing_fields:
            raise serializers.ValidationError({
                "owner": {field: "This field is required." for field in missing_fields}
            })

        username = owner["username"].strip()
        
        if AppUser.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("the username already exist, try another username")
        
        if Company.objects.filter(
            company_name__iexact=attrs["company_name"].strip(),
            company_location__iexact=attrs["company_location"].strip(),
            company_tin=attrs.get("company_tin"),
        ).exists():
            raise serializers.ValidationError("the company already exist")
        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        """
        A method to create company along with creating subscription and company owner for the
        first time.
        """
        owner = validated_data.pop("owner")
        company = Company.objects.create(**validated_data)
        
        # Create the initial subscription from the admin-managed default plan.
        today = timezone.localdate()
        default_subscription_type = (
            SubscriptionType.objects.filter(is_default=True, is_active=True).first()
            or SubscriptionType.objects.filter(code="TRIAL", is_active=True).first()
            or SubscriptionType.objects.filter(code="STANDARD", is_active=True).first()
            or SubscriptionType.objects.filter(is_active=True).order_by("name").first()
        )

        if default_subscription_type is None:
            raise serializers.ValidationError({
                "subscription": "Create and activate at least one subscription type in admin."
            })

        expire_date = today + timezone.timedelta(days=default_subscription_type.duration_days)

        Subscription.objects.create(
            type=default_subscription_type,
            date_activated=today,
            expire_date=expire_date,
            company=company,
        )

        shop_owner = AppUser.objects.create_user(
            username=owner["username"].strip(),
            password=owner["password"],
            first_name=owner["first_name"].strip(),
            last_name=owner["last_name"].strip(),
            phone_number=owner["phone_number"].strip(),
            email=owner.get("email"),
            user_company=company,
        )
        shop_owner.groups.add(get_or_create_configured_group("shopowner"))
        return company


class UserSerializer(PermissionFieldsMixin, serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    user_company = serializers.SlugRelatedField(queryset=Company.objects.all(),slug_field="company_name")
    groups = serializers.StringRelatedField(many=True, read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)
    all_permissions = serializers.SerializerMethodField(read_only=True)
    user_permissions = serializers.SerializerMethodField(read_only=True)
    group_permissions = serializers.SerializerMethodField(read_only=True)
    role_permissions = serializers.SerializerMethodField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    user_groups = serializers.JSONField(write_only=True)
    password = serializers.CharField(
        style={'input_type':'password'},
        write_only=True
    )

    class Meta:
        model = AppUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "user_company",
            "groups",
            "permissions",
            "all_permissions",
            "user_permissions",
            "group_permissions",
            "role_permissions",
            "is_superuser",
            "is_staff",
            "password",
            "user_groups",
        ]
    
    def create(self, validated_data):
        user_group = validated_data.pop("user_groups")
        password = validated_data.pop('password')
        username = validated_data.pop('username').strip()
        
        if AppUser.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({"username": "User with similar username Exist"})
        
        user = AppUser.objects.create_user(username=username, password=password, **validated_data)
        if user_group is not None:
            for userrole in user_group:
                try:
                    group = get_or_create_configured_group(userrole)
                except Group.DoesNotExist():
                    raise serializers.ValidationError("you provide the unknown group")
                user.groups.add(group)
        return user
    
    
    def update(self, instance, validated_data):
        validated_data = validated_data['user']
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.email = validated_data.get('email', instance.email)
        instance.phone_number = validated_data.get('phone_number', instance.phone_number)
        instance.save()
        return instance
        
        
class ChangePasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=150, min_length=8)
    password2 = serializers.CharField(write_only=True, max_length=150, min_length=8)
    old_password = serializers.CharField(write_only=True, max_length=150, min_length=8)
    
    class Meta:
        model = AppUser
        fields = '__all__'
        read_only_fields = ["username", "first_name", "last_name", "phone_number"]

        
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password":"you entered unmatched password"})
        return attrs
    
    def validate_old_password(self, value):
        #user = self.context['request'].user, now only the userId passed on Url is enough and important for changing the password
        userId = int(self.context['request']._request.path.split('/')[-2])
        print(userId)
        user=AppUser.objects.get(id=userId)
        print(user)
        if not user.check_password(value):
            raise serializers.ValidationError({"old password":"you entered wrong old password"})
        return value
    
    def update(self, instance, validated_data):
        instance.set_password(validated_data['password'])
        instance.save()
        return instance

class GroupSerializer(serializers.Serializer):
    def to_representation(self, instance):
        instance=Group.objects.values('name').get(id=instance.id)
        return instance

class LoginSerializer(PermissionFieldsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username=serializers.CharField(max_length=150)
    password=serializers.CharField(style={'input_type':'password'},trim_whitespace=False,write_only=True)
    first_name=serializers.CharField(read_only=True,max_length=150)
    last_name=serializers.CharField(read_only=True,max_length=150)
    phone_number=serializers.CharField(read_only=True,max_length=150)
    is_superuser = serializers.BooleanField(read_only=True)
    is_staff = serializers.BooleanField(read_only=True)
    groups = UserGroupField(many=True, read_only=True)
    user_company=CompanySerializer(read_only=True)
    permissions = serializers.SerializerMethodField(read_only=True)
    all_permissions = serializers.SerializerMethodField(read_only=True)
    user_permissions = serializers.SerializerMethodField(read_only=True)
    group_permissions = serializers.SerializerMethodField(read_only=True)
    role_permissions = serializers.SerializerMethodField(read_only=True)
    
    def validate(self,attrs):
        username = attrs.get('username', '').strip()
        password =attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidatorError('Provide both username and password')
        
        user_instance = AppUser.objects.filter(username__iexact=username).first()
        if not user_instance:
            raise serializers.ValidationError('User does not exist')
        user = authenticate(
            request=self.context.get('request'),
            username=user_instance.username,
            password=password,
        )
        
        if not user:
            raise serializers.ValidationError('Wrong credentials')
        attrs['user']=user
        
        return attrs
