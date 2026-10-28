"""
URL configuration for store_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.urls import include, path, re_path

try:
    from rest_framework import permissions
    from drf_yasg import openapi
    from drf_yasg.views import get_schema_view
except ImportError:
    schema_view = None
else:
    schema_view = get_schema_view(
        openapi.Info(
            title="Jensen Stores API",
            default_version="v1",
            description="API documentation for authentication, stock management, and order workflows.",
            contact=openapi.Contact(email="support@jensenstores.local"),
        ),
        public=True,
        permission_classes=(permissions.AllowAny,),
    )

urlpatterns = [
    path("admin/", admin.site.urls),
    path("jensen/auth/", include('user_management.urls')),
    path("jensen/stock/", include('stock_management.urls')),
    path("jensen/order/", include('order_management.urls')),
]

if schema_view is not None:
    urlpatterns = [
        path("admin/", admin.site.urls),
        re_path(
            r"^swagger(?P<format>\.json|\.yaml)$",
            schema_view.without_ui(cache_timeout=0),
            name="schema-json",
        ),
        path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
        path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
        path("jensen/auth/", include('user_management.urls')),
        path("jensen/stock/", include('stock_management.urls')),
        path("jensen/order/", include('order_management.urls')),
    ]

urlpatterns+=staticfiles_urlpatterns()
