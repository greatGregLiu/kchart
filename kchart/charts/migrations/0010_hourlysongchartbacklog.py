# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-23 16:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0009_auto_20160623_2311'),
    ]

    operations = [
        migrations.CreateModel(
            name='HourlySongChartBacklog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('next_backlog_timestamp', models.DateTimeField(auto_now_add=True, verbose_name='Time from which to start the next backlog operation')),
                ('last_modified', models.DateTimeField(auto_now=True)),
                ('chart', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hourly_backlog', to='charts.Chart')),
            ],
        ),
    ]