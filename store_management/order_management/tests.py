from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from order_management.models import Order, OrderAuthorizationStatus
from stock_management.models import Goods, GoodsType, Store
from user_management.models import Company, Customer


class OrderStatusEnumTests(APITestCase):
    def test_order_status_choices_are_system_defined(self):
        self.assertEqual(
            [value for value, _label in OrderAuthorizationStatus.choices],
            [
                "pending",
                "approved",
                "partially_paid",
                "paid",
                "rejected",
                "cancelled",
            ],
        )


class OrderApprovalAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.salesperson = get_user_model().objects.create_user(
            username="sales",
            password="pass12345",
            first_name="Sales",
            last_name="Person",
            phone_number="255700000011",
            email="sales@example.com",
            user_company=self.company,
        )
        self.cashier = get_user_model().objects.create_user(
            username="cashier",
            password="pass12345",
            first_name="Cash",
            last_name="ier",
            phone_number="255700000012",
            email="cashier@example.com",
            user_company=self.company,
        )
        self.salesperson.groups.add(Group.objects.create(name="salesperson"))
        self.cashier.groups.add(Group.objects.create(name="cashier"))

        self.store = Store.objects.create(
            store_name="Main Store",
            company=self.company,
            store_location="City Center",
            store_supervisor=self.salesperson,
            added_by=self.salesperson,
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
            added_by=self.salesperson,
        )

        self.order = Order.objects.create(
            creator=self.salesperson,
            authorization_status=OrderAuthorizationStatus.PENDING,
            order_caption="Walk-in customer",
        )

    def test_cashier_can_approve_order_with_status_string_only(self):
        self.client.force_authenticate(user=self.cashier)

        response = self.client.put(
            reverse("single_order", args=[self.order.order_no]),
            {"authorization_status": "approved"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.authorization_status, OrderAuthorizationStatus.APPROVED)


class OrderCustomerAPITests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456789",
        )
        self.other_company = Company.objects.create(
            company_name="Other Stores",
            company_location="Arusha",
            company_tin="987654321",
        )
        self.salesperson = get_user_model().objects.create_user(
            username="sales",
            password="pass12345",
            first_name="Sales",
            last_name="Person",
            phone_number="255700000021",
            email="sales@example.com",
            user_company=self.company,
        )
        self.salesperson.groups.add(Group.objects.create(name="salesperson"))

        self.store = Store.objects.create(
            store_name="Main Store",
            company=self.company,
            store_location="City Center",
            store_supervisor=self.salesperson,
            added_by=self.salesperson,
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
            added_by=self.salesperson,
        )
        self.customer = Customer.objects.create(
            customer_username="Aisha Nabirye",
            customer_phone="+255700000031",
            customer_company=self.company,
        )
        self.other_customer = Customer.objects.create(
            customer_username="Foreign Customer",
            customer_phone="+255700000032",
            customer_company=self.other_company,
        )
        self.client.force_authenticate(user=self.salesperson)

    def test_create_order_with_registered_customer(self):
        response = self.client.post(
            reverse("create_order"),
            {
                "order_caption": "Weekly wholesale order",
                "customer": self.customer.id,
                "order_goods": [
                    {"goods": self.goods.id, "goods_quantity": 2, "price": 3000}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["customer"], self.customer.id)
        self.assertEqual(response.data["customer_name"], self.customer.customer_username)
        self.assertEqual(response.data["customer_phone"], str(self.customer.customer_phone))

    def test_create_order_with_unregistered_customer_name(self):
        response = self.client.post(
            reverse("create_order"),
            {
                "order_caption": "Walk-in sale",
                "customer_name": "Walk-in customer",
                "order_goods": [
                    {"goods": self.goods.id, "goods_quantity": 1, "price": 3000}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["customer"])
        self.assertEqual(response.data["customer_name"], "Walk-in customer")
        self.assertIsNone(response.data["customer_phone"])

    def test_update_order_switches_to_unregistered_customer(self):
        order = Order.objects.create(
            creator=self.salesperson,
            authorization_status=OrderAuthorizationStatus.PENDING,
            order_caption="Existing order",
            customer=self.customer,
            customer_name=self.customer.customer_username,
        )

        response = self.client.put(
            reverse("single_order", args=[order.order_no]),
            {
                "customer": None,
                "customer_name": "Counter customer",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertIsNone(order.customer)
        self.assertEqual(order.customer_name, "Counter customer")

    def test_rejects_customer_from_another_company(self):
        response = self.client.post(
            reverse("create_order"),
            {
                "order_caption": "Weekly wholesale order",
                "customer": self.other_customer.id,
                "order_goods": [
                    {"goods": self.goods.id, "goods_quantity": 2, "price": 3000}
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("customer", response.data)


class StorekeeperOrderVisibilityTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="123456700",
        )
        self.salesperson = get_user_model().objects.create_user(
            username="sales-master",
            password="pass12345",
            first_name="Sales",
            last_name="Lead",
            phone_number="255700000101",
            email="sales-master@example.com",
            user_company=self.company,
        )
        self.storekeeper = get_user_model().objects.create_user(
            username="keeper-one",
            password="pass12345",
            first_name="Store",
            last_name="Keeper",
            phone_number="255700000102",
            email="keeper-one@example.com",
            user_company=self.company,
        )
        self.other_storekeeper = get_user_model().objects.create_user(
            username="keeper-two",
            password="pass12345",
            first_name="Other",
            last_name="Keeper",
            phone_number="255700000103",
            email="keeper-two@example.com",
            user_company=self.company,
        )
        self.salesperson.groups.add(Group.objects.create(name="salesperson"))
        self.storekeeper.groups.add(Group.objects.create(name="storekeeper"))
        self.other_storekeeper.groups.add(Group.objects.get(name="storekeeper"))

        self.store_a = Store.objects.create(
            store_name="Store A",
            company=self.company,
            store_location="Kinondoni",
            store_supervisor=self.storekeeper,
            added_by=self.salesperson,
        )
        self.store_b = Store.objects.create(
            store_name="Store B",
            company=self.company,
            store_location="Ilala",
            store_supervisor=self.other_storekeeper,
            added_by=self.salesperson,
        )
        self.goods_type = GoodsType.objects.create(goods_type="Hardware", company=self.company)
        self.goods_a = Goods.objects.create(
            goods_name="Ceiling Fan",
            goods_number="CF-1",
            goods_quantity=12,
            goods_type=self.goods_type,
            buying_price=40000,
            lower_price_margin=45000,
            store=self.store_a,
            added_by=self.salesperson,
        )
        self.goods_b = Goods.objects.create(
            goods_name="Water Pump",
            goods_number="WP-2",
            goods_quantity=8,
            goods_type=self.goods_type,
            buying_price=70000,
            lower_price_margin=75000,
            store=self.store_b,
            added_by=self.salesperson,
        )

        self.visible_order = Order.objects.create(
            creator=self.salesperson,
            authorization_status=OrderAuthorizationStatus.APPROVED,
            order_caption="Mixed-store order",
        )
        self.hidden_order = Order.objects.create(
            creator=self.salesperson,
            authorization_status=OrderAuthorizationStatus.APPROVED,
            order_caption="Other-store order",
        )

        self.visible_line = self.visible_order.order_goods.create(
            goods=self.goods_a,
            goods_quantity=2,
            price=50000,
        )
        self.foreign_line = self.visible_order.order_goods.create(
            goods=self.goods_b,
            goods_quantity=1,
            price=82000,
        )
        self.hidden_order.order_goods.create(
            goods=self.goods_b,
            goods_quantity=1,
            price=82000,
        )

    def test_storekeeper_only_lists_orders_for_supervised_store(self):
        self.client.force_authenticate(user=self.storekeeper)

        response = self.client.get(reverse("create_order"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order_numbers = [row["order_no"] for row in response.data["results"]]
        self.assertIn(self.visible_order.order_no, order_numbers)
        self.assertNotIn(self.hidden_order.order_no, order_numbers)

    def test_storekeeper_order_detail_only_returns_goods_lines_for_supervised_store(self):
        self.client.force_authenticate(user=self.storekeeper)

        response = self.client.get(reverse("single_order", args=[self.visible_order.order_no]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["order_goods_details"]), 1)
        self.assertEqual(response.data["order_goods_details"][0]["id"], self.visible_line.id)

    def test_storekeeper_can_issue_only_goodsorder_from_supervised_store(self):
        self.client.force_authenticate(user=self.storekeeper)

        response = self.client.patch(
            reverse("single_goods_order", args=[self.visible_line.id]),
            {"goods_issue": {"issued_status": True, "goods_quantity": self.visible_line.goods_quantity}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.visible_line.refresh_from_db()
        self.goods_a.refresh_from_db()
        self.assertTrue(self.visible_line.issued_status)
        self.assertEqual(self.visible_line.issuer_id, self.storekeeper.id)
        self.assertEqual(self.goods_a.goods_quantity, 10)

    def test_storekeeper_cannot_issue_goodsorder_from_other_store(self):
        self.client.force_authenticate(user=self.storekeeper)

        response = self.client.patch(
            reverse("single_goods_order", args=[self.foreign_line.id]),
            {"goods_issue": {"issued_status": True, "goods_quantity": self.foreign_line.goods_quantity}},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
