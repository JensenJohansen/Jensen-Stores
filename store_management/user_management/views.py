from django.shortcuts import render
from .serializers import *
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
            login(request,user)
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



class CompanyCreateAPIView(ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            company = serializer.save()
            company = self.serializer_class(company)
            return Response(data=company.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)


class CompanyRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'


class AppUserCreateAPIView(CreateAPIView):
    queryset = AppUser.objects.all()
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication,TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=self.request.data)
        if serializer.is_valid(raise_exception=True):
            user = self.serializer_class(serializer.save(validated_data=self.request.data))
            return Response(data=user.data, status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
