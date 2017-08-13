from rest_framework import serializers

import database.models as models


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Customer
        fields = '__all__'


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Supplier
        fields = '__all__'


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Source
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Category
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = '__all__'


class InvoiceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.InvoiceProduct
        exclude = ('invoice',)


class InvoiceSerializer(serializers.ModelSerializer):
    products = InvoiceProductSerializer(many=True)

    class Meta:
        model = models.Invoice
        fields = '__all__'

    def create(self, validated_data):
        products_data = validated_data.pop('products')
        invoice = models.Invoice.objects.create(**validated_data)

        for product in products_data:
            cost_price = models.Product.objects.get(id=product["product"].id).cost_price
            models.InvoiceProduct.objects.create(invoice=invoice, cost_price=cost_price, **product)

        return invoice
