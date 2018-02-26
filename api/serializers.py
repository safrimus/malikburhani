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

    class Meta:
        model = models.Source
        fields = '__all__'


# Category
class CategorySerializer(QueryFieldsMixin, serializers.ModelSerializer):

    class Meta:
        model = models.Category
        fields = '__all__'


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
                    raise serializers.ValidationError("sell_price and quantity must be greater than 0")
            except KeyError:
                pass

        return data

    def update(self, instance, validated_data):
        products = validated_data.pop('products')

        for product in products:
            invoice_product = models.InvoiceProduct.objects.get(invoice=instance.id, product=product["product"])
            invoice_product.returned_quantity = product["returned_quantity"]
            invoice_product.save(update_fields=["returned_quantity"])

        return instance

    def create(self, validated_data):
        products = validated_data.pop('products')
        invoice = models.Invoice.objects.create(**validated_data)

        for product in products:
            cost_price = models.Product.objects.get(id=product["product"].id).cost_price
            models.InvoiceProduct.objects.create(invoice=invoice, cost_price=cost_price, **product)

        return invoice
