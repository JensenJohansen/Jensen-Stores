from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth import get_user_model
from stock_management.models import Goods
from datetime import datetime

class OrderStatus(models.Model):
    '''Model definition for OrderStatus.'''
    status=models.CharField(_("Order status"), max_length=50)
    date_added=models.DateTimeField(_("Date a status added"), auto_now=True)
    class Meta:
        '''Meta definition for OrderStatus.'''
        
        verbose_name = 'OrderStatus'
        verbose_name_plural = 'OrderStatus'


class Order(models.Model):
    '''Model definition for Order.'''
    order_no=models.BigAutoField(_("order identification number"),primary_key=True)
    issuer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who issued an order"),related_name='order_issuer', on_delete=models.DO_NOTHING,blank=True, null=True)
    authorizer=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who authorizes an order"),related_name='order_authorizer', on_delete=models.DO_NOTHING,blank=True, null=True)
    authorization_status=models.ForeignKey(OrderStatus, verbose_name=_("Authorized status"), on_delete=models.SET_NULL,default=1,null=True,blank=True)
    creator=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who creates an order"), on_delete=models.CASCADE)
    issued_status=models.BooleanField(_("Has the order been issued?"), default=False)
    order_discount=models.FloatField(_("Discount given to a user"),default=0.00)
    date_added=models.DateTimeField(_("Date an order created"), auto_now=True)
    class Meta:
        '''Meta definition for Order.'''

        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    
class GoodsOrder(models.Model):
    '''Model definition for GoodsOrder.'''
    order=models.ForeignKey(Order, verbose_name=_("Order object"),related_name='order_goods', on_delete=models.CASCADE)
    goods=models.ForeignKey(Goods, verbose_name=_("Goods object"), on_delete=models.DO_NOTHING,related_query_name="goods_ref",blank=True, null=True)
    goods_quantity=models.IntegerField(_("How many goods is user buying?"))
    price=models.FloatField(_("Price of the goods"))
    issued_status=models.BooleanField(_("Is this item issued?"),default=False)
    date_added=models.DateTimeField(_("Date goods order added"), auto_now=True,blank=True, null=True)
    class Meta:
        '''Meta definition for GoodsOrder.'''

        verbose_name = 'GoodsOrder'
        verbose_name_plural = 'GoodsOrders'
