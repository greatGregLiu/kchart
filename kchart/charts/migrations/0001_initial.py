# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2016-06-14 10:28
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Album name')),
                ('release_date', models.DateField(verbose_name='Album release date')),
            ],
        ),
        migrations.CreateModel(
            name='Artist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Artist name')),
                ('debut_date', models.DateField(verbose_name='Artist debut date')),
            ],
        ),
        migrations.CreateModel(
            name='Chart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Chart name')),
                ('url', models.URLField(blank=True, verbose_name='Chart URL')),
                ('weight', models.URLField(default=1.0, verbose_name='Chart aggregation weight')),
            ],
        ),
        migrations.CreateModel(
            name='HourlySongChart',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hour', models.DateTimeField(verbose_name='Chart start hour')),
                ('chart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.Chart')),
            ],
            options={
                'ordering': ['-hour', 'chart'],
            },
        ),
        migrations.CreateModel(
            name='HourlySongChartEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('position', models.SmallIntegerField(verbose_name='Chart position')),
                ('hourly_chart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='entries', to='charts.HourlySongChart')),
            ],
            options={
                'ordering': ['hourly_chart', 'position'],
            },
        ),
        migrations.CreateModel(
            name='MusicService',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Music service name')),
                ('url', models.URLField(blank=True, verbose_name='Music service URL')),
                ('_artist_url', models.URLField(blank=True, verbose_name='Base artist URL')),
                ('_album_url', models.URLField(blank=True, verbose_name='Base album URL')),
                ('_song_url', models.URLField(blank=True, verbose_name='Base song URL')),
            ],
        ),
        migrations.CreateModel(
            name='MusicServiceAlbum',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_album_id', models.IntegerField()),
                ('album', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.Album')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.MusicService')),
            ],
        ),
        migrations.CreateModel(
            name='MusicServiceArtist',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_artist_id', models.IntegerField()),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.Artist')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.MusicService')),
            ],
        ),
        migrations.CreateModel(
            name='MusicServiceSong',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('service_song_id', models.IntegerField()),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.MusicService')),
            ],
        ),
        migrations.CreateModel(
            name='Song',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=255, verbose_name='Song name')),
                ('release_date', models.DateField(verbose_name='Song release date')),
                ('album', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='songs', to='charts.Album')),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='songs', to='charts.Artist')),
            ],
        ),
        migrations.AddField(
            model_name='musicservicesong',
            name='song',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.Song'),
        ),
        migrations.AddField(
            model_name='hourlysongchartentry',
            name='song',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='charts.Song'),
        ),
        migrations.AddField(
            model_name='chart',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='charts.MusicService'),
        ),
        migrations.AddField(
            model_name='album',
            name='artist',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='albums', to='charts.Artist'),
        ),
        migrations.AlterUniqueTogether(
            name='musicservicesong',
            unique_together=set([('service', 'service_song_id'), ('service', 'song')]),
        ),
        migrations.AlterUniqueTogether(
            name='musicserviceartist',
            unique_together=set([('service', 'service_artist_id'), ('service', 'artist')]),
        ),
        migrations.AlterUniqueTogether(
            name='musicservicealbum',
            unique_together=set([('service', 'album'), ('service', 'service_album_id')]),
        ),
        migrations.AlterUniqueTogether(
            name='hourlysongchartentry',
            unique_together=set([('hourly_chart', 'position'), ('hourly_chart', 'song')]),
        ),
        migrations.AlterUniqueTogether(
            name='hourlysongchart',
            unique_together=set([('chart', 'hour')]),
        ),
    ]