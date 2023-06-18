from django.shortcuts import render
from .serializers import *
from rest_framework.generics import *
from knox.views import LoginView as KnoxLoginView
from rest_framework.authentication import BasicAuthentication,SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import *

class LoginView(KnoxLoginView):
    authentication_classes = [BasicAuthentication]


class CompanyCreateAPIView(ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer=self.serializer_class(data= self.request.data)
        if serializer.is_valid(raise_exception=True):
            company=serializer.save(self.request.data)
            company=self.serializer_class(company)
            return Response(data=company.data,status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)


class CompanyRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'

class RoleCreateAPIView(ListCreateAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer=self.serializer_class(data= self.request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(data=serializer.data,status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)
        

class RoleRetrieveUpdateDestroyAPIView(RetrieveDestroyAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field='id'



class AppUserCreateAPIView(CreateAPIView):
    queryset = AppUser.objects.all()
    serializer_class = UserRegistrationSerializer
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer=self.serializer_class(data= self.request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(data=serializer.data,status=HTTP_201_CREATED)
        else:
            return Response(status=HTTP_304_NOT_MODIFIED)


