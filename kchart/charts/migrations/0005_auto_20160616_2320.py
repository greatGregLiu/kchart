# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-16 14:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0004_musicservice_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chart',
            name='weight',
            field=models.FloatField(default=1.0, verbose_name='Chart aggregation weight'),
        ),
    ]
