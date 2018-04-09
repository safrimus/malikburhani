from rest_framework import serializers
from drf_queryfields import QueryFieldsMixin
from django.db.models import Sum, F, FloatField

import database.models as models


# Customer
class CustomerSerializer(QueryFieldsMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Customer
        fields = '__all__'


# Source
class SourceSerializer(QueryFieldsMixin, serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Source
        fields = '__all__'

    def get_total_value(self, obj):
        products = models.Product.objects.filter(source=obj.id)
        return products.aggregate(total=Sum(F('stock') * F('cost_price'), output_field=FloatField()))['total']


# Category
class CategorySerializer(QueryFieldsMixin, serializers.ModelSerializer):
    total_value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Category
        fields = '__all__'

    def get_total_value(self, obj):
        products = models.Product.objects.filter(category=obj.id)
        return products.aggregate(total=Sum(F('stock') * F('cost_price'), output_field=FloatField()))['total']


# Product
class ProductSerializer(QueryFieldsMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Product
        fields = '__all__'


# Supplier
class SupplierSerializer(QueryFieldsMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Supplier
        fields = '__all__'


# Credit Payments
class InvoiceCreditPaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.InvoiceCreditPayment
        exclude = ('id',)


# Invoice
class InvoiceProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.InvoiceProduct
        exclude = ('invoice', 'id',)


class InvoiceSerializer(QueryFieldsMixin, serializers.ModelSerializer):
    products = InvoiceProductSerializer(many=True)
    invoice_total = serializers.SerializerMethodField(read_only=True)
    payments_total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = models.Invoice
        fields = '__all__'

    def get_invoice_total(self, obj):
        products = models.InvoiceProduct.objects.filter(invoice=obj.id)
        return products.aggregate(total=Sum((F('quantity') - F('returned_quantity')) * F('sell_price'),
                                            output_field=FloatField()))['total']

    def get_payments_total(self, obj):
        payments = models.InvoiceCreditPayment.objects.filter(invoice=obj.id)
        return payments.aggregate(total=Sum('payment', output_field=FloatField()))['total']

    def validate(self, data):
        products = data["products"]

        if not products:
            raise serializers.ValidationError("no products in invoice")

        for product in products:
            try:
                if product["sell_price"] <= 0.0 or product["quantity"] <= 0:
                    raise serializers.ValidationError("Sell price and quantity must be greater than 0")
            except KeyError:
                pass

            try:
                if product["returned_quantity"] > product["quantity"]:
                    raise serializers.ValidationError("Return quantity must be less than quantity sold")
            except KeyError:
                pass

        return data

    def update(self, instance, validated_data):
        products = validated_data.pop('products')

        for product in products:
            invoice_product = models.InvoiceProduct.objects.get(invoice=instance.id, product=product["product"])
            original_returned_quantity = invoice_product.returned_quantity
            invoice_product.returned_quantity = product["returned_quantity"]
            invoice_product.save(update_fields=["returned_quantity"])

            product_object = models.Product.objects.get(id=product["product"].id)
            product_object.stock += (product["returned_quantity"] - original_returned_quantity)
            product_object.save(update_fields=["stock"])

        return instance

    def create(self, validated_data):
        products = validated_data.pop('products')
        invoice = models.Invoice.objects.create(**validated_data)

        for product in products:
            product_object = models.Product.objects.get(id=product["product"].id)

            models.InvoiceProduct.objects.create(invoice=invoice, cost_price=product_object.cost_price, **product)

            product_object.stock -= product["quantity"]
            product_object.save(update_fields=["stock"])

        return invoice
