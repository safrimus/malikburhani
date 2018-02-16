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
        exclude = ('invoice', 'id',)


class InvoiceCreditPaymentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.InvoiceCreditPayment
        exclude = ('id',)


class InvoiceSerializer(serializers.ModelSerializer):
    products = InvoiceProductSerializer(many=True)
    credit_payments = InvoiceCreditPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = models.Invoice
        fields = '__all__'

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
