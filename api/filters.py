from django_filters import rest_framework as filters

import database.models


class InvoiceFilter(filters.FilterSet):
    product_name = filters.CharFilter(name='products__product__name', distinct=True, lookup_expr='icontains')
    customer_name = filters.CharFilter(name='customer__name', distinct=True, lookup_expr='icontains')

    class Meta:
        model = database.models.Invoice
        fields = {
            'created': ['lte', 'gte'],
            'date_of_sale': ['lte', 'gte'],
            'credit': ['exact',],
        }
