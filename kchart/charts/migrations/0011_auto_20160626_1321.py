# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-26 04:21
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('charts', '0010_hourlysongchartbacklog'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnknownServiceSong',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_song_id', models.IntegerField()),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.MusicService')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='unknownservicesong',
            unique_together=set([('service', 'service_song_id')]),
        ),
    ]
