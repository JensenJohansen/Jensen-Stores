from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(GoodsType)
admin.site.register(Goods)
admin.site.register(Store)
admin.site.register(GoodsUpdate)
admin.site.register(Categories)
admin.site.register(Leakage)
admin.site.register(Supplier)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(StockTransfer)
admin.site.register(SalesReturn)
