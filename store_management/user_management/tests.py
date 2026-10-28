from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from user_management.models import Company, Subscription, SubscriptionType
from user_management.role_permissions import get_or_create_configured_group
from user_management.serializers import CompanySerializer, LoginSerializer, UserSerializer


class UsersManagersTests(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(username="normal", password="foo")
        self.assertEqual(user.username, "normal")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username,"This is not right,Weka Jina")
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(username="")
        with self.assertRaises(ValueError):
            User.objects.create_user(username="", password="foo")

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(username="super", password="foo")
        self.assertEqual(admin_user.username, "super")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                username="super", password="foo", is_superuser=False)


class UserPermissionSerializerTests(TestCase):
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
        self.user.groups.add(Group.objects.create(name="shopowner"))

    def test_login_serializer_includes_effective_permissions(self):
        data = LoginSerializer(self.user).data

        self.assertIn("permissions", data)
        self.assertIn("all_permissions", data)
        self.assertIn("group_permissions", data)
        self.assertIn("role_permissions", data)
        self.assertIn("stock_management.add_supplier", data["permissions"])
        self.assertIn("stock_management.add_goodstype", data["permissions"])
        self.assertIn("stock_management.add_leakage", data["permissions"])
        self.assertTrue(data["role_permissions"]["can_manage_suppliers"])
        self.assertTrue(data["role_permissions"]["can_verify_purchase_orders"])

    def test_user_serializer_includes_role_flags_and_payment_scope(self):
        cashier = get_user_model().objects.create_user(
            username="cashier",
            password="pass12345",
            first_name="Cash",
            last_name="ier",
            phone_number="255700000002",
            email="cashier@example.com",
            user_company=self.company,
        )
        cashier.groups.add(Group.objects.create(name="cashier"))

        data = UserSerializer(cashier).data

        self.assertIn("permissions", data)
        self.assertIn("order_management.add_payment", data["permissions"])
        self.assertFalse(data["role_permissions"]["can_manage_suppliers"])
        self.assertTrue(data["role_permissions"]["can_manage_payments"])


class SubscriptionWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.today = timezone.localdate()
        self.trial_type, _ = SubscriptionType.objects.get_or_create(
            code="TRIAL",
            defaults={"name": "Trial", "duration_days": 30, "is_active": True, "is_default": True},
        )
        self.standard_type, _ = SubscriptionType.objects.get_or_create(
            code="STANDARD",
            defaults={"name": "Standard", "duration_days": 30, "is_active": True, "is_default": False},
        )
        self.professional_type, _ = SubscriptionType.objects.get_or_create(
            code="PROFESSIONAL",
            defaults={"name": "Professional", "duration_days": 45, "is_active": True},
        )
        self.ultimate_type, _ = SubscriptionType.objects.get_or_create(
            code="ULTIMATE",
            defaults={"name": "Ultimate", "duration_days": 60, "is_active": True},
        )
        self.trial_type.name = "Trial"
        self.trial_type.duration_days = 30
        self.trial_type.is_active = True
        self.trial_type.is_default = True
        self.trial_type.save()

        self.standard_type.name = "Standard"
        self.standard_type.duration_days = 30
        self.standard_type.is_active = True
        self.standard_type.is_default = False
        self.standard_type.save()

        self.professional_type.name = "Professional"
        self.professional_type.duration_days = 45
        self.professional_type.is_active = True
        self.professional_type.is_default = False
        self.professional_type.save()

        self.ultimate_type.name = "Ultimate"
        self.ultimate_type.duration_days = 60
        self.ultimate_type.is_active = True
        self.ultimate_type.is_default = False
        self.ultimate_type.save()

        self.company = Company.objects.create(
            company_name="Jensen Stores",
            company_location="Dar es Salaam",
            company_tin="SUB-001",
        )
        self.other_company = Company.objects.create(
            company_name="Jensen Wholesale",
            company_location="Arusha",
            company_tin="SUB-002",
        )

        User = get_user_model()
        self.owner = User.objects.create_user(
            username="owner",
            password="pass12345",
            first_name="Shop",
            last_name="Owner",
            phone_number="255700000101",
            email="owner@example.com",
            user_company=self.company,
        )
        self.owner.groups.add(get_or_create_configured_group("shopowner"))

        self.cashier = User.objects.create_user(
            username="cashier-user",
            password="pass12345",
            first_name="Cash",
            last_name="ier",
            phone_number="255700000102",
            email="cashier@example.com",
            user_company=self.company,
        )
        self.cashier.groups.add(get_or_create_configured_group("cashier"))

    def test_company_serializer_bootstraps_active_trial_subscription_and_owner(self):
        serializer = CompanySerializer(
            data={
                "company_name": "Trial Company",
                "company_location": "Mwanza",
                "company_tin": "TRIAL-001",
                "owner": {
                    "username": "trial-owner",
                    "password": "pass12345",
                    "first_name": "Trial",
                    "last_name": "Owner",
                    "phone_number": "255700000103",
                    "email": "trial-owner@example.com",
                },
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        company = serializer.save()

        subscription = Subscription.objects.get(company=company)
        owner = get_user_model().objects.get(username="trial-owner")

        self.assertEqual(subscription.type.code, "TRIAL")
        self.assertTrue(subscription.status)
        self.assertEqual(subscription.date_activated, self.today)
        self.assertEqual(subscription.expire_date, self.today + timedelta(days=30))
        self.assertTrue(owner.groups.filter(name="shopowner").exists())

    def test_company_serializer_uses_admin_default_subscription_type(self):
        self.professional_type.is_default = True
        self.professional_type.save()

        serializer = CompanySerializer(
            data={
                "company_name": "Pro Trial Company",
                "company_location": "Dodoma",
                "company_tin": "TRIAL-002",
                "owner": {
                    "username": "pro-owner",
                    "password": "pass12345",
                    "first_name": "Pro",
                    "last_name": "Owner",
                    "phone_number": "255700000104",
                    "email": "pro-owner@example.com",
                },
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        company = serializer.save()

        subscription = Subscription.objects.get(company=company)
        self.assertEqual(subscription.type.code, "PROFESSIONAL")
        self.assertEqual(subscription.expire_date, self.today + timedelta(days=45))

    def test_subscription_list_is_scoped_to_authenticated_users_company(self):
        Subscription.objects.create(
            company=self.company,
            type=self.standard_type,
            date_activated=self.today,
            expire_date=self.today + timedelta(days=7),
        )
        Subscription.objects.create(
            company=self.other_company,
            type=self.ultimate_type,
            date_activated=self.today,
            expire_date=self.today + timedelta(days=14),
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get("/jensen/auth/subscriptions/")
        payload = response.data["results"]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["company"], self.company.id)

    def test_subscription_list_refreshes_stale_status_flags(self):
        subscription = Subscription.objects.create(
            company=self.company,
            type=self.standard_type,
            date_activated=self.today,
            expire_date=self.today + timedelta(days=7),
        )
        Subscription.objects.filter(pk=subscription.pk).update(status=False)

        self.client.force_authenticate(self.owner)
        response = self.client.get("/jensen/auth/subscriptions/")

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.assertTrue(subscription.status)

    def test_cashier_cannot_create_subscription(self):
        self.client.force_authenticate(self.cashier)
        response = self.client.post(
            "/jensen/auth/subscriptions/",
            {
                "company": self.company.id,
                "type": "PROFESSIONAL",
                "date_activated": self.today.isoformat(),
                "expire_date": (self.today + timedelta(days=30)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_shopowner_cannot_create_overlapping_subscription(self):
        Subscription.objects.create(
            company=self.company,
            type=self.standard_type,
            date_activated=self.today,
            expire_date=self.today + timedelta(days=7),
        )

        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/jensen/auth/subscriptions/",
            {
                "company": self.company.id,
                "type": "ULTIMATE",
                "date_activated": (self.today + timedelta(days=3)).isoformat(),
                "expire_date": (self.today + timedelta(days=10)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("expire_date", response.data)

    def test_shopowner_cannot_create_subscription_with_reversed_dates(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            "/jensen/auth/subscriptions/",
            {
                "company": self.company.id,
                "type": "ULTIMATE",
                "date_activated": (self.today + timedelta(days=10)).isoformat(),
                "expire_date": (self.today + timedelta(days=1)).isoformat(),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("expire_date", response.data)
