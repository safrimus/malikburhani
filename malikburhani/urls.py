"""malikburhani URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from rest_framework import routers
from api import views


router = routers.DefaultRouter()
router.register(r'customers', views.CustomerViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'sources', views.SourceViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'payments', views.CreditPaymentsViewSet)
router.register(r'invoices', views.InvoiceViewSet, 'Invoice')
router.register(r'external/backup_db', views.BackupDbViewSet, 'Product')
router.register(r'external/restore_db', views.RestoreDbViewSet, 'Product')
router.register(r'external/stock', views.StockXlsViewSet, 'Product')
router.register(r'sales/total', views.SalesTotalViewSet, 'Invoice')
router.register(r'sales/category_source', views.SalesCategorySourceViewSet, 'InvoiceProduct')
router.register(r'sales/products', views.SalesProductsViewSet, 'InvoiceProduct')
router.register(r'sales/suppliers', views.SalesSuppliersViewSet, 'InvoiceProduct')
router.register(r'sales/customers', views.SalesCustomersViewSet, 'InvoiceProduct')
router.register(r'cashflow/total', views.CashflowTotalViewSet, 'Invoice')
router.register(r'stock/sold/total', views.StockSoldTotalViewSet, 'InvoiceProduct')


urlpatterns = [
	url(r'^api/v1/', include(router.urls)),
]
