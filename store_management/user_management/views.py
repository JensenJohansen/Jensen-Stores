from django.shortcuts import render
from .serializers import *
from .permissions import *
from django.utils.decorators import method_decorator
from rest_framework.generics import *
from knox.views import LoginView as KnoxLoginView
from knox.views import LogoutView as KnoxLogoutView
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.status import *
from knox.auth import TokenAuthentication
from django.utils import timezone
try:
    from drf_yasg.utils import swagger_auto_schema
except ImportError:
    def swagger_auto_schema(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
from store_management.swagger import (
    company_create_request_schema,
    login_request_schema,
    login_response_schema,
    wrapped_list_response_schema,
)


@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Authenticate a user and issue a Knox token",
        request_body=login_request_schema,
        responses={200: login_response_schema},
    ),
)
class LoginView(KnoxLoginView):
    authentication_classes = [BasicAuthentication]
    permission_classes=(AllowAny,)
    serializer_class=LoginSerializer
    
    def post(self, request,format=None):
        serializer=self.serializer_class(data=request.data)
        if serializer.is_valid(raise_exception=True):
            user=serializer.validated_data['user']
            login(request, user)
            response=super().post(request, format=None)
        else:
            Response({'errors':serializer.errors},status=HTTP_400_BAD_REQUEST)
            
        return Response({'data':response.data},status=HTTP_200_OK)
    
    def get_post_response_data(self, request, token, instance):
        data = {
            'expiry': self.format_expiry_datetime(instance.expiry),
            'token': token
        }
        if self.serializer_class is not None:
            data["user"] = self.serializer_class(
                request.user,
                context=self.get_context()
            ).data
        return data
    

@method_decorator(
    name="post",
    decorator=swagger_auto_schema(
        tags=["Authentication"],
        operation_summary="Invalidate the current Knox token",
        responses={204: "Token invalidated successfully."},
    ),
)
class LogoutView(KnoxLogoutView):
    permission_classes=[IsAuthenticated]


class SubscriptionListView(ListCreateAPIView):
    serializer_class = SubscriptionSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _sync_queryset_statuses(self, queryset):
        today = timezone.localdate()
        queryset.filter(status=True).exclude(
            date_activated__lte=today,
            expire_date__gte=today,
        ).update(status=False)
        queryset.filter(
            status=False,
            date_activated__lte=today,
            expire_date__gte=today,
        ).update(status=True)

    def get_queryset(self):
        queryset = Subscription.objects.select_related("company")

        if self.request.user.is_superuser:
            scoped = queryset
        else:
            company = getattr(self.request.user, "user_company", None)
            if company is None:
                return Subscription.objects.none()
            scoped = queryset.filter(company=company)

        self._sync_queryset_statuses(scoped)
        return scoped.order_by("-status", "-expire_date", "-date_activated", "-id")

    def perform_create(self, serializer):
        user = self.request.user
        if not (
            user.is_superuser
            or user.groups.filter(name__iexact="shopowner").exists()
        ):
            raise PermissionDenied("Only shop owners can manage subscriptions.")

        if user.is_superuser:
            serializer.save()
            return

        if user.user_company is None:
            raise PermissionDenied("Your account is not assigned to a company.")

        serializer.save(company=user.user_company)


class CustomerListCreateView(ListCreateAPIView):
    queryset = Customer.objects.all().order_by('-id')
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get_queryset(self):
        company = getattr(self.request.user, "user_company", None)
        if company is None:
            return self.queryset.none()
        return self.queryset.filter(customer_company=company)
    

class CustomerRetrieveUpdateDestroy(RetrieveUpdateDestroyAPIView):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated]
    lookup_field = "id"


class CompanyCreateAPIView(ListCreateAPIView):
    queryset = Company.objects.all().order_by('-id')
    serializer_class = CompanySerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        tags=["Company"],
        operation_summary="Register a company and bootstrap its owner account",
        request_body=company_create_request_schema,
        responses={201: CompanySerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(data=serializer.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
    
    def get_company_subscription(self, company_id):
        queryset = Subscription.objects.filter(company=company_id)
        today = timezone.localdate()
        queryset.filter(status=True).exclude(
            date_activated__lte=today,
            expire_date__gte=today,
        ).update(status=False)
        queryset.filter(
            status=False,
            date_activated__lte=today,
            expire_date__gte=today,
        ).update(status=True)
        return queryset.order_by("-status", "-expire_date", "-date_activated", "-id").values(
            "type__code",
            "status",
            "date_activated",
            "expire_date",
        ).first()
    
    @swagger_auto_schema(
        tags=["Company"],
        operation_summary="List companies with subscription details",
        responses={200: wrapped_list_response_schema("serialized_data")},
    )
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = CompanySerializer(queryset, many=True)
        serialized_data = serializer.data
        
        for company in serialized_data:
            sub = self.get_company_subscription(company["id"])
            if sub is not None:
                company["subscriptions"] = sub["type__code"]
                company["subscription_status"] = sub["status"]
                company["subscription_activated"] = sub["date_activated"]
                company["subscription_expires"] = sub["expire_date"]
        
        return Response({'serialized_data':serialized_data})


class CompanyRetrieveUpdateDestroyAPIView(RetrieveUpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class AppUserCreateAPIView(ListCreateAPIView):
    queryset = AppUser.objects.all().order_by("-id")
    serializer_class = UserSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Register a user for the current company",
        request_body=UserSerializer,
        responses={201: UserSerializer},
    )
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            user = self.serializer_class(serializer.save())
            return Response(data=user.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
    
    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="List users for the authenticated user's company",
        responses={200: UserSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        filtered_data =  self.get_queryset().filter(user_company=user_company)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response(data=serialized_data,status=HTTP_200_OK)
    

class AppUserRetrieveEditView(RetrieveUpdateDestroyAPIView):
    queryset = AppUser.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class ChangePasswordAPIView(RetrieveUpdateAPIView):
    queryset = AppUser.objects.all()
    serializer_class = ChangePasswordSerializer
    authentication_classes = [TokenAuthentication,]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Change a user's password",
        request_body=ChangePasswordSerializer,
        responses={200: ChangePasswordSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["Users"],
        operation_summary="Partially change a user's password",
        request_body=ChangePasswordSerializer,
        responses={200: ChangePasswordSerializer},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)
