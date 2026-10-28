from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from order_management.models import AuditLog
from stock_management.models import Goods, GoodsType, Leakage, Store, Supplier
from user_management.models import Company


class BulkGoodsUploadAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.user = get_user_model().objects.create_user(
            username="owner",
            password="pass12345",
            first_name="Shop",
            last_name="Owner",
            phone_number="255700000001",
            email="owner@example.com",
            user_company=self.company,
        )
        self.group = Group.objects.create(name="shopowner")
        self.user.groups.add(self.group)

        self.store = Store.objects.create(
            store_name="Main Store",
            company=self.company,
            store_location="City Center",
            store_supervisor=self.user,
            added_by=self.user,
        )
        self.goods_type = GoodsType.objects.create(
            goods_type="Groceries",
            company=self.company,
        )

        self.client.force_authenticate(user=self.user)

    def test_bulk_template_download_returns_csv_template(self):
        response = self.client.get(reverse("goods-bulk-template"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment; filename=\"goods_bulk_upload_template.csv\"", response["Content-Disposition"])
        self.assertIn("goods_name,goods_number,goods_quantity", response.content.decode("utf-8"))

    def test_bulk_upload_creates_goods_from_csv(self):
        upload = SimpleUploadedFile(
            "stocks.csv",
            (
                "goods_name,goods_number,goods_quantity,goods_type,buying_price,lower_price_margin,store,restricted_price,alert_on_goods_quantity\n"
                "Blue Band 500g,BB-500,120,Groceries,2400,2800,Main Store,true,20\n"
                "Rice 1kg,RC-001,85,Groceries,3200,3800,Main Store,false,15\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("goods-bulk-upload"),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(Goods.objects.count(), 2)
        self.assertEqual(AuditLog.objects.filter(action="goods.bulk_upload").count(), 1)
        self.assertEqual(Goods.objects.get(goods_number="BB-500").added_by, self.user)

    def test_bulk_upload_returns_row_errors_and_rolls_back(self):
        upload = SimpleUploadedFile(
            "stocks.csv",
            (
                "goods_name,goods_number,goods_quantity,goods_type,buying_price,lower_price_margin,store,restricted_price,alert_on_goods_quantity\n"
                "Blue Band 500g,BB-500,120,Groceries,2400,2800,Main Store,true,20\n"
                "Rice 1kg,RC-001,85,Groceries,3200,3800,Unknown Store,false,15\n"
            ).encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            reverse("goods-bulk-upload"),
            {"file": upload},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Goods.objects.count(), 0)
        self.assertEqual(AuditLog.objects.filter(action="goods.bulk_upload").count(), 0)
        self.assertEqual(response.data["rows"][0]["row"], 3)
        self.assertIn("store", response.data["rows"][0]["errors"])


class SupplierAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.user = get_user_model().objects.create_user(
            username="owner",
            password="pass12345",
            first_name="Shop",
            last_name="Owner",
            phone_number="255700000001",
            email="owner@example.com",
            user_company=self.company,
        )
        self.shop_owner_group = Group.objects.create(name="shopowner")
        self.user.groups.add(self.shop_owner_group)
        self.client.force_authenticate(user=self.user)

    def test_shop_owner_can_create_supplier(self):
        response = self.client.post(
            reverse("suppliers"),
            {
                "supplier_name": "West Procurement Ltd",
                "contact_person": "Asha Selemani",
                "phone_number": "255700000002",
                "email": "procurement@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 1)


class GoodsAccessAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.user = get_user_model().objects.create_user(
            username="sales",
            password="pass12345",
            first_name="Sales",
            last_name="Person",
            phone_number="255700000008",
            email="sales@example.com",
            user_company=self.company,
        )
        self.user.groups.add(Group.objects.create(name="salesperson"))

        self.store = Store.objects.create(
            store_name="Sales Floor",
            company=self.company,
            store_location="City Center",
            store_supervisor=self.user,
            added_by=self.user,
        )
        self.goods_type = GoodsType.objects.create(
            goods_type="Beverages",
            company=self.company,
        )
        self.goods = Goods.objects.create(
            goods_name="Orange Juice 1L",
            goods_number="OJ-100",
            goods_quantity=18,
            goods_type=self.goods_type,
            buying_price=4000,
            lower_price_margin=5000,
            store=self.store,
            added_by=self.user,
        )
        self.client.force_authenticate(user=self.user)

    def test_salesperson_can_list_goods_for_order_creation(self):
        response = self.client.get(reverse("goods"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["result"][0]["goods_number"], "OJ-100")


class LeakageAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.other_company = Company.objects.create(
            company_name="Elsewhere Stores",
            company_location="Arusha",
            company_tin="987654321",
        )
        self.user = get_user_model().objects.create_user(
            username="keeper",
            password="pass12345",
            first_name="Store",
            last_name="Keeper",
            phone_number="255700000003",
            email="keeper@example.com",
            user_company=self.company,
        )
        self.user.groups.add(Group.objects.create(name="storekeeper"))
        self.client.force_authenticate(user=self.user)

        self.store = Store.objects.create(
            store_name="Main Store",
            company=self.company,
            store_location="City Center",
            store_supervisor=self.user,
            added_by=self.user,
        )
        self.other_store = Store.objects.create(
            store_name="Other Store",
            company=self.other_company,
            store_location="Uzunguni",
            store_supervisor=self.user,
            added_by=self.user,
        )
        self.goods_type = GoodsType.objects.create(
            goods_type="Groceries",
            company=self.company,
        )
        self.goods = Goods.objects.create(
            goods_name="Blue Band 500g",
            goods_number="BB-500",
            goods_quantity=20,
            goods_type=self.goods_type,
            buying_price=2400,
            lower_price_margin=2800,
            store=self.store,
            added_by=self.user,
        )
        self.other_goods_type = GoodsType.objects.create(
            goods_type="Electronics",
            company=self.other_company,
        )
        self.other_goods = Goods.objects.create(
            goods_name="Radio",
            goods_number="RD-100",
            goods_quantity=10,
            goods_type=self.other_goods_type,
            buying_price=12000,
            lower_price_margin=15000,
            store=self.other_store,
            added_by=self.user,
        )

    def test_create_leakage_updates_stock(self):
        response = self.client.post(
            reverse("leakage"),
            {
                "goods": self.goods.id,
                "amount_broken": 3,
                "leakage_summary": "Broken during unloading",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Leakage.objects.count(), 1)
        self.goods.refresh_from_db()
        self.assertEqual(self.goods.goods_quantity, 17)

    def test_cannot_create_leakage_for_other_company_goods(self):
        response = self.client.post(
            reverse("leakage"),
            {
                "goods": self.other_goods.id,
                "amount_broken": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("goods", response.data)
        self.assertEqual(Supplier.objects.get().company, self.company)
        self.assertEqual(Supplier.objects.get().added_by, self.user)

    def test_shop_owner_with_additional_groups_can_create_supplier(self):
        self.user.groups.add(Group.objects.create(name="cashier"))

        response = self.client.post(
            reverse("suppliers"),
            {
                "supplier_name": "Second Supplier",
                "contact_person": "Asha Selemani",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_user_with_group_supplier_permission_can_create_supplier(self):
        cashier_user = get_user_model().objects.create_user(
            username="cashier-user",
            password="pass12345",
            first_name="Cash",
            last_name="ier",
            phone_number="255700000009",
            email="cashier-user@example.com",
            user_company=self.company,
        )
        cashier_group = Group.objects.create(name="cashier-with-supplier-perm")
        cashier_group.permissions.add(Permission.objects.get(codename="add_supplier"))
        cashier_user.groups.add(cashier_group)
        self.client.force_authenticate(user=cashier_user)

        response = self.client.post(
            reverse("suppliers"),
            {
                "supplier_name": "Permission Supplier",
                "contact_person": "Asha Selemani",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.filter(supplier_name="Permission Supplier").count(), 1)
