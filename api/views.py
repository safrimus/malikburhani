from .filters import *
from .serializers import *

from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters

from django.db.models import Sum, F, Case, When
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear


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
    serializer_class = InvoiceSerializer
    filter_class = InvoiceFilter

    def get_queryset(self):
        queryset = database.models.Invoice.objects.all()
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset


class CreditPaymentsViewSet(viewsets.ModelViewSet):
    queryset = database.models.InvoiceCreditPayment.objects.all()
    serializer_class = InvoiceCreditPaymentSerializer
    filter_fields = ('invoice',)


class SalesTotalViewSet(viewsets.ModelViewSet):
    serializer_class = SalesTotalSerializer
    filter_class = SalesTotalFilter

    def get_queryset(self):
        queryset = database.models.Invoice.objects.annotate(month=ExtractMonth('date_of_sale'), year=ExtractYear('date_of_sale'))\
                                                  .annotate(cratio=Coalesce(F('payments_total') / F('invoice_total'), 0.0))\
                                                  .annotate(_sales=Sum(Case(
                                                                When(credit=True, then=Coalesce(F('payments_total'), 0.0)),
                                                                default='invoice_total',
                                                            )))\
                                                  .annotate(_profit=Sum(Case(
                                                                When(credit=True, then=F('profit_total') * F('cratio')),
                                                                default='profit_total',
                                                            )))\
                                                  .values('year', 'month', '_sales', '_profit')\
                                                  .annotate(sales=F('_sales'), profit=F('_profit'))\
                                                  .values('year', 'month', 'sales', 'profit')\
                                                  .order_by('year', 'month')
        return queryset
