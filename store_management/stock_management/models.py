from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

def validate_value(value):
    if value <= 0:
        raise ValidationError(
            _('%(value)s should be greater than 0'),
            params={'value': value},
        )


class GoodsType(models.Model):
    '''Model definition for GoodsType.'''
    goods_type=models.CharField(_("Goods type"), max_length=150, unique=True)
    date_added=models.DateTimeField(_("Date goods type added"), auto_now=True)

    class Meta:
        '''Meta definition for GoodsType.'''
        verbose_name = 'GoodsType'
        verbose_name_plural = 'GoodsTypes'

    def __str__(self):
        return self.goods_type
    
    
class Store(models.Model):
    '''Model definition for Store.'''
    store_name=models.CharField(_("Store name"), max_length=150)
    store_location=models.CharField(_("Store location"), max_length=150)
    store_supervisor=models.ForeignKey(get_user_model(), verbose_name=_("store supervisor"),related_name='store_keeper', on_delete=models.SET_NULL,blank=True, null=True)
    added_by=models.ForeignKey(get_user_model(), verbose_name=_("User who added store"),related_name='store_adder', on_delete=models.DO_NOTHING,blank=True, null=True)
    date_added=models.DateTimeField(_("Date store registered"), auto_now=True)

    class Meta:
        '''Meta definition for Store.'''

        verbose_name = 'Store'
        verbose_name_plural = 'Stores'

    def __str__(self):
        return self.store_name


class Goods(models.Model):
    '''Model definition for Goods.'''
    goods_name=models.CharField(_("Goods name"), max_length=150)
    goods_number=models.CharField(_("Goods number"), max_length=150)
    goods_quantity=models.IntegerField(_("Goods quantity in number"),validators=[validate_value])
    goods_size=models.ForeignKey(GoodsType, verbose_name=_("goods type or size"),related_name='size', on_delete=models.DO_NOTHING)
    lower_price_margin=models.FloatField(_("Lowest price of a product"),validators=[validate_value])
    store=models.ForeignKey(Store, verbose_name=_("store goods found"),related_name='store', on_delete=models.DO_NOTHING)
    added_by=models.ForeignKey(get_user_model(), verbose_name=_("User who added goods"), on_delete=models.DO_NOTHING)
    date_added=models.DateTimeField(_("date goods added"), auto_now=True)
    class Meta:
        '''Meta definition for Goods.'''
        unique_together=['goods_number','store',]
        verbose_name = 'Goods'
        verbose_name_plural = 'Goods'

    def __str__(self):
        return self.goods_number


class GoodsUpdate(models.Model):
    goods=models.ForeignKey(Goods, verbose_name=_("Goods to be updated"), on_delete=models.CASCADE)
    updated_by=models.ForeignKey(get_user_model(), verbose_name=_("User who updated goods"), on_delete=models.DO_NOTHING)
    quantity_available=models.IntegerField(_("Quantity available"))
    quantity_added=models.IntegerField(_("Quantity added"))
    updated_on=models.DateField(_("Date goods updated"), auto_now=True)
    
    class Meta:
        verbose_name = 'GoodsUpdate'
        verbose_name_plural = 'GoodsUpdates'
