from django.contrib.auth.models import Group
from django.db.models import Q, F
from rest_framework import serializers
from django.core.serializers import serialize
from .models import Company, AppUser


class CompanyUserListingField(serializers.Serializer):
    def to_representation(self, user_company):
        """
        Purpose: This displays company and their owners.
        """
        company_owner = AppUser.objects.values('id','first_name','last_name','username','groups__name').get(id=user_company.id)
        return company_owner
    # end def


class CompanySerializer(serializers.ModelSerializer):
    user_company = CompanyUserListingField(many=True, read_only=True)

    class Meta:
        model = Company
        fields = '__all__'

    def save(self, validated_data):
        """
        Purpose: Create a Company Profile
        """
        company_owner = validated_data.pop('owner')

        company = Company.objects.create(**validated_data)
        if company_owner is not None:
            for own in company_owner:
                own_role = own.pop('user_groups')
                try:
                    owner = AppUser.objects.get(username=own['username'])
                except AppUser.DoesNotExist:
                    owner = AppUser.objects.create_user(user_company=company, **own)
                for role in own_role:
                    role = Group.objects.get(name=role.title())
                    owner.groups.add(role)
        return company
    # end def


class UserRegistrationSerializer(serializers.ModelSerializer):
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
                userrole=userrole.title()
                group = Group.objects.get(name=userrole)
                user.groups.add(group)

        return user
    # end def
