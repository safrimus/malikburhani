from django.db.models import F
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters

import database.models


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class ProductFilter(filters.FilterSet):
    name = filters.CharFilter(field_name='name', distinct=True, lookup_expr='istartswith')

    class Meta:
        model = database.models.Product
        fields = {
            'hide_product': ['exact',],
            'supplier': ['exact',],
        }


class InvoiceFilter(filters.FilterSet):
    unpaid_invoices = filters.BooleanFilter(method='filter_unpaid_invoices')
    product_name = filters.CharFilter(field_name='products__product__name', distinct=True, lookup_expr='istartswith')
    customer_name = filters.CharFilter(field_name='customer__name', distinct=True, lookup_expr='istartswith')

    class Meta:
        model = database.models.Invoice
        fields = {
            'created': ['lte', 'gte'],
            'date_of_sale': ['lte', 'gte'],
            'credit': ['exact',],
            'id': ['exact',],
        }

    def filter_unpaid_invoices(self, queryset, name, value):
        if value:
            queryset = queryset.filter(invoice_total__gt=Coalesce(F('payments_total'), 0.0))
        return queryset


class SalesTotalFilter(filters.FilterSet):
    year = NumberInFilter(method='filter_year')

    class Meta:
        model = database.models.Invoice
        # Exclude all fields from Invoice model
        exclude = ('id', 'created', 'date_of_sale', 'credit', 'customer')

    def filter_year(self, queryset, name, value):
        if value:
            queryset = queryset.filter(year__in=value)
        return queryset


class SalesCategorySourceFilter(filters.FilterSet):
    year = NumberInFilter(method='filter_year')
    requested_type = filters.NumberFilter(method='filter_requested_type')

    class Meta:
        model = database.models.InvoiceProduct
        # Exclude all fields from InvoiceProduct model
        exclude = ('id', 'invoice', 'product', 'quantity', 'sell_price', 'cost_price', 'returned_quantity')

    def filter_year(self, queryset, name, value):
        if value:
            queryset = queryset.filter(year__in=value)
        return queryset

    def filter_requested_type(self, queryset, name, value):
        if value:
            queryset = queryset.filter(requested_type=value)
        return queryset
