# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-13 17:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scans', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scantype',
            name='scan_name',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]