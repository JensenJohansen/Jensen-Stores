from django.contrib.auth.models import Group
from django.db.models import Q, F
from rest_framework import serializers
from .models import Company, AppUser
from django.contrib.auth import authenticate, login, models, get_user_model


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
    owner=serializers.JSONField(write_only=True)
    class Meta:
        model = Company
        fields = '__all__'

    def create(self, validated_data):
        """
        Purpose: Create a Company Profile
        """
        company_owner = validated_data.pop('owner')
        
        if Company.objects.filter(**validated_data).exists():
            raise serializers.ValidationError("This Company already exists")
        else:
            company=Company.objects.create(**validated_data)
            if company_owner is not None:
                for own in company_owner:
                    own_role = own.pop('user_groups')
                    own['username']=own['username'].capitalize()
                    try:
                        owner = AppUser.objects.get(username=own['username'])
                    except AppUser.DoesNotExist:
                        owner = AppUser.objects.create_user(user_company=company, **own)
                    for role in own_role:
                        role = Group.objects.get(name=role) #removing .title to match queries
                        owner.groups.add(role)
            return company
    # end def


class UserSerializer(serializers.ModelSerializer):
    company_owners = CompanySerializer(many=True, read_only=True)

    class Meta:
        model = AppUser
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
        }

    def save(self, validated_data):
        """
        Purpose: Method registers data
        """
        user_group = validated_data.pop('user_groups')
        user_company = validated_data.pop('company')
        try:
            user_company = Company.objects.get(company_name=user_company)
        except Company.DoesNotExist:
            user_company = None

        user = AppUser.objects.create_user(user_company=user_company, **validated_data)

        if user_group is not None:
            for userrole in user_group:
                group = Group.objects.get(name=userrole)
                user.groups.add(group)

        return user
    # end def


class GroupSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return instance.name

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
        username=attrs.get('username')
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