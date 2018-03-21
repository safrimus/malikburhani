import os
import csv
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "malikburhani.settings")
django.setup()

import database.models as models


stock_details = {}
with open('csv/tblStockDetails.txt') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        stock_details[row['Product ID']] = {k:v for k,v in row.items() if k != 'Product ID'}

with open('csv/tblProductDetails.txt') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        # Customer
        # name = row['Customer Name']
        # primary_phone = row['Phone Number']
        # secondary_phone = row['Other Details']

        # new_customer = models.Customer(name=name, primary_phone=primary_phone, secondary_phone=secondary_phone)
        # new_customer.save()

        # Product
        skip_list = [1, 272, 275, 285, 286, 321, 391, 402, 409, 417, 434, 465, 479, 565, 566, 623, 626, 627,
                     667, 673, 679, 680, 681, 682, 684, 685, 709, 753, 814, 824]
        if row['Product ID'] in skip_list:
            continue

        hide_product = 1 - int(row['Display'])
        stock = int(stock_details[row['Product ID']]['Stock in Shop'])

        if (stock <= 0 and hide_product):
            continue

        name = row['Product Name/Code']
        description = row['Product Description']
        size = row['Size']
        cost_price = row['Cost Price']
        sell_price = row['Sell Price']
        source = models.Source.objects.get(id=row['Source ID'])

        cat_id = row['Category ID']
        if (cat_id == "12"):
            cat_id = 11
        elif (cat_id == "13"):
            cat_id = 12
        category = models.Category.objects.get(id=cat_id)
        supplier = models.Supplier.objects.get(id=stock_details[row['Product ID']]['Supplier ID'])

        new_product = models.Product(name=name, description=description, size=size, cost_price=cost_price,
                                     sell_price=sell_price, hide_product=hide_product, source=source,
                                     category=category, supplier=supplier, stock=stock)
        new_product.save()

        # Supplier
        # id = row['Supplier ID']
        # company = row['Supplier Company']
        # agent = row['Supplier Agent']
        # email = row['E-Mail Address']
        # phone = row['Telephone Number']
        # address = row['Postal Address']

        # new_supplier = models.Supplier(id=id, company=company, agent=agent, email=email, phone=phone,
        #                                address=address)
        # new_supplier.save()
