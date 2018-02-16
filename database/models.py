from django.db import models
from django.utils import timezone


# Create your models here.
class Supplier(models.Model):
    class Meta:
        unique_together = ('company', 'agent',)

    company = models.TextField(help_text="Name of the supplier")
    agent = models.TextField(blank=True, null=True, help_text="Name of the company agent")
    email = models.EmailField(blank=True, null=True, help_text="Email address of the supplier")
    phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the supplier")
    address = models.TextField(blank=True, null=True, help_text="Address of the supplier")


class Source(models.Model):
    name = models.TextField(unique=True, help_text="Name of a country and/or city")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")


class Category(models.Model):
    name = models.TextField(unique=True, help_text="Name of a product category")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")


class Product(models.Model):
    class Meta:
        unique_together = ('name', 'description', 'size', 'supplier',)

    name = models.TextField(help_text="Name of the product")
    description = models.TextField(blank=True, null=True, help_text="Description of the product")
    size = models.TextField(blank=True, null=True, help_text="Size of the product")
    cost_price = models.DecimalField(default=0.0, max_digits=7, decimal_places=3, help_text="Cost price of the product")
    sell_price = models.DecimalField(default=0.0, max_digits=7, decimal_places=3, help_text="Sell price of the product")
    stock = models.IntegerField(default=0, help_text="Quantity of the product in stock")
    created = models.DateTimeField(default=timezone.now, help_text="Date product was added to database")
    image = models.ImageField(blank=True, null=True, help_text="An image of the product")
    hide_product = models.BooleanField(default=False, help_text="Hide from list of available products")
    source = models.ForeignKey(Source, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)


# Invoice
class Customer(models.Model):
    created = models.DateTimeField(default=timezone.now, help_text="Date customer added to database")
    name = models.TextField(unique=True, help_text="Name of the customer")
    primary_phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the customer")
    secondary_phone = models.CharField(blank=True, null=True, max_length=25, help_text="Phone number of the customer")


class Invoice(models.Model):
    created = models.DateTimeField(default=timezone.now, help_text="Date of creation of the invoice")
    credit = models.BooleanField(default=False, help_text="Credit sale")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    date_of_sale = models.DateTimeField(default=timezone.now, help_text="Date of sale for the invoice")


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
