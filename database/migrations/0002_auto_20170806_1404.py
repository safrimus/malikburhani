# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-08-06 14:04
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('database', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceproduct',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='database.Invoice'),
        ),
    ]
