from django.db import models
from django.utils import timezone
from django.db.models import Sum, F, FloatField, Subquery, OuterRef

import re


class NaturalSortField(models.TextField):
    def __init__(self, *args, **kwargs):
        self.for_field = kwargs.pop('for_field', None)
        kwargs.setdefault('db_index', True)
        kwargs.setdefault('editable', False)
        super(NaturalSortField, self).__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        return self.naturalize(getattr(model_instance, self.for_field))

    def naturalize(self, string):
        def naturalize_int_match(match):
            return '%08d' % (int(match.group(0)),)

        string = string.lower()
        string = string.strip()
        string = re.sub(r'^the\s+', '', string)
        string = re.sub(r'\d+', naturalize_int_match, string)

        return string


# Supplier
class Supplier(models.Model):
    class Meta:
        unique_together = ('company', 'agent',)

    company = models.TextField(help_text="Name of the supplier")
    agent = models.TextField(blank=True, null=True, help_text="Name of the company agent")
    email = models.EmailField(blank=True, null=True, help_text="Email address of the supplier")
    phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the supplier")
    address = models.TextField(blank=True, null=True, help_text="Address of the supplier")


# Source and Category
class TotalValueManager(models.Manager):
    def get_queryset(self):
        queryset = super(TotalValueManager, self).get_queryset()
        queryset = queryset.annotate(total_value=Sum(F('products__stock') * F('products__cost_price'), output_field=FloatField()))
        return queryset


class Source(models.Model):
    name = models.TextField(unique=True, help_text="Name of a country and/or city")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")

    # Override the default ORM manager
    objects = TotalValueManager()


class Category(models.Model):
    name = models.TextField(unique=True, help_text="Name of a product category")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")

    # Override the default ORM manager
    objects = TotalValueManager()


# Product
class Product(models.Model):
    class Meta:
        unique_together = ('name', 'description', 'size', 'supplier',)

    name = models.TextField(help_text="Name of the product")
    name_sort = NaturalSortField(blank=True, null=True, for_field='name')
    description = models.TextField(blank=True, null=True, help_text="Description of the product")
    description_sort = NaturalSortField(blank=True, null=True, for_field='description')
    size = models.TextField(blank=True, null=True, help_text="Size of the product")
    size_sort = NaturalSortField(blank=True, null=True, for_field='size')
    cost_price = models.DecimalField(default=0.0, max_digits=7, decimal_places=3, help_text="Cost price of the product")
    sell_price = models.DecimalField(default=0.0, max_digits=7, decimal_places=3, help_text="Sell price of the product")
    stock = models.IntegerField(default=0, help_text="Quantity of the product in stock")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")
    image = models.ImageField(blank=True, null=True, help_text="An image of the product")
    hide_product = models.BooleanField(default=False, help_text="Hide from list of available products")
    source = models.ForeignKey(Source, related_name="products", on_delete=models.PROTECT)
    category = models.ForeignKey(Category, related_name="products", on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, related_name="products", on_delete=models.PROTECT)


# Customer
class Customer(models.Model):
    created = models.DateTimeField(default=timezone.now, help_text="Date customer added to database")
    name = models.TextField(unique=True, help_text="Name of the customer")
    primary_phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the customer")
    secondary_phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the customer")


# Invoice
class InvoiceTotalManager(models.Manager):
    def get_queryset(self):
        queryset = super(InvoiceTotalManager, self).get_queryset()

        invoice_total = Subquery(InvoiceProduct.objects.filter(invoice=OuterRef('pk')).values('invoice_id')\
                            .annotate(sum=Sum((F('quantity') - F('returned_quantity')) * F('sell_price'),
                                output_field=FloatField()))\
                            .values('sum')[:1])
        payments_total = Subquery(InvoiceCreditPayment.objects.filter(invoice=OuterRef('pk')).values('invoice_id')\
                            .annotate(sum=Sum('payment', output_field=FloatField())).values('sum')[:1])

        queryset = queryset.annotate(invoice_total=invoice_total, payments_total=payments_total)
        return queryset


class Invoice(models.Model):
    created = models.DateTimeField(default=timezone.now, help_text="Date of creation of the invoice")
    credit = models.BooleanField(default=False, help_text="Credit sale")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date_of_sale = models.DateTimeField(default=timezone.now, help_text="Date of sale for the invoice")

    # Override the default ORM manager
    objects = InvoiceTotalManager()


class InvoiceProduct(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="products", on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField(help_text="Quantity sold")
    sell_price = models.DecimalField(max_digits=7, decimal_places=3, help_text="Sell price at time of sale")
    cost_price = models.DecimalField(default=0.0, max_digits=7, decimal_places=3, help_text="Cost price at time of sale")
    returned_quantity = models.IntegerField(default=0, help_text="Quantity returned by customer")


class InvoiceCreditPayment(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="credit_payments", on_delete=models.PROTECT)
    payment = models.DecimalField(max_digits=7, decimal_places=3, help_text="Credit payment for this invoice")
    date_of_payment = models.DateTimeField(default=timezone.now, help_text="Date of credit payment")
