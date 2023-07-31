from django.urls import path
from knox import views as knox_views
from .views import *

urlpatterns = [
        path(r'login/', LoginView.as_view(), name='knox_login'),
        path(r'logout/', LogoutView.as_view(), name='knox_logout'),
        path(r'logoutall/', knox_views.LogoutAllView.as_view(), name='knox_logoutall'),
        path("company/", CompanyCreateAPIView.as_view(), name="company"),
        path("company/<int:id>/", CompanyRetrieveUpdateDestroyAPIView.as_view(), name="company_single"),
        path("user_registration/", AppUserCreateAPIView.as_view(), name="user_registration"),
        path("user_edit/<int:id>/", AppUserRetrieveEditView.as_view(), name="user_edit"),
    ]