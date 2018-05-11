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
    total_value = serializers.FloatField(read_only=True)

    class Meta:
        model = models.Source
        fields = '__all__'


# Category
class CategorySerializer(QueryFieldsMixin, serializers.ModelSerializer):
    total_value = serializers.FloatField(read_only=True)

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
        fields = ('invoice_id', 'payment', 'date_of_payment',)


# Invoice
class InvoiceProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.InvoiceProduct
        exclude = ('invoice', 'id',)


class InvoiceSerializer(QueryFieldsMixin, serializers.ModelSerializer):
    products = InvoiceProductSerializer(many=True)
    invoice_total = serializers.FloatField(read_only=True)
    payments_total = serializers.FloatField(read_only=True)

    class Meta:
        model = models.Invoice
        fields = '__all__'

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('products')
        return queryset

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

# Sales total
class SalesTotalSerializer(serializers.Serializer):
    year = serializers.IntegerField(read_only=True)
    month = serializers.IntegerField(read_only=True)
    sum = serializers.FloatField(read_only=True)
