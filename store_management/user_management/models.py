
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser,PermissionsMixin
from .managers import CustomUserManager

class Company(models.Model):
    '''Model definition for Company.'''
    company_name=models.CharField(_("Company name"), max_length=150)
    company_location=models.CharField(_("Company location"), max_length=150)
    company_tin=models.CharField(_("Company's tin number"), max_length=50,blank=True, null=True)
    date_added=models.DateTimeField(_("Date company added"), auto_now=True)

    class Meta:
        '''Meta definition for Company.'''

        verbose_name = 'Company'
        verbose_name_plural = 'Companys'

    def __str__(self):
        return self.company_name

class Role(models.Model):
    '''Model definition for Role.'''
    role_name=models.CharField(_("Role name"), max_length=150)
    role_description=models.TextField(_("role description"),blank=True, null=True)
    date_added=models.DateTimeField(_("Date role added"), auto_now=True)
    class Meta:
        '''Meta definition for Role.'''

        verbose_name = 'Role'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.role_name

class AppUser(AbstractBaseUser,PermissionsMixin):
    username=models.CharField(_("This identifies a login credentials for our user"), max_length=250,unique=True)
    first_name=models.CharField(_("First name"), max_length=100)
    last_name=models.CharField(_("Last name"), max_length=100)
    phone_number=models.CharField(_("Phone number"),max_length=15)
    owner=models.ManyToManyField(Company,verbose_name=_("company owner"),related_query_name="company_owners")
    role=models.ManyToManyField(Role,verbose_name=_("User's role"),related_query_name="user_roles")
    
    USERNAME_FIELD="username"
    
    REQUIRED_FIELDS = ["first_name","last_name","phone_number"]
    
    objects = CustomUserManager

    def __str__(self):
        return self.username

    def __unicode__(self):
        return self.username
