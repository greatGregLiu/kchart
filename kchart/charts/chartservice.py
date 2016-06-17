# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from datetime import datetime, date
import logging
import re

from lxml.html import fromstring
import requests

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned

from .models import (
    Artist,
    Album,
    Song,
    MusicService,
    MusicServiceArtist,
    MusicServiceAlbum,
    MusicServiceSong,
    Chart,
    HourlySongChart,
    HourlySongChartEntry,
)
from .utils import KR_TZ, strip_to_hour, utcnow, melon_hour


logger = logging.getLogger(__name__)


class BaseChartService(object):
    '''Abstract chart service class'''

    NAME = None
    URL = ''
    ARTIST_URL = '{artist_id}'
    ALBUM_URL = '{album_id}'
    SONG_URL = '{song_id}'
    SLUG = ''

    def __init__(self):
        if not self.NAME:
            raise NotImplementedError('BaseChartService.NAME field must be overridden')
        self.service = self._get_or_create()

    def _get_or_create(self, force_update=False):
        '''Get or create this MusicService object

        :param bool force_update: True if the row for this service should be updated
        :rtype MusicService
        '''
        defaults = {
            'url': self.NAME,
            '_artist_url': self.ARTIST_URL,
            '_album_url': self.ALBUM_URL,
            '_song_url': self.SONG_URL,
            'slug': self.SLUG,
        }

        (service, created) = MusicService.objects.get_or_create(name=self.NAME, defaults=defaults)
        if force_update:
            service.update(defaults)
            service.save()
        return service

    def fetch_hourly(self, hour=None, dry_run=False, force_update=False):
        '''Fetch the specified hourly chart for this service and update the relevant table

        :param datetime hour: The specific (tz aware) hour to update. If no hour is specified, the current live chart
            will be fetched.
        :param bool dry_run: True if the chart data should not be written to the database.
        :param bool force_update: True if existing chart data should be overwritten
        '''
        raise NotImplementedError


