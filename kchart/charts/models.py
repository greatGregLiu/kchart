# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _


class Artist(models.Model):

    name = models.CharField(_('Artist name'), blank=True, max_length=255)
    debut_date = models.DateField(_('Artist debut date'), null=True)


class Album(models.Model):

    name = models.CharField(_('Album name'), blank=True, max_length=255)
    artists = models.ManyToManyField(Artist, related_name='albums')
    release_date = models.DateField(_('Album release date'))


class Song(models.Model):

    name = models.CharField(_('Song name'), blank=True, max_length=255)
    artists = models.ManyToManyField(Artist, related_name='songs')
    album = models.ForeignKey(Album, on_delete=models.PROTECT, related_name='songs')
    release_date = models.DateField(_('Song release date'))


class MusicService(models.Model):
    '''A Korean digital music service'''

    name = models.CharField(_('Music service name'), blank=True, max_length=255)
    url = models.URLField(_('Music service URL'), blank=True)
    _artist_url = models.URLField(_('Base artist URL'), blank=True)
    _album_url = models.URLField(_('Base album URL'), blank=True)
    _song_url = models.URLField(_('Base song URL'), blank=True)

    def get_artist_url(self, artist_id):
        '''Return the URL for the specified artist page

        :param artist_id: The service-specific artist id
        :rtype: str
        '''
        return self._artist_url.format(artist_id=artist_id)

    def get_album_url(self, album_id):
        '''Return the URL for the specified album page

        :param album_id: The service-specific album id
        :rtype: str
        '''
        return self._album_url.format(album_id=album_id)

    def get_song_url(self, song_id):
        '''Return the URL for the specified album page

        :param album_id: The service-specific album id
        :rtype: str
        '''
        return self._song_url.format(song_id=song_id)


class MusicServiceArtist(models.Model):
    '''Table for mapping Artist ID to a MusicService artist ID'''
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE)
    service = models.ForeignKey(MusicService, on_delete=models.CASCADE)
    service_artist_id = models.IntegerField()

    class Meta:
        unique_together = (('service', 'artist'), ('service', 'service_artist_id'))


class MusicServiceAlbum(models.Model):
    '''Table for mapping Album ID to a MusicService artist ID'''
    album = models.ForeignKey(Album, on_delete=models.CASCADE)
    service = models.ForeignKey(MusicService, on_delete=models.CASCADE)
    service_album_id = models.IntegerField()

    class Meta:
        unique_together = (('service', 'album'), ('service', 'service_album_id'))


class MusicServiceSong(models.Model):
    '''Table for mapping Song ID to a MusicService song ID'''
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    service = models.ForeignKey(MusicService, on_delete=models.CASCADE)
    service_song_id = models.IntegerField()

    class Meta:
        unique_together = (('service', 'song'), ('service', 'service_song_id'))


class Chart(models.Model):

    service = models.ForeignKey(MusicService, on_delete=models.PROTECT)
    name = models.CharField(_('Chart name'), blank=True, max_length=255)
    url = models.URLField(_('Chart URL'), blank=True)
    weight = models.URLField(_('Chart aggregation weight'), default=1.0)

    def __str__(self):
        return self.name


class HourlySongChart(models.Model):

    chart = models.ForeignKey(Chart, on_delete=models.CASCADE)
    hour = models.DateTimeField(_('Chart start hour'))

    class Meta:
        unique_together = ('chart', 'hour')
        ordering = ['-hour', 'chart']


class HourlySongChartEntry(models.Model):

    hourly_chart = models.ForeignKey(HourlySongChart, on_delete=models.CASCADE, related_name='entries')
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    position = models.SmallIntegerField(_('Chart position'))

    class Meta:
        unique_together = (('hourly_chart', 'song'), ('hourly_chart', 'position'))
        ordering = ['hourly_chart', 'position']