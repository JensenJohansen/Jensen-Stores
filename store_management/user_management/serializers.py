from django.contrib.auth.models import Group
from django.db.models import Q, F
from rest_framework import serializers
from .models import Company, AppUser, Subscription, Customer
from django.contrib.auth import authenticate, login, models, get_user_model
from rest_framework.response import Response
import datetime


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
    class Meta:
        model = Subscription
        fields = '__all__'


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
    owner = serializers.JSONField(write_only=True, required=False)
    class Meta:
        model = Company
        fields = '__all__'
    
    def validate(self, attrs):
        owner = attrs.get("owner")
        username = owner["username"]
        
        if AppUser.objects.filter(username=username.title()).exists():
            raise serializers.ValidationError("the username already exist, try another username")
        
        if Company.objects.filter(company_name=attrs['company_name']).exists():
            raise serializers.ValidationError('the company name already exist')
        return attrs
    
    def create(self, validated_data):
        """
        A method to create company along with creating subscription and company owner for the
        first time.
        """
        owner = validated_data.pop("owner")
        owner['user_groups'] = ["shopowner"]
        company = Company.objects.create(**validated_data)
        owner['user_company'] = company
        
        #creating a free 7days subscription for the company
        today = datetime.date.today()
        free_days = today + datetime.timedelta(days=7)
        sub = SubscriptionSerializer(
            data={
                "type": "STANDARD", 
                "date_activated":today, 
                "expire_date":free_days,
                "company": company.pk
                }
            )
        if sub.is_valid():
            sub.save()
        else:
            return sub.errors
        
        #Creating user who is shopowner for the company
        shop_owner = UserSerializer(data=owner)
        if shop_owner.is_valid():
            shop_owner.save()
        else:
            return shop_owner.errors
        return company


class UserSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(max_length=150)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    user_company = serializers.SlugRelatedField(queryset=Company.objects.all(),slug_field="company_name")
    groups = serializers.StringRelatedField(many=True, read_only=True)
    user_groups = serializers.JSONField(write_only=True)
    password = serializers.CharField(
        style={'input_type':'password'},
        write_only=True
    )

    class Meta:
        model = AppUser
        fields = ["id","username", "first_name", "last_name", "phone_number", "email", 
                    "user_company", "groups", "password", "user_groups"]
    
    def create(self, validated_data):
        user_group = validated_data.pop("user_groups")
        password = validated_data.pop('password')
        username = validated_data.pop('username').title()
        
        if AppUser.objects.filter(username=username.title()).exists():
            raise serializers.ValidationError({"username": "User with similar username Exist"})
        
        user = AppUser.objects.create_user(username=username, password=password, **validated_data)
        if user_group is not None:
            for userrole in user_group:
                try:
                    group = Group.objects.get(name=userrole.lower())
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
        user = self.context['request'].user
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

class LoginSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    username=serializers.CharField(max_length=150)
    password=serializers.CharField(style={'input_type':'password'},trim_whitespace=False,write_only=True)
    first_name=serializers.CharField(read_only=True,max_length=150)
    last_name=serializers.CharField(read_only=True,max_length=150)
    phone_number=serializers.CharField(read_only=True,max_length=150)
    groups = UserGroupField(many=True, read_only=True)
    user_company=CompanySerializer(read_only=True)
    
    def validate(self,attrs):
        username=attrs.get('username').title()
        password =attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidatorError('Provide both username and password')
        
        if not AppUser.objects.filter(username=username).exists():
            raise serializers.ValidationError('User does not exist')
        user=authenticate(request=self.context.get('request'),username=username,password=password)
        
        if not user:
            raise serializers.ValidationError('Wrong credentials')
        attrs['user']=user
        
        return attrs