class MelonChartService(BaseChartService):

    NAME = 'Melon'
    URL = 'http://www.melon.com'
    ARTIST_URL = 'http://www.melon.com/artist/detail.htm?artistId={artist_id}'
    ALBUM_URL = 'http://www.melon.com/album/detail.htm?albumId={album_id}'
    SONG_URL = 'http://www.melon.com/song/detail.htm?songId={song_id}'
    SLUG = 'melon'

    def __init__(self):
        super(MelonChartService, self).__init__()
        (self.hourly_chart, created) = Chart.objects.get_or_create(
            service=self.service,
            defaults={
                'name': 'Melon realtime top 100',
                'url': 'http://www.melon.com/chart/index.htm',
                'weight': 0.5,  # the instiz weight for melon is 6x (50% of potential points)
            }
        )

    @classmethod
    def api_get_json(cls, url, params=None):
        headers = {'Accept': 'application/json', 'appKey': settings.MELON_APP_KEY}
        r = requests.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    def get_artist_from_melon(self, melon_id, defaults=None):
        try:
            melon_artist = MusicServiceArtist.objects.get(service=self.service, service_artist_id=melon_id)
            return melon_artist.artist
        except ObjectDoesNotExist:
            if defaults:
                artist_info = defaults
            else:
                artist_info = self._scrape_artist_info(melon_id)
            artist = Artist.objects.create(name=artist_info['name'], debut_date=artist_info['debut_date'])
            artist.save()
            melon_artist = MusicServiceArtist.objects.create(
                artist=artist,
                service=self.service,
                service_artist_id=melon_id
            )
            melon_artist.save()
            return artist

    def get_album_from_melon(self, melon_id, defaults=None):
        try:
            melon_album = MusicServiceAlbum.objects.get(service=self.service, service_album_id=melon_id)
            return melon_album.album
        except ObjectDoesNotExist:
            if not defaults:
                raise NotImplementedError('Melon album detail scraper not implemented')
            album = Album.objects.create(
                name=defaults['name'],
                release_date=defaults['release_date']
            )
            for artist in defaults['artists']:
                album.artists.add(artist)
            album.save()
            melon_album = MusicServiceAlbum.objects.create(
                album=album,
                service=self.service,
                service_album_id=melon_id
            )
            melon_album.save()
            return album

    def get_song_from_melon(self, melon_id, defaults=None):
        try:
            melon_song = MusicServiceSong.objects.get(service=self.service, service_song_id=melon_id)
            return melon_song.song
        except ObjectDoesNotExist:
            if not defaults:
                raise NotImplementedError('Melon song detail scraper not implemented')
            song = Song.objects.create(
                name=defaults['name'],
                album=defaults['album'],
                release_date=defaults['release_date']
            )
            for artist in defaults['artists']:
                song.artists.add(artist)
            song.save()
            melon_song = MusicServiceSong.objects.create(
                song=song,
                service=self.service,
                service_song_id=melon_id
            )
            melon_song.save()
            return song

    def _scrape_artist_info(self, melon_id):
        artist_info = {'melon_id': melon_id, 'debut_date': None}
        url = self.ARTIST_URL.format(artist_id=melon_id)
        r = requests.get(url)
        r.raise_for_status()
        html = fromstring(r.text)
        title = html.find_class('title_atist')
        if len(title) != 1:
            raise RuntimeError('Got unexpected melon artist detail HTML')
        artist_info['name'] = title[0][0].tail.strip()
        artist_infos = html.find_class('section_atistinfo03')
        if len(artist_infos) != 1:
            raise RuntimeError('Got unexpected melon artist detail HTML')
        info_list = artist_infos[0].find_class('list_define')[0]
        if info_list[0].text.strip() == '데뷔' and info_list[1].tag == 'dd':
            if 'debut_song' in info_list[1].classes:
                debut_str = info_list[1].text_content().split('|')[0].strip()
            else:
                debut_str = info_list[1].text.strip()
            if debut_str:
                parts = debut_str.split('.')
                year = int(parts[0])
                if len(parts) > 1:
                    month = int(parts[1])
                else:
                    month = 1
                if len(parts) > 2:
                    day = int(parts[2])
                else:
                    day = 1
                artist_info['debut_date'] = date(year, month, day)
        return artist_info

    @classmethod
    def get_or_create_song_from_melon_data(cls, song_data):
        melon = cls()
        release_date = datetime.strptime(song_data['issueDate'], '%Y%m%d').date()
        artists = []
        for artist_data in song_data['artists']['artist']:
            artists.append(melon.get_artist_from_melon(artist_data['artistId']))
        defaults = {
            'name': song_data['albumName'],
            'artists': artists,
            'release_date': release_date,
        }
        album = melon.get_album_from_melon(song_data['albumId'], defaults=defaults)
        defaults['name'] = song_data['songName']
        defaults['album'] = album
        return melon.get_song_from_melon(song_data['songId'], defaults=defaults)

    def fetch_hourly(self, hour=None, dry_run=False, force_update=False):
        if hour:
            raise ValueError(
                'Melon does not allow historical hourly chart data to be retrieved. '
                'Only live hourly Melon chart data can be fetched.'
            )
        hour = strip_to_hour(utcnow())
        if not force_update:
            try:
                chart = HourlySongChart.objects.get(chart=self.hourly_chart, hour=hour)
                if chart and chart.entries.count() and not force_update:
                    logger.debug('Already fetched this chart')
                    return
            except ObjectDoesNotExist:
                pass
            except MultipleObjectsReturned:
                pass
        url = 'http://apis.skplanetx.com/melon/charts/realtime'
        params = {
            'version': 1,
            'page': 1,
            'count': 100,
        }
        melon_data = self.api_get_json(url, params)['melon']
        if melon_data['count'] != 100:
            raise ValueError('Melon returned unexpected number of chart entries: {}'.format(melon_data['count']))
        rank_hour = melon_hour(melon_data['rankDay'], melon_data['rankHour'])
        logger.info('Fetched melon realtime chart for {}'.format(rank_hour))
        if dry_run:
            return
        (hourly_song_chart, created) = HourlySongChart.objects.get_or_create(chart=self.hourly_chart, hour=rank_hour)
        if not created and hourly_song_chart.entries.count() and not force_update:
            logger.debug('Already fetched this chart')
            return
        for song_data in melon_data['songs']['song']:
            song = self.get_or_create_song_from_melon_data(song_data)
            defaults = {'position': song_data['currentRank']}
            (chart_entry, created) = HourlySongChartEntry.objects.get_or_create(
                hourly_chart=hourly_song_chart,
                song=song,
                defaults=defaults
            )
            if not created and chart_entry.position != song_data['currentRank']:
                chart_entry.position = song_data['currentRank']
                chart_entry.save()
        logger.debug('Wrote melon realtime chart for {} to database'.format(rank_hour))

    @classmethod
    def search_artist(cls, name, page=1):
        url = 'http://apis.skplanetx.com/melon/artists'
        params = {
            'version': 1,
            'page': page,
            'count': 10,
            'searchKeyword': name.lower()
        }
        data = cls.api_get_json(url, params)['melon']
        if data['count']:
            artists = data['artists']['artist']
        else:
            artists = None
        if data['totalPages'] > data['page']:
            next_page = data['page'] + 1
        else:
            next_page = None
        return (artists, next_page)

    @classmethod
    def search_album(cls, name, page=1, artist_names=[]):
        url = 'http://apis.skplanetx.com/melon/albums'
        params = {
            'version': 1,
            'page': page,
            'count': 10,
            'searchKeyword': '{} {}'.format(name, ' '.join(artist_names)).lower()
        }
        data = cls.api_get_json(url, params)['melon']
        if data['count']:
            albums = data['albums']['album']
        else:
            albums = None
        if data['totalPages'] > data['page']:
            next_page = data['page'] + 1
        else:
            next_page = None
        return (albums, next_page)

    @classmethod
    def search_song(cls, name, page=1, artist_names=[]):
        url = 'http://apis.skplanetx.com/melon/songs'
        params = {
            'version': 1,
            'page': page,
            'count': 10,
            'searchKeyword': '{} {}'.format(name, ' '.join(artist_names)).lower()
        }
        data = cls.api_get_json(url, params)['melon']
        if data['count']:
            songs = data['songs']['song']
        else:
            songs = None
        if data['totalPages'] > data['page']:
            next_page = data['page'] + 1
        else:
            next_page = None
        return (songs, next_page)

    @classmethod
    def _compare_artist_sets(cls, left, right_list):
        intersections = []
        for right in right_list:
            i = left & right
            if i and len(i) == 1:
                intersections.append(i)
        if len(intersections) == 1 or not set.intersection(*intersections):
            return intersections
        return None

    @classmethod
    def match_song(cls, alt_service, song, album, artists):
        '''Attempt to match an alternate service song to a melon song

        If an exact match is found, the database will be updated accordingly

        :param MusicService alt_service: The alternate service
        :param dict song: A dictionary of the form {'song_name': <name>, 'song_id': <id>}
            containing alternate service's name and ID
        :param dict album: A dictionary of the form {'album_name': <name>, 'album_id': <id>}
            containing alternate service's name and ID
        :param list artists: A list of dictionaries of the form [{'album_name': <name>, 'album_id': <id>}]
            containing alternate service's name and ID
        '''
        melon = cls()
        try:
            # If we've already matched this song just return it
            alt_song = MusicServiceSong.objects.get(service=alt_service, service_song_id=song['song_id'])
            return alt_song.song
        except MusicServiceSong.DoesNotExist:
            artist_names = []
            for artist in artists:
                artist_names.append(artist['artist_name'])
            (results, next_page) = cls.search_song(song['song_name'], artist_names=artist_names)
            if not results:
                logger.info('0 search results for song {}'.format(song['song_name']))
                return None
            song['search_results'] = (results, next_page)
        for artist in artists:
            try:
                # Check for existing matched artists
                a = MusicServiceArtist.objects.get(service=alt_service, service_artist_id=artist['artist_id'])
                melon_artist = MusicServiceArtist.objects.get(service=melon.service, artist=a.artist)
                artist['melon_id'] = melon_artist.service_artist_id
            except MusicServiceArtist.DoesNotExist:
                (results, next_page) = cls.search_artist(artist['artist_name'])
                if not results:
                    logger.info('0 search results for artist {}'.format(artist['artist_name']))
                    return None
                artist['search_results'] = (results, next_page)
        try:
            # Check for existing matched albums
            a = MusicServiceAlbum.objects.get(service=alt_service, service_album_id=album['album_id'])
            melon_album = MusicServiceAlbum.objects.get(service=melon.service, album=a.album)
            album['melon_id'] = melon_album.service_album_id
        except MusicServiceAlbum.DoesNotExist:
            for artist in artists:
                artist_names.append(artist['artist_name'])
            (results, next_page) = cls.search_album(album['album_name'], artist_names=artist_names)
            if not results:
                logger.info('0 search results for album {}'.format(album['album_name']))
                return None
            album['search_results'] = (results, next_page)
        inst = bool(re.match('inst', song['song_name'], re.I))
        matched_song = None
        for potential_song in song['search_results'][0]:
            if matched_song:
                break

            # hack to make sure we don't match instrumentals to
            # non-instrumentals
            if inst != bool(re.match('inst', potential_song['songName'], re.I)):
                continue
            if 'melon_id' in album:
                if potential_song['albumId'] == album['melon_id']:
                    matched_song = potential_song
                    break
            else:
                for potential_album in album['search_results'][0]:
                    if potential_song['albumId'] != potential_album['albumId']:
                        continue
                    album_artist_set = set()
                    for a in potential_album['artists']['artist']:
                        album_artist_set.add(a['artistId'])
                    artist_set_list = []
                    for artist in artists:
                        if 'melon_id' in artist:
                            artist_set_list.append(set([artist['melon_id']]))
                        else:
                            artist_set = set()
                            for potential_artist in artist['search_results'][0]:
                                artist_set.add(potential_artist['artistId'])
                            artist_set_list.append(artist_set)
                    intersections = cls._compare_artist_sets(album_artist_set, artist_set_list)
                    if intersections:
                        matched_song = potential_song
                        song['melon_id'] = matched_song['songId']
                        album['melon_id'] = potential_album['albumId']
                        for i in intersections:
                            melon_id = i.pop()
                            for artist in artists:
                                if 'melon_id' in artist:
                                    continue
                                for potential_artist in artist['search_results'][0]:
                                    if melon_id == potential_artist['artistId']:
                                        artist['melon_id'] = melon_id
                                        break
                        break
        if matched_song:
            logger.info('Got matched song: {}'.format(matched_song))
            return cls.get_or_create_song_from_melon_data(matched_song)
        else:
            logger.error('Could not find match for song {}'.format(song))
            return None


