# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-14 13:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='album',
            name='artist',
        ),
        migrations.RemoveField(
            model_name='song',
            name='artist',
        ),
        migrations.AddField(
            model_name='album',
            name='artists',
            field=models.ManyToManyField(related_name='albums', to='charts.Artist'),
        ),
        migrations.AddField(
            model_name='song',
            name='artists',
            field=models.ManyToManyField(related_name='songs', to='charts.Artist'),
        ),
    ]