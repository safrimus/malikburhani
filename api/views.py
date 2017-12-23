from rest_framework import viewsets
from .serializers import *
from .filters import *

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
    filter_fields = ('hide_product',)


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = database.models.Invoice.objects.all()
    serializer_class = InvoiceSerializer
    filter_class = InvoiceFilter


class InvoiceProductViewSet(viewsets.ModelViewSet):
    queryset = database.models.InvoiceProduct.objects.all()
    serializer_class = InvoiceProductSerializer