class GenieChartService(BaseChartService):

    NAME = 'Genie'
    URL = 'http://www.genie.co.kr'
    ARTIST_URL = 'http://www.genie.co.kr/detail/artistInfo?xxnm={artist_id}'
    ALBUM_URL = 'http://www.genie.co.kr/detail/albumInfo?axnm={album_id}'
    SONG_URL = 'http://www.genie.co.kr/detail/songInfo?xgnm={song_id}'
    SLUG = 'genie'

    def __init__(self):
        super(GenieChartService, self).__init__()
        (self.hourly_chart, created) = Chart.objects.get_or_create(
            service=self.service,
            defaults={
                'name': 'Genie hourly top 100',
                'url': 'http://www.genie.co.kr/chart/top100',
                'weight': 0.25,  # the instiz weight for genie is 3x (20% of potential instiz points)
            }
        )

    def _get_artist_id_from_a(self, a):
        m = re.match(r'fnViewArtist\((?P<artist_id>\d+)\)', a.get('onclick'))
        if not m:
            return None
        return int(m.group('artist_id'))

    def _get_album_id_from_a(self, a):
        m = re.match(r'fnViewAlbumLayer\((?P<album_id>\d+)\)', a.get('onclick'))
        if not m:
            return None
        return int(m.group('album_id'))

    def _split_genie_artist(self, name, artist_id):
        url = self.ARTIST_URL.format(artist_id=artist_id)
        r = requests.get(url)
        r.raise_for_status()
        html = fromstring(r.text)
        if '&' in name:
            # Genie lists collab'd artists as a group, all other services split
            # them so we determine if we need to split here
            main_infos = html.find_class('artist-main-infos')[0]
            type_span = main_infos.find("./div[@class='info-zone']/ul[@class='info-data']/li")
            if '프로젝트' in type_span.text_content():
                artists = []
                # This is a collab artist
                artist_list = html.find_class('artist-member-list')[0]
                for li in artist_list.findall('./ul/li'):
                    artist_a = li.find('./a')
                    artist_id = self._get_artist_id_from_a(artist_a)
                    artist_name = li.text_content().strip()
                    artists.append({'artist_name': artist_name, 'artist_id': artist_id})
                return artists
        return [{'artist_name': name, 'artist_id': artist_id}]

    def _scrape_chart_entry(self, entry_element, dry_run=False):
        rank = None
        for cls in entry_element.classes:
            m = re.match('rank-(?P<rank>\d+)', cls)
            if m:
                rank = int(m.group('rank'))
        if not rank:
            raise RuntimeError('Got unexpected genie chart HTML')
        song_id = int(entry_element.get('songid'))
        music_span = entry_element.find("./span[@class='music-info']/span[@class='music_area']/span[@class='music']")
        artist_a = music_span.find("./span[@class='meta']/a[@class='artist']")
        artist_name = artist_a.text.strip()
        artist_id = self._get_artist_id_from_a(artist_a)
        artists = self._split_genie_artist(artist_name, artist_id)
        album_a = music_span.find("./span[@class='meta']/a[@class='albumtitle']")
        album_id = self._get_album_id_from_a(album_a)
        album_name = album_a.text.strip()
        title_a = music_span.find("./a[@class='title']")
        song_name = title_a.text.strip()
        song = {'song_name': song_name, 'song_id': song_id}
        album = {'album_name': album_name, 'album_id': album_id}
        song = MelonChartService.match_song(self.service, song, album, artists)
        if not song:
            return None
        MusicServiceSong.objects.get_or_create(
            song=song,
            service=self.service,
            defaults={'service_song_id': song_id}
        )
        MusicServiceAlbum.objects.get_or_create(
            album=song.album,
            service=self.service,
            defaults={'service_album_id': album_id}
        )
        for artist in artists:
            melon = MelonChartService()
            if 'melon_id' in artist:
                melon_artist = MusicServiceArtist.objects.get(
                    service=melon.service,
                    service_artist_id=artist['melon_id']
                )
                MusicServiceArtist.objects.get_or_create(
                    artist=melon_artist.artist,
                    service=self.service,
                    defaults={'service_artist_id': artist['artist_id']}
                )
        return {'song': song, 'position': rank}

    def _scrape_hourly_chart_page(self, hour, page=1, dry_run=False):
        kr_hour = hour.astimezone(KR_TZ)
        url = self.hourly_chart.url
        params = {
            'ditc': 'D',
            'rtm': 'Y',
            'ymd': kr_hour.strftime('%Y%m%d'),
            'hh': kr_hour.strftime('%H'),
            'pg': page,
        }
        r = requests.get(url, params=params)
        r.raise_for_status()
        html = fromstring(r.text)
        song_list = html.find_class('list-wrap')
        if len(song_list) != 1:
            raise RuntimeError('Got unexpected genie chart HTML')
        entries = []
        for list_entry in song_list[0]:
            entry = self._scrape_chart_entry(list_entry, dry_run=dry_run)
            if entry:
                entries.append(entry)
        return entries

    def _get_hourly_chart(self, hour, dry_run=False):
        pg1_data = self._scrape_hourly_chart_page(hour, page=1, dry_run=dry_run)
        pg2_data = self._scrape_hourly_chart_page(hour, page=2, dry_run=dry_run)
        return pg1_data + pg2_data

    def fetch_hourly(self, hour=None, dry_run=False, force_update=False):
        if hour:
            hour = strip_to_hour(hour)
        else:
            hour = strip_to_hour(utcnow())
        if not force_update:
            try:
                chart = HourlySongChart.objects.get(chart=self.hourly_chart, hour=hour)
                if chart and chart.entries.count() and not force_update:
                    logger.debug('Already fetched this chart')
                    return
            except ObjectDoesNotExist:
                pass
            except MultipleObjectsReturned:
                pass
        genie_data = self._get_hourly_chart(hour, dry_run=dry_run)
        if len(genie_data) != 100:
            logger.warning('Genie returned unexpected number of chart entries: {}'.format(len(genie_data)))
        logger.info('Fetched genie realtime chart for {}'.format(hour))
        if dry_run:
            return
        (hourly_song_chart, created) = HourlySongChart.objects.get_or_create(chart=self.hourly_chart, hour=hour)
        if not created and hourly_song_chart.entries.count():
            logger.debug('Already fetched this chart')
            return
        for song_data in genie_data:
            defaults = {'position': song_data['position']}
            (chart_entry, created) = HourlySongChartEntry.objects.get_or_create(
                hourly_chart=hourly_song_chart,
                song=song_data['song'],
                defaults=defaults
            )
            if not created and chart_entry.position != song_data['position']:
                chart_entry.position = song_data['position']
                chart_entry.save()
        logger.debug('Wrote genie realtime chart for {} to database'.format(hour))


# Add chart services to process here
CHART_SERVICES = {
    'melon': MelonChartService,
    'genie': GenieChartService,
}