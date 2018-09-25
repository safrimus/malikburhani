from django_filters import rest_framework as filters

import database.models


class InvoiceFilter(filters.FilterSet):
    product_name = filters.CharFilter(field_name='products__product__name', distinct=True, lookup_expr='icontains')
    customer_name = filters.CharFilter(field_name='customer__name', distinct=True, lookup_expr='icontains')

    class Meta:
        model = database.models.Invoice
        fields = {
            'created': ['lte', 'gte'],
            'date_of_sale': ['lte', 'gte'],
            'credit': ['exact',],
            'id': ['exact',],
        }


class SalesTotalFilter(filters.FilterSet):
    year = filters.NumberFilter(method='filter_year')

    class Meta:
        model = database.models.Invoice
        # Exclude all fields from Invoice model
        exclude = ('id', 'created', 'date_of_sale', 'credit', 'customer')

    def filter_year(self, queryset, name, value):
        if value:
            queryset = queryset.filter(year=value)
        return queryset


class SalesCategoryFilter(filters.FilterSet):
    year = filters.NumberFilter(method='filter_year')
    category = filters.NumberFilter(method='filter_category')

    class Meta:
        model = database.models.InvoiceProduct
        # Exclude all fields from InvoiceProduct model
        exclude = ('id', 'invoice', 'product', 'quantity', 'sell_price', 'cost_price', 'returned_quantity')

    def filter_year(self, queryset, name, value):
        if value:
            queryset = queryset.filter(year=value)
        return queryset

    def filter_category(self, queryset, name, value):
        if value:
            queryset = queryset.filter(category=value)
        return queryset
