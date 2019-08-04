from .filters import *
from .serializers import *

import io
import os
import sys
import json
import xlwt
import xlrd
import tarfile
import tempfile
import datetime

from rest_framework import viewsets
from rest_framework.exceptions import ParseError
from rest_framework.filters import OrderingFilter
from django_filters import rest_framework as filters

from django.db import models, transaction
from django.core import management
from django.http import HttpResponse, HttpResponseBadRequest, FileResponse
from django.db.models import Sum, ExpressionWrapper, F, Case, When
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear, ExtractDay

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


class SalesProductsViewSet(viewsets.ModelViewSet):
    serializer_class = SalesProductsSerializer
    http_method_names = ('get')

    def get_object(self, queryset=None):
        if self.request.query_params.get("id"):
            if queryset is None:
                queryset = self.get_queryset()

            return queryset.aggregate(units=Sum('quantity'), sales=Sum('_sales'), profit=Sum('_profit'))
        else:
            return super(SalesProductsViewSet, self).get_object()

    def get_queryset(self):
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        product = self.request.query_params.get("id")
        group_by = self.request.query_params.get("group_by", "product")
        date_end = self.request.query_params.get("date_end")
        date_start = self.request.query_params.get("date_start")

        # Format group_by param into list
        group_by_params = []
        for param in group_by.split(','):
            group_by_params.append(param.strip())

        # Validate group_by params
        if "customer" in group_by_params and not product:
            raise ParseError("Provide product ID to group by customers")

        # Initial queryset
        queryset = database.models.InvoiceProduct.objects.totals().select_related('invoice')

        # Handle product filter
        if product:
            queryset = queryset.filter(product=product)

        # Handle date range filters
        if month:
            if not year:
                raise ParseError("Provide year for month {0}".format(month))
            queryset = queryset.filter(invoice__date_of_sale__month=month, invoice__date_of_sale__year=year)
        elif year:
            queryset = queryset.filter(invoice__date_of_sale__year=year)
        elif date_start and date_end:
            queryset = queryset.filter(invoice__date_of_sale__range=(date_start, date_end))
        else:
            raise ParseError("Must provide a month, year or custom date range")

        queryset = queryset.annotate(credit=F('invoice__credit'), customer=F('invoice__customer'))\
                           .annotate(month=ExtractMonth('invoice__date_of_sale'), year=ExtractYear('invoice__date_of_sale'),
                                     day=ExtractDay('invoice__date_of_sale'))\
                           .annotate(cratio=Coalesce(F('payments_total') / F('invoice_total'), 0.0))\
                           .annotate(product_sales=ExpressionWrapper((F('quantity') - F('returned_quantity')) * F('sell_price'),
                                                        output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                           .annotate(product_profit=ExpressionWrapper((F('quantity') - F('returned_quantity')) * (F('sell_price') - F('cost_price')),
                                                          output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                           .annotate(_sales=Sum(Case(When(credit=True, then=F('product_sales') * F('cratio')), default='product_sales',
                                                output_field=models.DecimalField(max_digits=15, decimal_places=3))))\
                           .annotate(_profit=Sum(Case(When(credit=True, then=F('product_profit') * F('cratio')), default='product_profit',
                                                output_field=models.DecimalField(max_digits=15, decimal_places=3))))\
                           .values(*group_by_params)\
                           .annotate(sales=F('_sales'), profit=F('_profit'), units=Sum(F('quantity') - F('returned_quantity')))\
                           .order_by(*group_by_params)

        return queryset


class SalesTotalViewSet(viewsets.ModelViewSet):
    serializer_class = SalesTotalSerializer
    filterset_class = SalesTotalFilter
    http_method_names = ('get')

    def get_queryset(self):
        queryset = database.models.Invoice.objects
        queryset = queryset.annotate(month=ExtractMonth('date_of_sale'), year=ExtractYear('date_of_sale'))\
                           .annotate(cratio=Coalesce(F('payments_total') / F('invoice_total'), 0.0))\
                           .annotate(_sales=Sum(Case(When(credit=True, then=Coalesce(F('payments_total'), 0.0)),
                                                          default='invoice_total')))\
                           .annotate(_profit=Sum(Case(When(credit=True, then=F('profit_total') * F('cratio')),
                                                           default='profit_total')))\
                           .values('year', 'month')\
                           .annotate(sales=F('_sales'), profit=F('_profit'))\
                           .order_by('year', 'month')
        return queryset


class SalesCategorySourceViewSet(viewsets.ModelViewSet):
    serializer_class = SalesCategorySourceSerializer
    filterset_class = SalesCategorySourceFilter
    http_method_names = ('get')

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
                        .values('year', 'month', 'requested_type')\
                        .annotate(sales=F('_sales'), profit=F('_profit'))\
                        .order_by('year', 'month', 'requested_type')
        return queryset


class BackupDbViewSet(viewsets.ModelViewSet):
    http_method_names = ('get')

    def list(self, request):
        response = tempfile.NamedTemporaryFile(delete=False)
        archive = tarfile.open(fileobj=response, mode='w:gz')

        fixtures = [('database.Category', 'categories.json'), ('database.Source', 'sources.json'),
                    ('database.Supplier', 'suppliers.json'), ('database.Product', 'products.json'),
                    ('database.Customer', 'customers.json'), ('database.Invoice', 'invoices.json'),
                    ('database.InvoiceProduct', 'invoice_products.json'),
                    ('database.InvoiceCreditPayment', 'payments.json')]

        for fixture, filename in fixtures:
            buf = io.StringIO()
            management.call_command('dumpdata', fixture, indent=2, format='json', stdout=buf)
            buf.seek(0)
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(buf.getvalue())
            archive.addfile(tarinfo, fileobj=io.BytesIO(buf.getvalue().encode('utf-8')))
            buf.close()

        archive.close()

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        filename = "backup_{}.tar.gz".format(today)
        return FileResponse(open(response.name, 'rb'), filename=filename, as_attachment=True)


class RestoreDbViewSet(viewsets.ModelViewSet):
    http_method_names = ('post')

    FIXTURES = ["customers.json", "categories.json", "sources.json", "suppliers.json", "products.json",
                "invoices.json", "invoice_products.json", "payments.json"]

    def create(self, request):
        file = request.FILES.get('file', None)

        if not file:
            return HttpResponseBadRequest("No file received")

        try:
            archive = tarfile.open(fileobj=file, mode='r')
        except tarfile.ReadError as e:
            return HttpResponseBadRequest("File is not a .tar.gz file")

        # Verify we have all the right files
        expected = self.FIXTURES.copy()
        for fixture in archive.getnames():
            if fixture in expected:
                expected.remove(fixture)
            else:
                return HttpResponseBadRequest("Unexpected file '{0}'".format(fixture))
        if expected:
            return HttpResponseBadRequest("Missing files: {0}".format(','.join(expected)))

        # Convert binary files to json which also verifies if the files are valid json
        fixtures_json = []
        for fixture in self.FIXTURES:
            file = archive.extractfile(fixture)

            try:
                file_dict = json.loads(file.read().decode('utf-8'))
            except json.decoder.JSONDecodeError:
                return HttpResponseBadRequest("File {0} may be corrupted".format(fixture))

            fixtures_json.append(file_dict)

        # Flush db
        management.call_command('flush', verbosity=0, interactive=False)

        # Load data into db
        response = ""
        for fixture in fixtures_json:
            temp = tempfile.NamedTemporaryFile(delete=False)
            with open(temp.name, mode='w') as f:
                json.dump(fixture, f)

            output = io.StringIO()
            os.rename(temp.name, "{0}.json".format(temp.name))
            management.call_command('loaddata', temp.name, stdout=output)

            objects_restored = output.getvalue().split(' ')[1]
            fixture_name = fixture[0]["model"].split('.')[1].lower()
            response += "\n" + "Restored {0} {1} items".format(objects_restored, fixture_name)

        return HttpResponse(response)


class StockXlsViewSet(viewsets.ModelViewSet):
    http_method_names = ('get', 'post')

    def list(self, request):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = "attachment; filename=stock-{0}.xls".format(today)

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

        # Sheet body, remaining rows
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
            return HttpResponseBadRequest("No file received")

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
                    return HttpResponseBadRequest("Table must have at least one of 'Stock', 'Sell Price' or \
                                                  'Cost Price' as columns")

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
