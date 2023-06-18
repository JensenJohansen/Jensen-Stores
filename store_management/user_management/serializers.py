from rest_framework import serializers
from django.core.serializers import serialize
from .models import Company,Role,AppUser

class CompanyUserListingField(serializers.Serializer):
    def to_representation(self, user_company):
        """
        Purpose: This displays company and their owners.
        """
        company_owner=AppUser.objects.values('id','first_name','last_name','role__role_name').get(id=user_company.id)
        return company_owner
    # end def

class CompanySerializer(serializers.ModelSerializer):
    user_company=CompanyUserListingField(many=True,read_only=True)
    class Meta:
        model = Company
        fields='__all__'
        
    def save(self, validated_data):
        """
        Purpose: Create a Company Profile
        """
        company_owner= validated_data.pop('owner')
        
        company=Company.objects.create(**validated_data)
        if company_owner != None:
            for own in company_owner:
                own_role=own.pop('role').capitalize()
                try:
                    owner=AppUser.objects.get(username=own['username'])
                except AppUser.DoesNotExist:
                    owner=AppUser.objects.create_user(user_company=company,**own)
                    
                role=Role.objects.get_or_create(role_name=own_role)
                owner.role.add(role[0])
        return company
    # end def

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields='__all__'

class UserRegistrationSerializer(serializers.ModelSerializer):
    company_owners=CompanySerializer(many=True,read_only=True)
    user_roles=RoleSerializer(many=True,read_only=True)
    class Meta:
        model=AppUser
        fields='__all__'
        extra_kwargs = {
            'password': {'write_only': True, 'min_length': 8}
            }
        
    def save(self,validated_data):
        """
        Purpose: Method registers data
        """
        user_role = validated_data.pop('user_roles')
        user_company=validated_data.pop('company')
        try:
            user_company=Company.objects.get(company_name=user_company)
        except Company.DoesNotExist:
            user_company=None
        
        user=AppUser.objects.create_user(company=user_company,**validated_data)
        
        if user_role != None:
            for userrole in user_role:
                role=Role.objects.get(**userrole)
                user.role.add(role)
            
        return user
    # end def
    
