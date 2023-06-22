from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from stock_management.models import Goods

class Order(models.Model):
    '''Model definition for Order.'''
    order_no=models.IntegerField(_("order identification number"),primary_key=True)
    issuer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who issued an order"),related_name='order_issuer', on_delete=models.DO_NOTHING,blank=True, null=True)
    authorizer=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who authorizes an order"),related_name='order_authorizer', on_delete=models.DO_NOTHING,blank=True, null=True)
    authorized_status=models.BooleanField(_("The authorization status"),default=False)
    creator=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who creates an order"), on_delete=models.CASCADE)
    issued_status=models.BooleanField(_("Has the order been issued?"), default=False)
    order_discount=models.FloatField(_("Discount given to a user"),default=0.00)
    date_added=models.DateTimeField(_("Date an order created"), auto_now=True)
    class Meta:
        '''Meta definition for Order.'''

        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f'{self.order_no}'
    
class GoodsOrder(models.Model):
    '''Model definition for GoodsOrder.'''
    order=models.ForeignKey(Order, verbose_name=_("Order object"), on_delete=models.CASCADE)
    goods=models.ForeignKey(Goods, verbose_name=_("Goods object"), on_delete=models.DO_NOTHING,blank=True, null=True)
    goods_quantity=models.IntegerField(_("How many goods is user buying?"))
    price=models.FloatField(_("Price of the "))
    issued_status=models.BooleanField(_("Is this item issued?"))

    class Meta:
        '''Meta definition for GoodsOrder.'''

        verbose_name = 'GoodsOrder'
        verbose_name_plural = 'GoodsOrders'

    def __str__(self):
        return f'{self.goods} is for {self.order}'