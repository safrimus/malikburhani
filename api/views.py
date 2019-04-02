from .filters import *
from .serializers import *

import xlwt
import xlrd
import datetime

from rest_framework import viewsets
from rest_framework.exceptions import ParseError
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters

from django.db import models, transaction
from django.http import HttpResponse, HttpResponseBadRequest
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
    filterset_class = ProductFilter
    ordering_fields = ('name_sort', 'description_sort', 'size_sort')


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


class SalesCategorySourceViewSet(viewsets.ModelViewSet):
    serializer_class = SalesCategorySourceSerializer
    filterset_class = SalesCategorySourceFilter

    def get_queryset(self):
        request_type = self.request.query_params.get("type");

        if request_type not in ["category", "source"]:
            raise ParseError("Type must be either 'category' or 'source'")

        queryset = database.models.InvoiceProduct.objects.totals().select_related('product', 'invoice')\
                        .annotate(credit=F('invoice__credit'), requested_type=F('product__' + request_type),
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
                        .values('requested_type', 'year', 'month', '_sales', '_profit')\
                        .annotate(sales=F('_sales'), profit=F('_profit'))\
                        .values('requested_type', 'year', 'month', 'sales', 'profit')\
                        .order_by('year', 'month', 'requested_type')
        return queryset


class StockXlsViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', 'post')

    def list(self, request):
        now = datetime.datetime.now()
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = "attachment; filename=stock-{0}.xls".format(now.strftime("%Y-%m-%d"))

        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Stock')

        # Sheet header, first row
        row_num = 0

        font_style = xlwt.XFStyle()
        font_style.font.bold = True

        columns = ['ID', 'Product Name', 'Description', 'Size', 'Stock', 'Cost Price', 'Sell Price', 'Supplier',
                   'Source', 'Category']

        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num], font_style)

        #Sheet body, remaining rows
        font_style = xlwt.XFStyle()

        hide_product = request.query_params.get("hide_product");
        if hide_product is None:
            products = database.models.Product.objects.all()
        else:
            products = database.models.Product.objects.filter(hide_product=hide_product)

        rows = products.values_list('id', 'name', 'description', 'size', 'stock', 'cost_price', 'sell_price',
                                    'supplier__company', 'source__name', 'category__name')

        for row in rows:
            row_num += 1
            for col_num in range(len(row)):
                ws.write(row_num, col_num, row[col_num], font_style)

        wb.save(response)
        return response

    def create(self, request):
        file = request.FILES.get('file', None)

        if not file:
            HttpResponseBadRequest("No file received")

        wb = xlrd.open_workbook(file_contents=file.read())
        sheet = wb.sheet_by_index(0);

        # Get the first row of the table and the columns indices we want to update
        cols = dict()
        start_row = 0
        for row in range(sheet.nrows):
            if sheet.cell(row, 0).value == "ID":
                start_row = row + 1

                for col in range(sheet.ncols):
                    if sheet.cell(row, col).value in ["Stock", "Cost Price", "Sell Price"]:
                        cols[sheet.cell(row, col).value] = col

                if not cols:
                    HttpResponseBadRequest("Table must have at least one of 'Stock', 'Sell Price' or 'Cost Price' \
                                            as columns")

                break
        else:
            return HttpResponseBadRequest("'ID' column not found in spreadsheet")


        # Update the products
        with transaction.atomic():
            for row in range(start_row, sheet.nrows):
                try:
                    product = database.models.Product.objects.get(id=sheet.cell(row, 0).value)
                except database.models.Product.DoesNotExist:
                    continue

                for col_name, col in cols.items():
                    field = col_name.lower().replace(' ', '_')
                    setattr(product, field, sheet.cell(row, col).value)
                    product.save()

        return HttpResponse()
