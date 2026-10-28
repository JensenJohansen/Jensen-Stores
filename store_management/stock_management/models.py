from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from user_management.models import Company

def validate_value(value):
    if value <= 0:
        raise ValidationError(
            _('%(value)s should be greater than 0'),
            params={'value': value},
        )


class Categories(models.Model):
    '''Model definition for goods categories'''
    category_name = models.CharField(_("Goods category"), max_length=150, unique=True)
    date_added = models.DateTimeField(_("date goods category added"), auto_now=True)
    
    def __str__(self) -> str:
        return self.category_name

class GoodsType(models.Model):
    '''Model definition for GoodsType.'''
    goods_type=models.CharField(_("Goods type"), max_length=150)
    categories=models.ForeignKey(Categories, verbose_name=_("goods category"), on_delete=models.SET_NULL, blank=True, null=True)
    date_added=models.DateTimeField(_("Date goods type added"), auto_now=True)
    company = models.ForeignKey(Company, verbose_name=_("goodstype company"), on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        '''Meta definition for GoodsType.'''
        unique_together = ("company", "goods_type")
        verbose_name = 'GoodsType'
        verbose_name_plural = 'GoodsTypes'

    def __str__(self):
        return self.goods_type
    
    
class Store(models.Model):
    '''Model definition for Store.'''
    store_name=models.CharField(_("Store name"), max_length=150)
    company = models.ForeignKey(Company, verbose_name=_("store company"), related_name=_('store_company'), on_delete=models.DO_NOTHING, blank=True, null=True)
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


class Supplier(models.Model):
    supplier_name = models.CharField(_("Supplier name"), max_length=150)
    company = models.ForeignKey(Company, verbose_name=_("supplier company"), related_name="suppliers", on_delete=models.CASCADE)
    contact_person = models.CharField(_("Contact person"), max_length=150, blank=True, null=True)
    phone_number = models.CharField(_("Phone number"), max_length=20, blank=True, null=True)
    email = models.EmailField(_("Supplier email"), blank=True, null=True)
    address = models.CharField(_("Supplier address"), max_length=255, blank=True, null=True)
    tin = models.CharField(_("Supplier TIN"), max_length=50, blank=True, null=True)
    added_by = models.ForeignKey(
        get_user_model(),
        verbose_name=_("User who added supplier"),
        related_name="suppliers_added",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    date_added = models.DateTimeField(_("Date supplier added"), auto_now=True)

    class Meta:
        unique_together = ("company", "supplier_name")
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")

    def __str__(self):
        return self.supplier_name


class Goods(models.Model):
    '''Model definition for Goods.'''
    goods_name=models.CharField(_("Goods name"), max_length=150)
    goods_number=models.CharField(_("Goods number"), max_length=150)
    goods_quantity=models.IntegerField(_("Goods quantity in number"),validators=[validate_value])
    goods_type=models.ForeignKey(GoodsType, verbose_name=_("goods type or size"),related_name='goods_and_type', on_delete=models.SET_NULL,blank=True, null=True)
    buying_price=models.IntegerField(_("buying price"), blank=True, null=True, validators=[validate_value])
    lower_price_margin=models.FloatField(_("Lowest price of a product"),validators=[validate_value])
    store=models.ForeignKey(Store, verbose_name=_("store goods found"),related_name='store', on_delete=models.DO_NOTHING)
    added_by=models.ForeignKey(get_user_model(), verbose_name=_("User who added goods"), on_delete=models.DO_NOTHING)
    restricted_price=models.BooleanField(_("The limited lower price"),default=True)
    alert_on_goods_quantity=models.IntegerField(_("The quantity where a user is alerted of shortage of stock"),default=50)
    date_updated=models.DateField(_("Date updated"),null=True,blank=True)
    time_updated=models.TimeField(_("Time updated"),null=True,blank=True)
    update_url=models.TextField(_("URL which updated goods"),null=True,blank=True)
    date_added=models.DateTimeField(_("date goods added"), auto_now=True)
    
    class Meta:
        '''Meta definition for Goods.'''
        unique_together=['goods_number','store',]
        verbose_name = 'Goods'
        verbose_name_plural = 'Goods'

    def __str__(self):
        return self.goods_number


class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("received", "Received"),
        ("cancelled", "Cancelled"),
    ]

    supplier = models.ForeignKey(Supplier, verbose_name=_("supplier"), related_name="purchase_orders", on_delete=models.CASCADE)
    store = models.ForeignKey(Store, verbose_name=_("destination store"), related_name="purchase_orders", on_delete=models.CASCADE)
    created_by = models.ForeignKey(get_user_model(), verbose_name=_("created by"), related_name="purchase_orders_created", on_delete=models.CASCADE)
    authorized_by = models.ForeignKey(
        get_user_model(),
        verbose_name=_("authorized by"),
        related_name="purchase_orders_authorized",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField(_("purchase order status"), max_length=20, choices=STATUS_CHOICES, default="draft")
    notes = models.TextField(_("notes"), blank=True, null=True)
    received_at = models.DateTimeField(_("received at"), blank=True, null=True)
    date_added = models.DateTimeField(_("date purchase order created"), auto_now=True)

    class Meta:
        verbose_name = _("PurchaseOrder")
        verbose_name_plural = _("PurchaseOrders")

    def __str__(self):
        return f"PO-{self.id} {self.supplier}"


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, verbose_name=_("purchase order"), related_name="items", on_delete=models.CASCADE)
    goods = models.ForeignKey("stock_management.Goods", verbose_name=_("goods"), related_name="purchase_order_items", on_delete=models.CASCADE)
    quantity = models.IntegerField(_("quantity"), validators=[validate_value])
    unit_cost = models.FloatField(_("unit cost"), validators=[validate_value])
    date_added = models.DateTimeField(_("date item added"), auto_now=True)

    class Meta:
        unique_together = ("purchase_order", "goods")
        verbose_name = _("PurchaseOrderItem")
        verbose_name_plural = _("PurchaseOrderItems")

    def __str__(self):
        return f"{self.goods} x {self.quantity}"


class GoodsUpdate(models.Model):
    choice_order=[
        ('deleted_order','Deleted Order'),
        ('issued_order', 'Issued Order'),
        ('updated_stock','Updated Stock'),
        ('broken_stock','Broken Stock'),
        ('restocked_broken','Broken Return'),
        ('purchase_order_receipt', 'Purchase Order Receipt'),
        ('sales_return', 'Sales Return'),
        ('store_transfer_out', 'Store Transfer Out'),
        ('store_transfer_in', 'Store Transfer In'),
    ]
    
    goods=models.ForeignKey(Goods, verbose_name=_("Goods to be updated"), on_delete=models.CASCADE)
    updated_by=models.ForeignKey(get_user_model(), verbose_name=_("User who updated goods"), on_delete=models.DO_NOTHING)
    quantity_available=models.IntegerField(_("Quantity available"))
    quantity_added=models.IntegerField(_("Quantity added"))
    updated_on=models.DateField(_("Date goods updated"), auto_now=True)
    goods_update_reason=models.CharField(_("reason for Update"),choices=choice_order,max_length=30,default='updated_stock',null=True,blank=True)
    authorized_by=models.ForeignKey(get_user_model(),related_name='update_authorizer', verbose_name=_("Authorizer of update"), on_delete=models.SET_NULL,null=True,blank=True)
    
    class Meta:
        verbose_name = 'GoodsUpdate'
        verbose_name_plural = 'GoodsUpdates'

class TemporaryGoodsUpdate(models.Model):
    
    goods=models.ForeignKey(Goods, verbose_name=_("Goods to be updated"), on_delete=models.CASCADE)
    updated_by=models.ForeignKey(get_user_model(), verbose_name=_("User who updated goods"), on_delete=models.DO_NOTHING)
    quantity_added=models.IntegerField(_("Quantity added"))
    updated_on=models.DateField(_("Date goods updated"), auto_now=True)

    class Meta:
        verbose_name = _("TemporaryGoodsUpdate")
        verbose_name_plural = _("TemporaryGoodsUpdates")


class StockTransfer(models.Model):
    STATUS_CHOICES = [
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    goods = models.ForeignKey("stock_management.Goods", verbose_name=_("source goods"), related_name="stock_transfers", on_delete=models.CASCADE)
    from_store = models.ForeignKey(Store, verbose_name=_("from store"), related_name="outgoing_transfers", on_delete=models.CASCADE)
    to_store = models.ForeignKey(Store, verbose_name=_("to store"), related_name="incoming_transfers", on_delete=models.CASCADE)
    quantity = models.IntegerField(_("quantity"), validators=[validate_value])
    transfer_note = models.CharField(_("transfer note"), max_length=255, blank=True, null=True)
    transferred_by = models.ForeignKey(get_user_model(), verbose_name=_("transferred by"), related_name="stock_transfers_created", on_delete=models.CASCADE)
    authorized_by = models.ForeignKey(
        get_user_model(),
        verbose_name=_("authorized by"),
        related_name="stock_transfers_authorized",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    status = models.CharField(_("transfer status"), max_length=20, choices=STATUS_CHOICES, default="completed")
    date_added = models.DateTimeField(_("date transfer created"), auto_now=True)

    class Meta:
        verbose_name = _("StockTransfer")
        verbose_name_plural = _("StockTransfers")

    def __str__(self):
        return f"{self.goods} {self.from_store} -> {self.to_store}"


class Leakage(models.Model):
    """
    A model that define the leaked or broken goods in the company
    """
    goods = models.ForeignKey(Goods, verbose_name=_("broken goods"),related_name='broken', on_delete=models.CASCADE)
    amount_broken = models.IntegerField(_("how many that broke"))
    leakage_summary = models.CharField(_("leakage summary"), max_length=150,null=True,blank=True)
    broken_date = models.DateTimeField(_("Date for the leakage"), auto_now=True, auto_now_add=False)
    added_by = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    
    def __str__(self) -> str:
        return f"broken: {self.goods} - {self.amount_broken}"


class SalesReturn(models.Model):
    goods_order = models.ForeignKey("order_management.GoodsOrder", verbose_name=_("goods order"), related_name="sales_returns", on_delete=models.CASCADE)
    returned_quantity = models.IntegerField(_("returned quantity"), validators=[validate_value])
    return_reason = models.CharField(_("return reason"), max_length=255, blank=True, null=True)
    returned_by = models.ForeignKey(get_user_model(), verbose_name=_("returned by"), related_name="sales_returns_created", on_delete=models.CASCADE)
    authorized_by = models.ForeignKey(
        get_user_model(),
        verbose_name=_("authorized by"),
        related_name="sales_returns_authorized",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    date_added = models.DateTimeField(_("date return created"), auto_now=True)

    class Meta:
        verbose_name = _("SalesReturn")
        verbose_name_plural = _("SalesReturns")

    def __str__(self):
        return f"Return {self.goods_order_id} x {self.returned_quantity}"
    
    
