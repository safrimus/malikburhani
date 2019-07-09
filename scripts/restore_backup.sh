#!/bin/bash

backupdir="cd ~/Desktop/Backup_*;"
flush="python3 ~/malikburhani/manage.py flush --no-input;"
load_cus="python3 ~/malikburhani/manage.py loaddata customers.json;"
load_cat="python3 ~/malikburhani/manage.py loaddata categories.json;"
load_sor="python3 ~/malikburhani/manage.py loaddata sources.json;"
load_sup="python3 ~/malikburhani/manage.py loaddata suppliers.json;"
load_pro="python3 ~/malikburhani/manage.py loaddata products.json;"
load_inv="python3 ~/malikburhani/manage.py loaddata invoices.json;"
load_inv_pro="python3 ~/malikburhani/manage.py loaddata invoice_products.json;"
load_pay="python3 ~/malikburhani/manage.py loaddata payments.json;"

commands=$backupdir$flush$load_cus$load_cat$load_sor$load_sup$load_pro$load_inv$load_inv_pro$load_pay

gnome-terminal -e "bash -c \"$commands exec bash\""
