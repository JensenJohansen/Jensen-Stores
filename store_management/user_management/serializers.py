from django.contrib.auth.models import Group
from django.db.models import Q, F
from rest_framework import serializers
from .models import Company, AppUser
from django.contrib.auth import authenticate, login, models, get_user_model
from rest_framework.response import Response


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

class CompanySerializer(serializers.ModelSerializer):
    user_company = CompanyUserListingField(many=True, read_only=True)
    owner=serializers.JSONField(write_only=True, allow_null=True)
    company = serializers.JSONField(write_only=True, allow_null=True)
    class Meta:
        model = Company
        fields = '__all__'
        read_only_fields = ["company_name", "company_location", "company_tin"]

    def create(self, validated_data):
        """
        Purpose: Create a Company Profile
        """
        company_owner = validated_data.pop('owner')
        validated_data = validated_data['company']
        
        if Company.objects.filter(**validated_data).exists():
            raise serializers.ValidationError("This Company already exists")
        else:
            company=Company.objects.create(**validated_data)
            return company
    # end def
    
    def update(self, instance, validated_data):
        company = instance.id
        validated_data = validated_data['owner']
        group = validated_data.pop('user_groups')
        username = validated_data.pop('username')
        for item in group:
            try:
                group = Group.objects.get(name=item.title())
            except Group.DoesNotExist:
                raise serializers.ValidationError("you choose the uknown group")
        
        try:
            staff = AppUser.objects.get(username=username.title())
        except AppUser.DoesNotExist:
            staff = AppUser.objects.create_user(username=username.title(), user_company=instance, **validated_data)
        
        staff.groups.add(group)
        return Response(data=staff)



class UserSerializer(serializers.ModelSerializer):
    company_owners = CompanySerializer(many=True, read_only=True)
    user = serializers.JSONField(write_only=True, allow_null=True)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = AppUser
        fields = '__all__'
        read_only_fields = ["username", "first_name", "last_name", "phone_number"]
    
    def create(self, validated_data):
        """
        Purpose: Method registers data
        """
        password = validated_data['password']
        validated_data = validated_data['user']
        user_group = validated_data.pop('user_groups')
        user_company = validated_data.pop('company')
        try:
            user_company = Company.objects.get(company_name=user_company)
        except Company.DoesNotExist:
            user_company = None
        
        if AppUser.objects.filter(username=validated_data['username'].title()).exists():
            raise serializers.ValidationError({"username": "User with similar username Exist"})
        
        user = AppUser.objects.create_user(user_company=user_company, password=password, **validated_data)
        
        if user_group is not None:
            for userrole in user_group:
                group = Group.objects.get(name=userrole.title())
                user.groups.add(group)
        
        return user
    # end def
    
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