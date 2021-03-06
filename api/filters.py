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
    last_invoice_only = filters.BooleanFilter(method='filter_last_invoice')
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

    def filter_last_invoice(self, queryset, name, value):
        if value:
            last_id = queryset.latest('id').id
            queryset = queryset.filter(id=last_id)
        return queryset
