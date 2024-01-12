from django.shortcuts import render
from .serializers import *
from .permissions import *
from rest_framework.generics import *
from knox.views import LoginView as KnoxLoginView
from knox.views import LogoutView as KnoxLogoutView
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework.status import *
from knox.auth import TokenAuthentication


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
    
class LogoutView(KnoxLogoutView):
    permission_classes=[IsAuthenticated]


class SubscriptionListView(ListCreateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    
class CompanyCreateAPIView(ListCreateAPIView):
    queryset = Company.objects.all().order_by('-id')
    serializer_class = CompanySerializer
    authentication_classes = [BasicAuthentication, TokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(data=serializer.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
    
    def get_serializer_context(self, id):
        subscription = Subscription.objects.values("type").filter(company=id)
        return subscription
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = CompanySerializer(queryset, many=True)
        #serializer.is_valid(raise_exception=True)
        serialized_data = serializer.data
        
        for company in serialized_data:
            sub = self.get_serializer_context(company["id"])
            if sub.exists():
                company['subscriptions'] = sub[0]["type"]
        
        return Response({'serialized_data':serialized_data})


class CompanyRetrieveUpdateDestroyAPIView(RetrieveUpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class AppUserCreateAPIView(ListCreateAPIView):
    queryset = AppUser.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated, IsShopOwner]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            user = self.serializer_class(serializer.save())
            return Response(data=user.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
    
    def get(self, request, *args, **kwargs):
        user_company = request.user.user_company
        print(user_company)
        filtered_data =  self.get_queryset().filter(user_company=user_company)
        serializer = self.serializer_class(filtered_data, many=True)
        serialized_data = serializer.data
        return Response(data=serialized_data,status=HTTP_200_OK)
    

class AppUserRetrieveEditView(RetrieveUpdateAPIView):
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
