from .filters import *
from .serializers import *
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters


import database.models


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = database.models.Customer.objects.all()
    serializer_class = CustomerSerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = database.models.Supplier.objects.all()
    serializer_class = SupplierSerializer


class SourceViewSet(viewsets.ModelViewSet):
    queryset = database.models.Source.objects.all()
    serializer_class = SourceSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = database.models.Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = database.models.Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = (filters.DjangoFilterBackend, OrderingFilter,)
    filter_fields = ('hide_product', 'supplier')
    ordering_fileds = ('name_sort',)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = database.models.Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_class = InvoiceFilter


class CreditPaymentsViewSet(viewsets.ModelViewSet):
    queryset = database.models.InvoiceCreditPayment.objects.all()
    serializer_class = InvoiceCreditPaymentSerializer
    filter_fields = ('invoice',)
