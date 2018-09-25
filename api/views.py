from .filters import *
from .serializers import *

from django.db import models
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters

from django.db.models import Sum, ExpressionWrapper, F, Case, When
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
    filterset_fields = ('hide_product', 'supplier')
    ordering_fileds = ('name_sort',)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    filterset_class = InvoiceFilter

    def get_queryset(self):
        queryset = database.models.Invoice.objects.all()
        queryset = self.get_serializer_class().setup_eager_loading(queryset)
        return queryset


class CreditPaymentsViewSet(viewsets.ModelViewSet):
    queryset = database.models.InvoiceCreditPayment.objects.all()
    serializer_class = InvoiceCreditPaymentSerializer
    filterset_fields = ('invoice',)


class SalesTotalViewSet(viewsets.ModelViewSet):
    serializer_class = SalesTotalSerializer
    filterset_class = SalesTotalFilter

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

class SalesCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = SalesCategorySerializer
    filterset_class = SalesCategoryFilter

    def get_queryset(self):
        queryset = database.models.InvoiceProduct.objects.totals().select_related('product', 'invoice')\
                        .annotate(credit=F('invoice__credit'), category=F('product__category'),
                                  month=ExtractMonth(F('invoice__date_of_sale')), year=ExtractYear(F('invoice__date_of_sale')))\
                        .annotate(cratio=Coalesce(F('payments_total') / F('invoice_total'), 0.0))\
                        .annotate(product_sales=ExpressionWrapper((F('quantity') - F('returned_quantity')) * F('sell_price'),
                                                                    output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                        .annotate(product_profit=ExpressionWrapper((F('quantity') - F('returned_quantity')) * (F('sell_price') - F('cost_price')),
                                                                    output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                        .annotate(_sales=Sum(Case(When(credit=True, then=F('product_sales') * F('cratio')), default='product_sales',
                                                output_field=models.DecimalField(max_digits=15, decimal_places=3))))\
                        .annotate(_profit=Sum(Case(When(credit=True, then=F('product_profit') * F('cratio')), default='product_profit',
                                                output_field=models.DecimalField(max_digits=15, decimal_places=3))))\
                        .values('category', 'year', 'month', '_sales', '_profit')\
                        .annotate(sales=F('_sales'), profit=F('_profit'))\
                        .values('category', 'year', 'month', 'sales', 'profit')\
                        .order_by('year', 'month', 'category')
        return queryset
