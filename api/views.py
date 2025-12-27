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

from django.db import models, transaction, connection
from django.core import management
from django.http import HttpResponse, HttpResponseBadRequest, FileResponse
from django.db.models import Sum, ExpressionWrapper, F, Case, When, Value
from django.db.models.functions import Coalesce, ExtractMonth, ExtractYear, ExtractDay

import database.models

# d = list(database.models.InvoiceProduct.objects.filter(product=389).values_list('invoice', flat=True))
# database.models.InvoiceProduct.objects.filter(Q(invoice__in=d), ~Q(product=389)).values('product').annotate(count=Count('product')).filter(count__gt=5)


def sales_per_type(type_name, field_lookup, params):
    ids = params.get("id");
    year = params.get("year")
    month = params.get("month")
    group_by = params.get("group_by")
    date_end = params.get("date_end")
    date_start = params.get("date_start")

    # Format id param into list
    ids_list = ids.split(',') if ids else []

    # Format group_by param into list
    group_by_params = group_by.split(',') if group_by else [type_name]

    # Validate group_by params
    if group_by_params and \
       any(param not in [type_name, "customer", "day", "month", "year"] for param in group_by_params):
        raise ParseError("Can only group by {0}, customer, day, month or year".format(type_name))
    if "customer" in group_by_params and not ids_list:
        raise ParseError("Provide ID to group by customer")
    if "day" in group_by_params and "month" not in group_by_params and not month:
        raise ParseError("Must group by both day and month when filtering by year or custom dates")
    if "month" in group_by_params and year and month:
        raise ParseError("Can not group by month when filtering by month")

    # Initial queryset
    queryset = database.models.InvoiceProduct.objects.totals().select_related('product', 'invoice')

    # Handle ids filter
    if ids_list:
        lookup = field_lookup + '__in'
        queryset = queryset.filter(**{lookup: ids_list})

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

    # Check for case where field already exists in the queryset i.e. product field
    if type_name != field_lookup:
        queryset = queryset.annotate(**{type_name: F(field_lookup)})

    # Do the query
    queryset = queryset.annotate(customer=F('invoice__customer'),
                                 month=ExtractMonth('invoice__date_of_sale'),
                                 year=ExtractYear('invoice__date_of_sale'),
                                 day=ExtractDay('invoice__date_of_sale'))\
                       .annotate(product_sales=ExpressionWrapper(
                           (F('quantity') - F('returned_quantity')) * F('sell_price'),
                               output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                       .annotate(product_profit=ExpressionWrapper(
                           (F('quantity') - F('returned_quantity')) * (F('sell_price') - F('cost_price')),
                               output_field=models.DecimalField(max_digits=15, decimal_places=3)))\
                       .annotate(_sales=Sum("product_sales"))\
                       .annotate(_profit=Sum("product_profit"))\
                       .values(*group_by_params)\
                       .annotate(sales=F('_sales'), profit=F('_profit'),
                                 units=Sum(F('quantity') - F('returned_quantity')))\
                       .order_by(*group_by_params)

    return queryset


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
    http_method_names = ('get')

    def get_queryset(self):
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        group_by = self.request.query_params.get("group_by")
        date_end = self.request.query_params.get("date_end")
        date_start = self.request.query_params.get("date_start")

        # Format group_by param into list
        group_by_params = group_by.split(',') if group_by else []

        # Validate group_by params
        if "day" in group_by_params and "month" not in group_by_params and not month:
            raise ParseError("Must group by both day and month when filtering by year or custom dates")
        if "month" in group_by_params and year and month:
            raise ParseError("Can not group by month when filtering by month")

        # Initial queryset
        queryset = database.models.Invoice.objects

        # Handle date range filters
        if month:
            if not year:
                raise ParseError("Provide year for month {0}".format(month))
            queryset = queryset.filter(date_of_sale__month=month, date_of_sale__year=year)
        elif year:
            queryset = queryset.filter(date_of_sale__year=year)
        elif date_start and date_end:
            queryset = queryset.filter(date_of_sale__range=(date_start, date_end))
        else:
            raise ParseError("Must provide a month, year or custom date range")

        queryset = queryset.annotate(month=ExtractMonth('date_of_sale'), year=ExtractYear('date_of_sale'),
                                     day=ExtractDay('date_of_sale'))

        if group_by_params:
            queryset = queryset.values(*group_by_params)\
                               .annotate(sales=Sum('invoice_total'), profit=Sum('profit_total'))\
                               .order_by(*group_by_params)
        else:
            queryset = queryset.annotate(_sales=Sum('invoice_total'), _profit=Sum('profit_total'))\
                               .values('_sales', '_profit')\
                               .annotate(sales=F('_sales'), profit=F('_profit'))\
                               .values('sales', 'profit')

        return queryset


class SalesCustomersViewSet(viewsets.ModelViewSet):
    serializer_class = SalesCustomersSerializer
    http_method_names = ('get')

    def get_queryset(self):
        ids = self.request.query_params.get("id");
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        group_by = self.request.query_params.get("group_by")
        date_end = self.request.query_params.get("date_end")
        date_start = self.request.query_params.get("date_start")

        # Format id param into list
        ids_list = ids.split(',') if ids else []

        # Format group_by param into list
        group_by_params = group_by.split(',') if group_by else ["customer"]

        # Validate group_by params
        if group_by_params and \
           any(param not in ["customer", "day", "month", "year"] for param in group_by_params):
            raise ParseError("Can only group by customer, day, month or year")
        if "day" in group_by_params and "month" not in group_by_params and not month:
            raise ParseError("Must group by both day and month when filtering by year or custom dates")
        if "month" in group_by_params and year and month:
            raise ParseError("Can not group by month when filtering by month")

        # Initial queryset
        queryset = database.models.Invoice.objects

        # Handle ids filter
        if ids_list:
            queryset = queryset.filter(customer__in=ids_list)

        # Handle date range filters
        if month:
            if not year:
                raise ParseError("Provide year for month {0}".format(month))
            queryset = queryset.filter(date_of_sale__month=month, date_of_sale__year=year)
        elif year:
            queryset = queryset.filter(date_of_sale__year=year)
        elif date_start and date_end:
            queryset = queryset.filter(date_of_sale__range=(date_start, date_end))
        else:
            raise ParseError("Must provide a month, year or custom date range")

        queryset = queryset.annotate(month=ExtractMonth('date_of_sale'), year=ExtractYear('date_of_sale'),
                                     day=ExtractDay('date_of_sale'))\
                           .values(*group_by_params)\
                           .annotate(sales=Sum('invoice_total'), profit=Sum('profit_total'))\
                           .order_by(*group_by_params)
        return queryset


class SalesProductsViewSet(viewsets.ModelViewSet):
    serializer_class = SalesProductsSerializer
    http_method_names = ('get')

    def get_queryset(self):
        return sales_per_type("product", "product", self.request.query_params)


class SalesCategorySourceViewSet(viewsets.ModelViewSet):
    serializer_class = SalesCategorySourceSerializer
    http_method_names = ('get')

    def get_queryset(self):
        type_name = self.request.query_params.get("type")

        # Validate type_name
        if type_name not in ["category", "source"]:
            raise ParseError("Type must be either 'category' or 'source'")

        return sales_per_type("requested_type", "product__" + type_name, self.request.query_params)


class SalesSuppliersViewSet(viewsets.ModelViewSet):
    serializer_class = SalesSuppliersSerializer
    http_method_names = ('get')

    def get_queryset(self):
        return sales_per_type("supplier", "product__supplier", self.request.query_params)


class CashflowTotalViewSet(viewsets.ModelViewSet):
    serializer_class = CashflowTotalSerializer
    http_method_names = ('get')

    def get_queryset(self):
        year = self.request.query_params.get("year")
        month = self.request.query_params.get("month")
        date_end = self.request.query_params.get("date_end")
        date_start = self.request.query_params.get("date_start")

        # Set group by field
        if year and month:
            group_by = "day"
        else:
            group_by = "month"

        # Initial querysets
        cash_invoices = database.models.Invoice.objects.filter(credit=False)
        payments = database.models.InvoiceCreditPayment.objects

        # Handle date range filters
        if month:
            if not year:
                raise ParseError("Provide year for month {0}".format(month))
            cash_invoices = cash_invoices.filter(date_of_sale__month=month, date_of_sale__year=year)
            payments = payments.filter(date_of_payment__month=month, date_of_payment__year=year)
        elif year:
            cash_invoices = cash_invoices.filter(date_of_sale__year=year)
            payments = payments.filter(date_of_payment__year=year)
        elif date_start and date_end:
            cash_invoices = cash_invoices.filter(date_of_sale__range=(date_start, date_end))
            payments = payments.filter(date_of_payment__range=(date_start, date_end))
        else:
            raise ParseError("Must provide a month, year or custom date range")

        cash_invoices = cash_invoices.annotate(month=ExtractMonth('date_of_sale'), year=ExtractYear('date_of_sale'),
                                               day=ExtractDay('date_of_sale'),
                                               type=Value("invoice", output_field=models.CharField()))\
                                     .values(group_by, "type")\
                                     .annotate(cash=Sum('invoice_total'))
        payments = payments.annotate(month=ExtractMonth('date_of_payment'), year=ExtractYear('date_of_payment'),
                                     day=ExtractDay('date_of_payment'),
                                     type=Value("credit_payment", output_field=models.CharField()))\
                           .values(group_by, "type")\
                           .annotate(cash=Sum('payment'))

        return cash_invoices.union(payments).order_by(group_by)


class StockSoldTotalViewSet(viewsets.ModelViewSet):
    serializer_class = StockSoldTotalSerializer
    http_method_names = ('get')

    def get_queryset(self):
        return database.models.InvoiceProduct.objects.annotate(month=ExtractMonth('invoice__date_of_sale'))\
                                                     .values('product', 'month')\
                                                     .annotate(quantity=Sum(F('quantity') - F('returned_quantity')))


class BackupDbViewSet(viewsets.ModelViewSet):
    http_method_names = ('get',)

    def list(self, request):
        # Using delete=True would delete the file immediately on close, 
        # so we manage cleanup manually to allow FileResponse to stream it.
        tmp_file = tempfile.NamedTemporaryFile(delete=False)
        
        try:
            # Context manager ensures tar footer and gzip stream are finalized
            with tarfile.open(fileobj=tmp_file, mode='w:gz') as archive:
                fixtures = [
                    ('database.Category', 'categories.json'), 
                    ('database.Source', 'sources.json'),
                    ('database.Supplier', 'suppliers.json'), 
                    ('database.Product', 'products.json'),
                    ('database.Customer', 'customers.json'), 
                    ('database.Invoice', 'invoices.json'),
                    ('database.InvoiceProduct', 'invoice_products.json'),
                    ('database.InvoiceCreditPayment', 'payments.json')
                ]

                for fixture, filename in fixtures:
                    buf = io.StringIO()
                    management.call_command('dumpdata', fixture, indent=2, format='json', stdout=buf)
                    data = buf.getvalue().encode('utf-8')
                    
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(data)
                    archive.addfile(tarinfo, fileobj=io.BytesIO(data))
                    buf.close()
            
            # Close the underlying file handle so the OS flushes the buffer to disk
            tmp_file.close()

            today = datetime.datetime.now().strftime("%Y-%m-%d")
            download_name = "backup_{}.tar.gz".format(today)
            
            # Re-open in read-binary mode for the response
            return FileResponse(open(tmp_file.name, 'rb'), filename=download_name, as_attachment=True)
            
        except Exception as e:
            # If something fails during creation, clean up the leaked temp file
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)
            raise e

class RestoreDbViewSet(viewsets.ModelViewSet):
    http_method_names = ('post',)

    FIXTURES = [
        "customers.json", "categories.json", "sources.json", "suppliers.json", 
        "products.json", "invoices.json", "invoice_products.json", "payments.json"
    ]

    def create(self, request):
        file_obj = request.FILES.get('file', None)
        if not file_obj:
            return HttpResponseBadRequest("No file received")

        try:
            # Open the tarball
            archive = tarfile.open(fileobj=file_obj, mode='r:gz')
            
            # Pre-parse and validate all JSON files first to avoid 
            # failing halfway through a database transaction
            fixtures_data = []
            for fixture_name in self.FIXTURES:
                extracted = archive.extractfile(fixture_name)
                if extracted:
                    fixtures_data.append({
                        'name': fixture_name,
                        'data': json.loads(extracted.read().decode('utf-8'))
                    })
            archive.close()
        except Exception as e:
            return HttpResponseBadRequest(f"Archive processing error: {str(e)}")

        # Start the optimization: Everything inside one Database Transaction
        try:
            with transaction.atomic():
                # 1. Clear the database
                management.call_command('flush', verbosity=0, interactive=False)

                results = []
                # 2. Process each file separately (Backwards Compatible)
                for item in fixtures_data:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(item['data'], f)
                        temp_path = f.name
                    
                    try:
                        output = io.StringIO()
                        management.call_command('loaddata', temp_path, stdout=output)
                        
                        # Extract the count for the response log
                        val = output.getvalue()
                        count = val.split(' ')[1] if 'Installed' in val else "0"
                        results.append(f"Restored {count} from {item['name']}")
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                # 3. Optional but Recommended: Reset Postgres ID sequences
                # This prevents "Duplicate Key" errors on next manual entry
                # (Requires django-extensions or a custom management command)
                management.call_command('sqlsequencereset', 'database') 

            return HttpResponse("\n".join(results))

        except Exception as e:
            return HttpResponse(f"Transaction failed: {str(e)}", status=500)

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
