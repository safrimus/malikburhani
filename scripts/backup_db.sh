#!/bin/bash

create_dir="mkdir ~/Desktop/Backup_$(date +%Y-%m-%d_%H-%M); cd ~/Desktop/Backup_$(date +%Y-%m-%d_%H-%M);"
dump_categories="python3 ~/malikburhani/manage.py dumpdata database.Category > categories.json;"
dump_sources="python3 ~/malikburhani/manage.py dumpdata database.Source > sources.json;"
dump_suppliers="python3 ~/malikburhani/manage.py dumpdata database.Supplier > suppliers.json;"
dump_products="python3 ~/malikburhani/manage.py dumpdata database.Product > products.json;"
dump_customers="python3 ~/malikburhani/manage.py dumpdata database.Customer > customers.json;"
dump_invoices="python3 ~/malikburhani/manage.py dumpdata database.Invoice > invoices.json;"
dump_invoice_products="python3 ~/malikburhani/manage.py dumpdata database.InvoiceProduct > invoice_products.json;"
dump_payments="python3 ~/malikburhani/manage.py dumpdata database.InvoiceCreditPayment > payments.json;"

commands=$dump_categories$dump_sources$dump_suppliers$dump_products$dump_customers$dump_invoices$dump_invoice_products$dump_payments

gnome-terminal -e "bash -c \"$create_dir$commands exec bash\""
