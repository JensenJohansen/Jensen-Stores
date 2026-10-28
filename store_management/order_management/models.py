from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from stock_management.models import Goods


class OrderAuthorizationStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    PARTIALLY_PAID = "partially_paid", _("Partially paid")
    PAID = "paid", _("Paid")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", _("Cancelled")


class Order(models.Model):
    '''Model definition for Order.'''
    order_no=models.BigAutoField(_("order identification number"),primary_key=True)
    customer = models.ForeignKey(
        "user_management.Customer",
        verbose_name=_("registered customer"),
        related_name="orders",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    customer_name = models.CharField(_("Customer name"), max_length=150, null=True, blank=True)
    authorizer=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who authorizes an order"),related_name='order_authorizer', on_delete=models.DO_NOTHING,blank=True, null=True)
    authorization_status = models.CharField(
        _("Authorized status"),
        max_length=20,
        choices=OrderAuthorizationStatus.choices,
        default=OrderAuthorizationStatus.PENDING,
    )
    creator=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who creates an order"), on_delete=models.CASCADE)
    issued_status=models.BooleanField(_("Has the order been completly issued?"), default=False)
    order_discount=models.FloatField(_("Discount given to a user"),default=0.00)
    order_caption=models.TextField(_("Short description about the order"),blank=True, null=True)
    approval_note=models.TextField(_("Approval note"), blank=True, null=True)
    submitted_at=models.DateTimeField(_("submitted at"), default=timezone.now)
    approved_at=models.DateTimeField(_("approved at"), blank=True, null=True)
    rejected_at=models.DateTimeField(_("rejected at"), blank=True, null=True)
    paid_at=models.DateTimeField(_("paid at"), blank=True, null=True)
    date_added=models.DateTimeField(_("Date an order created"), auto_now=True)
    class Meta:
        '''Meta definition for Order.'''

        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        

class GoodsOrder(models.Model):
    '''Model definition for GoodsOrder.'''
    order=models.ForeignKey(Order, verbose_name=_("Order object"),related_name='order_goods', on_delete=models.CASCADE)
    goods=models.ForeignKey(Goods, verbose_name=_("Goods object"), on_delete=models.CASCADE,related_query_name="goods_ref",blank=True, null=True)
    goods_quantity=models.IntegerField(_("How many goods is user buying?"))
    price=models.FloatField(_("Price of the goods"))
    issued_status=models.BooleanField(_("Is this item issued?"),default=False)
    issuer = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who issued an order"),related_name='order_issuer', on_delete=models.DO_NOTHING,blank=True, null=True)
    date_added=models.DateTimeField(_("Date goods order added"), auto_now=True,blank=True, null=True)
    class Meta:
        '''Meta definition for GoodsOrder.'''

        verbose_name = 'GoodsOrder'
        verbose_name_plural = 'GoodsOrders'
    
    def __str__(self) -> str:
        return f'{self.goods.goods_name} for order {self.order}'
    
class DeletedOrder(models.Model):

    order_no=models.IntegerField(_("Order number"))
    deleted_by=models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("user who deleted an order"),related_name='goods_deleter', on_delete=models.CASCADE)
    goods_object=models.JSONField(_("deleted goods json"))
    deleted_time=models.DateTimeField(_("date the order deleted"), auto_now=True)
    class Meta:
        verbose_name = _("DeletedOrder")
        verbose_name_plural = _("DeletedOrders")


class Payment(models.Model):
    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("bank", "Bank"),
        ("card", "Card"),
        ("mobile_money", "Mobile Money"),
        ("credit", "Credit"),
        ("dummy", "Dummy"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("void", "Void"),
        ("refunded", "Refunded"),
    ]

    order = models.ForeignKey(Order, verbose_name=_("order"), related_name="payments", on_delete=models.CASCADE)
    amount = models.FloatField(_("amount"))
    method = models.CharField(_("payment method"), max_length=30, choices=METHOD_CHOICES, default="dummy")
    status = models.CharField(_("payment status"), max_length=20, choices=STATUS_CHOICES, default="completed")
    reference = models.CharField(_("payment reference"), max_length=100, blank=True, null=True)
    provider = models.CharField(_("payment provider"), max_length=100, blank=True, null=True)
    currency = models.CharField(_("currency"), max_length=10, default="TZS")
    note = models.TextField(_("payment note"), blank=True, null=True)
    metadata = models.JSONField(_("payment metadata"), blank=True, null=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("recorded by"), related_name="payments_recorded", on_delete=models.CASCADE)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("approved by"), related_name="payments_approved", on_delete=models.SET_NULL, blank=True, null=True)
    paid_at = models.DateTimeField(_("paid at"), blank=True, null=True)
    date_added = models.DateTimeField(_("date payment added"), auto_now=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")

    def __str__(self):
        return f"{self.order_id} - {self.amount} {self.method}"


class AuditLog(models.Model):
    company = models.ForeignKey("user_management.Company", verbose_name=_("company"), related_name="audit_logs", on_delete=models.CASCADE, blank=True, null=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("actor"), related_name="audit_logs", on_delete=models.SET_NULL, blank=True, null=True)
    action = models.CharField(_("action"), max_length=100)
    entity_type = models.CharField(_("entity type"), max_length=100)
    entity_id = models.CharField(_("entity id"), max_length=100)
    description = models.TextField(_("description"), blank=True, null=True)
    payload = models.JSONField(_("payload"), blank=True, null=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("AuditLog")
        verbose_name_plural = _("AuditLogs")

    def __str__(self):
        return f"{self.action} {self.entity_type}#{self.entity_id}"
