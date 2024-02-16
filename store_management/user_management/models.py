from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager
from django.contrib.auth.models  import Group
from phonenumber_field.modelfields import PhoneNumberField

    
class Company(models.Model):
    '''Model definition for Company.'''
    company_name = models.CharField(_("Company name"), max_length=150)
    company_location = models.CharField(_("Company location"), max_length=150)
    company_tin = models.CharField(_("Company's tin number"), max_length=50, blank=True, null=True)
    date_added = models.DateTimeField(_("Date company added"), auto_now=True)

    class Meta:
        '''Meta definition for Company.'''
        unique_together=('company_name','company_location','company_tin',)
        verbose_name = 'Company'
        verbose_name_plural = 'Companys'

    def __str__(self):
        return self.company_name


class Subscription(models.Model):
    """A model defining the company subscriptions for the caffein services"""
    TYPE = (
        ("STANDARD", "STANDARD"),
        ("PROFESSIONAL", "PROFFESIONAL"),
        ("ULTIMATE", "ULTIMATE"),
    )
    status = models.BooleanField(_("subscription status"), default=False)
    type = models.CharField(_("subscription type"), max_length=50, choices=TYPE)
    date_activated = models.DateField(_("date activated"), auto_now=False, auto_now_add=False)
    expire_date = models.DateField(_("expire date"), auto_now=False, auto_now_add=False)
    company = models.ForeignKey(Company, verbose_name=_("company subscribed"), on_delete=models.CASCADE, blank=True, null=True)
    
    def __str__(self) -> str:
        return f'{self.company} - {self.type}'


class AppUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_("This identifies a login credentials for our user"), max_length=250, unique=True)
    first_name = models.CharField(_("First name"), max_length=100)
    last_name = models.CharField(_("Last name"), max_length=100)
    phone_number = models.CharField(_("Phone number"), max_length=15)
    email = models.EmailField(max_length=100, blank=True, null=True)
    user_company = models.ForeignKey(Company, verbose_name=_("Users company"), related_name='user_company',
                                    on_delete=models.CASCADE, null=True, blank=True)
    groups = models.ManyToManyField(Group, verbose_name=_("app users"), blank=True, null=True)
    is_staff = models.BooleanField(_("Is a user staff"), default=False)
    is_active = models.BooleanField(_("Is a user active"), default=True)

    USERNAME_FIELD = "username"
    
    EMAIL_FIELD = "email"

    REQUIRED_FIELDS = ["first_name", "last_name", "phone_number"]

    objects = CustomUserManager()

    def __str__(self):
        return self.username


class Customer(models.Model):
    """"
    A model definition for the company customers
    """
    customer_username = models.CharField(_("Customer name"), max_length=50)
    customer_phone = PhoneNumberField(blank=False, unique=True)
    customer_company = models.ForeignKey(Company, verbose_name=_("customer company"), on_delete=models.CASCADE)
    
    def __str__(self) -> str:
        return self.customer_username