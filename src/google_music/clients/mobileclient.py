__all__ = ['MobileClient']

from collections import defaultdict
from operator import itemgetter
from uuid import getnode as get_mac

import google_music_proto.mobileclient.calls as mc_calls
from google_music_proto.mobileclient.types import (
	ListenNowItemType, QueryResultType, StationSeedType
)
from google_music_proto.oauth import IOS_CLIENT_ID, IOS_CLIENT_SECRET, MOBILE_SCOPE

from .base import GoogleMusicClient
from ..utils import create_mac_string

# TODO: 'max_results', 'start_token', 'updated_min', 'quality', etc.
# TODO: Playlist edits.
# TODO: Podcast edits.
# TODO: Station create/edit.
# TODO: Shared playlists and playlist entries.
# TODO: Playlist entries batch.
# TODO: Difference between shuffles and instant mixes?
# TODO: Situations are now returned through a protobuf call?


class MobileClient(GoogleMusicClient):
	"""API wrapper class to access Google Music mobile client functionality.

	>>> from google_music import MobileClient
	>>> mc = MobileClient('username')

	Note:
		Streaming requires a ``device_id`` from a valid, linked mobile device.
		The :class:`MobileClient` instance's ``device_id`` can be changed after
		instantiation, or a different ``device_id`` provided to :meth:`stream`
		or :meth:`stream_url`.

	Parameters:
		username (str, Optional): Your Google Music username.
			This is used to store OAuth credentials for different accounts separately.
		device_id (str, Optional): A mobile device ID.
			Default: An ID is generated from your system's MAC address.
		token (dict, Optional): An OAuth token compatible with ``requests-oauthlib``.
		locale (str, Optional): `ICU <http://www.localeplanet.com/icu/>`__ locale used to
			localize some responses. This must be a locale supported by Android.
			Default: `'en_US'``.
	"""

	client = 'mobileclient'
	client_id = IOS_CLIENT_ID
	client_secret = IOS_CLIENT_SECRET
	oauth_scope = MOBILE_SCOPE

	def __init__(self, username, device_id=None, *, token=None, locale='en_US'):
		if self.login(username, token=token):
			self.locale = locale
			self.tier = 'fr'

			if device_id is None:
				mac_int = get_mac()

				if (mac_int >> 40) % 2:
					raise OSError("A valid MAC address could not be obtained.")

				self.device_id = create_mac_string(mac_int)
			else:
				self.device_id = device_id

			self.is_subscribed

	def __repr__(self):
		return f"MobileClient(username={self.username!r}, device_id={self.device_id}, token={self.token}, locale={self.locale})"

	@property
	def device_id(self):
		"""The mobile device ID of the :class:`MobileClient` instance."""

		return self.session.headers.get('X-Device-ID')

	@device_id.setter
	def device_id(self, device_id):
		self.session.headers.update({'X-Device-ID': device_id})

	@property
	def is_subscribed(self):
		"""The subscription status of the account linked to the :class:`MobileClient` instance."""

		subscribed = next(
			(
				config_item['value'] == 'true'
				for config_item in self.config()
				if config_item['key'] == 'isNautilusUser'
			),
			None
		)

		if subscribed:
			self.tier = 'aa'
		else:
			self.tier = 'fr'

		return subscribed

	@property
	def locale(self):
		"""The locale of the :class:`MobileClient` instance.

		Can be changed after instantiation.

		`ICU <http://www.localeplanet.com/icu/>`__ locale used to localize some
		responses. This must be a locale supported by Android.
		"""

		return self.session.params.get('hl')

	@locale.setter
	def locale(self, locale):
		self.session.params.update({'hl': locale})

	@property
	def tier(self):
		"""The subscription tier of the :class:`MobileClient` instance.

		Can be changed after instantiation.

		``aa`` if subscribed, ``fr`` if not.
		"""

		return self.session.params.get('tier')

	@tier.setter
	def tier(self, tier):
		self.session.params.update({'tier': tier})

	def album(self, album_id, *, include_description=True, include_songs=True):
		"""Get information about an album.

		Parameters:
			album_id (str): An album ID. Album IDs start with a 'B'.
			include_description (bool, Optional): Include description of the album in the returned dict.
			include_songs (bool, Optional): Include songs from the album in the returned dict.
				Default: ``True``.

		Returns:
			dict: Album information.
		"""

		response = self._call(
			mc_calls.FetchAlbum, album_id, include_description=include_description, include_tracks=include_songs
		)
		album_info = response.body

		return album_info

	def artist(self, artist_id, *, include_albums=True, num_related_artists=5, num_top_tracks=5):
		"""Get information about an artist.

		Parameters:
			artist_id (str): An artist ID. Artist IDs start with an 'A'.
			include_albums (bool, Optional): Include albums by the artist in returned dict.
				Default: ``True``.
			num_related_artists (int, Optional): Include up to given number of related artists in returned dict.
				Default: ``5``.
			num_top_tracks (int, Optional): Include up to given number of top tracks in returned dict.
				Default: ``5``.

		Returns:
			dict: Artist information.
		"""

		response = self._call(
			mc_calls.FetchArtist, artist_id, include_albums=include_albums,
			num_related_artists=num_related_artists, num_top_tracks=num_top_tracks
		)
		artist_info = response.body

		return artist_info

	def browse_podcasts(self, podcast_genre_id='JZCpodcasttopchartall'):
		"""Get the podcasts for a genre from the Podcasts browse tab.

		Parameters:
			podcast_genre_id (str, Optional): A podcast genre ID as found
				in :meth:`browse_podcasts_genres`.
				Default: ``'JZCpodcasttopchartall'``.

		Returns:
			list: Podcast dicts.
		"""

		response = self._call(mc_calls.PodcastBrowse, podcast_genre_id=podcast_genre_id)
		podcast_series_list = response.body.get('series', [])

		return podcast_series_list

	def browse_podcasts_genres(self):
		"""Get the genres from the Podcasts browse tab dropdown.

		Returns:
			list: Genre groups that contain sub groups.
		"""

		response = self._call(mc_calls.PodcastBrowseHierarchy)
		genres = response.body.get('groups', [])

		return genres

	def browse_stations(self, station_category_id):
		"""Get the stations for a category from Browse Stations.

		Parameters:
			station_category_id (str): A station category ID as
				found with :meth:`browse_stations_categories`.

		Returns:
			list: Station dicts.
		"""

		response = self._call(mc_calls.BrowseStations, station_category_id)
		stations = response.body.get('stations', [])

		return stations

	def browse_stations_categories(self):
		"""Get the categories from Browse Stations.

		Returns:
			list: Station categories that can contain subcategories.
		"""

		response = self._call(mc_calls.BrowseStationCategories)
		station_categories = response.body.get('root', {}).get('subcategories', [])

		return station_categories

	def config(self):
		"""Get a listing of mobile client configuration settings."""

		response = self._call(mc_calls.Config)
		config_list = response.body.get('data', {}).get('entries', [])

		return config_list

	# TODO: Check success/failure?
	def device_deauthorize(self, device):
		"""Deauthorize a registered device.

		Parameters:
			device (dict): A device dict as returned by :meth:`devices`.
		"""

		self._call(mc_calls.DeviceManagementInfoDelete, device['id'])

	# TODO: Set device dict as property of MobileClient?
	def device_set(self, device):
		"""Set device used by :class:`MobileClient` instance.

		Parameters:
			device (dict): A device dict as returned by :meth:`devices`.
		"""

		if device['id'].startswith('0x'):
			self.device_id = device['id'][2:]
		elif device['id'].startswith('ios:'):
			self.device_id = device['id'].replace(':', '')
		else:
			self.device_id = device['id']

	def devices(self):
		"""Get a listing of devices registered to the Google Music account."""

		response = self._call(mc_calls.DeviceManagementInfo)
		registered_devices = response.body.get('data', {}).get('items', [])

		return registered_devices

	def explore_genres(self, parent_genre_id=None):
		"""Get a listing of song genres.

		Parameters:
			parent_genre_id (str, Optional): A genre ID.
				If given, a listing of this genre's sub-genres is returned.

		Returns:
			list: Genre dicts.
		"""

		response = self._call(mc_calls.ExploreGenres, parent_genre_id)
		genre_list = response.body.get('genres', [])

		return genre_list

	def explore_tabs(self, *, num_items=100, genre_id=None):
		"""Get a listing of explore tabs.

		Parameters:
			num_items (int, Optional): Number of items per tab to return.
				Default: ``100``
			genre_id (genre_id, Optional): Genre ID from :meth:`explore_genres` to explore.
				Default: ``None``.

		Returns:
			dict: Explore tabs content.
		"""

		response = self._call(mc_calls.ExploreTabs, num_items=num_items, genre_id=genre_id)
		tab_list = response.body.get('tabs', [])

		explore_tabs = {}
		for tab in tab_list:
			explore_tabs[tab['tab_type'].lower()] = tab

		return explore_tabs

	def listen_now_dismissed_items(self):
		"""Get a listing of items dismissed from Listen Now tab."""

		response = self._call(mc_calls.ListenNowGetDismissedItems)
		dismissed_items = response.body.get('items', [])

		return dismissed_items

	def listen_now_items(self):
		"""Get a listing of Listen Now items.

		Note:
			This does not include situations;
			use the :meth:`situations` method instead.

		Returns:
			dict: With ``albums`` and ``stations`` keys of listen now items.
		"""

		response = self._call(mc_calls.ListenNowGetListenNowItems)
		listen_now_item_list = response.body.get('listennow_items', [])

		listen_now_items = defaultdict(list)
		for item in listen_now_item_list:
			listen_now_items[f"{ListenNowItemType(int(item['type'])).name}s"].append(item)

		return dict(listen_now_items)

	def new_releases(self, genre_id=None):
		new_releases_tab = self.explore_tabs(genre_id=genre_id)['new_releases']

		new_releases = []
		if 'groups' in new_releases_tab:
			for group in new_releases_tab['groups']:
				for entity in group['entities']:
					entity.pop('kind')
					new_releases.append(entity.popitem()[1])

		return new_releases

	def playlist_entries(self):
		"""Get a listing of playlist entries for all library playlists.

		Returns:
			list: Playlist entry dicts.
		"""

		playlist_entry_list = []
		for chunk in self.playlist_entries_iter(page_size=49995):
			playlist_entry_list.extend(chunk)

		return playlist_entry_list

	def playlist_entries_iter(self, *, start_token=None, page_size=250):
		"""Get a paged iterator of playlist entries for all library playlists.

		Parameters:
			start_token (str): The token of the page to return.
				Default: Not sent to get first page.
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Playlist entry dicts.
		"""

		start_token = None

		while True:
			response = self._call(mc_calls.PlaylistEntryFeed, max_results=page_size, start_token=start_token)
			items = response.body.get('data', {}).get('items', [])

			if items:
				yield items

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	# TODO: Rename and add shared playlist method or combine for shared playlists.
	def playlist(self, playlist_id, *, include_songs=False):
		"""Get information about a playlist.

		Parameters:
			playlist_id (str): A playlist ID.
			include_songs (bool, Optional): Include songs from the playlist in the returned dict.
				Default: ``False``

		Returns:
			dict: Playlist information.
		"""

		playlists = self.playlists(include_songs=include_songs)

		playlist_info = next(
			(
				playlist
				for playlist in playlists
				if playlist['id'] == playlist_id
			),
			{}
		)

		return playlist_info

	def playlist_create(self, name, description='', *, make_public=False):
		"""Create a playlist.

		Parameters:
			name (str): Name to give the playlist.
			description (str): Description to give the playlist.
			make_public (bool): If ``True`` and account has a subscription, make playlist public.
				Default: ``False``

		Returns:
			dict: Playlist information.
		"""

		share_state = 'PUBLIC' if make_public else 'PRIVATE'

		playlist = self._call(mc_calls.PlaylistsCreate, name, description, share_state).body

		return playlist

	# TODO: Check success/failure?
	def playlist_delete(self, playlist):
		"""Delete a playlist.

		Parameters:
			playlist (dict): A playlist dict.
		"""

		self._call(mc_calls.PlaylistsDelete, playlist['id'])

	def playlist_edit(self, playlist, *, name=None, description=None, public=None):
		"""Edit playlist(s).

		Parameters:
			playlist (dict): A playlist dict.
			name (str): Name to give the playlist.
			description (str): Description to give the playlist.
			make_public (bool): If ``True`` and account has a subscription, make playlist public.
				Default: ``False``

		Returns:
			dict: Playlist information.
		"""

		if all(value is None for value in (name, description, public)):
			raise ValueError('At least one of name, description, or public must be provided')

		playlist_id = playlist['id']

		playlist = self.playlist(playlist_id)

		name = name if name is not None else playlist['name']
		description = description if description is not None else playlist['description']
		share_state = 'PUBLIC' if public else playlist['accessControlled']

		playlist = self._call(mc_calls.PlaylistsUpdate, playlist_id, name, description, share_state).body

		return playlist

	def playlists(self, *, include_songs=False):
		"""Get a listing of library playlists.

		Parameters:
			include_songs (bool, Optional): Include songs in the returned playlist dicts.
				Default: ``False``.

		Returns:
			list: A list of playlist dicts.
		"""

		playlist_list = []
		for chunk in self.playlists_iter(page_size=49995):
			playlist_list.extend(chunk)

		if include_songs:
			playlist_entries = self.playlist_entries()

			for playlist in playlist_list:
				playlist_type = playlist.get('type')

				if playlist_type in ('USER_GENERATED', None):
					pl_entries = sorted(
						(
							pl_entry
							for pl_entry in playlist_entries
							if pl_entry['playlistId'] == playlist['id']
						),
						key=itemgetter('absolutePosition')
					)

					playlist['tracks'] = pl_entries

		return playlist_list

	def playlists_iter(self, *, start_token=None, page_size=250):
		"""Get a paged iterator of library playlists.

		Parameters:
			start_token (str): The token of the page to return.
				Default: Not sent to get first page.
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Playlist dicts.
		"""

		start_token = None

		while True:
			response = self._call(mc_calls.PlaylistFeed, max_results=page_size, start_token=start_token)
			items = response.body.get('data', {}).get('items', [])

			if items:
				yield items

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	def podcast(self, podcast_series_id, *, max_episodes=50):
		"""Get information about a podcast series.

		Parameters:
			podcast_series_id (str): A podcast series ID.
			max_episodes (int, Optional): Include up to given number of episodes in returned dict.
				Default: ``50``

		Returns:
			dict: Podcast series information.
		"""

		podcast_info = self._call(mc_calls.PodcastFetchSeries, podcast_series_id, max_episodes=max_episodes).body

		return podcast_info

	def podcasts(self, *, device_id=None):
		"""Get a listing of subsribed podcast series.

		Paramaters:
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.

		Returns:
			list: Podcast series dict.
		"""

		if device_id is None:
			device_id = self.device_id

		podcast_list = []
		for chunk in self.podcasts_iter(device_id=device_id, page_size=49995):
			podcast_list.extend(chunk)

		return podcast_list

	def podcasts_iter(self, *, device_id=None, page_size=250):
		"""Get a paged iterator of subscribed podcast series.

		Parameters:
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Podcast series dicts.
		"""

		if device_id is None:
			device_id = self.device_id

		start_token = None
		prev_items = None

		while True:
			response = self._call(
				mc_calls.PodcastSeries, device_id, max_results=page_size, start_token=start_token
			)
			items = response.body.get('data', {}).get('items', [])

			# Google does some weird shit.
			if items != prev_items:
				subscribed_podcasts = [
					item
					for item in items
					if item.get('userPreferences', {}).get('subscribed')
				]

				yield subscribed_podcasts

				prev_items = items
			else:
				break

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	def podcast_episode(self, podcast_episode_id):
		"""Get information about a podcast_episode.

		Parameters:
			podcast_episode_id (str): A podcast episode ID.

		Returns:
			dict: Podcast episode information.
		"""

		response = self._call(mc_calls.PodcastFetchEpisode, podcast_episode_id)
		podcast_episode_info = [
			podcast_episode
			for podcast_episode in response.body
			if not podcast_episode['deleted']
		]

		return podcast_episode_info

	def podcast_episodes(self, *, device_id=None):
		"""Get a listing of podcast episodes for all subscribed podcasts.

		Paramaters:
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.

		Returns:
			list: Podcast episode dicts.
		"""

		if device_id is None:
			device_id = self.device_id

		podcast_episode_list = []
		for chunk in self.podcast_episodes_iter(device_id=device_id, page_size=49995):
			podcast_episode_list.extend(chunk)

		return podcast_episode_list

	def podcast_episodes_iter(self, *, device_id=None, page_size=250):
		"""Get a paged iterator of podcast episode for all subscribed podcasts.

		Parameters:
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Podcast episode dicts.
		"""

		if device_id is None:
			device_id = self.device_id

		start_token = None
		prev_items = None

		while True:
			response = self._call(
				mc_calls.PodcastEpisode, device_id, max_results=page_size, start_token=start_token
			)
			items = response.body.get('data', {}).get('items', [])

			# Google does some weird shit.
			if items != prev_items:
				yield items

				prev_items = items
			else:
				break

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	def search(self, query, *, max_results=100, **kwargs):
		"""Search Google Music and library for content.

		Parameters:
			query (str): Search text.
			max_results (int, Optional): Maximum number of results per type per
				location to retrieve. I.e up to 100 Google and 100 library
				for a total of 200 for the default value.
				Google only accepts values up to 100.
				Default: ``100``
			kwargs (bool, Optional): Any of ``albums``, ``artists``, ``genres``,
				``playlists``, ``podcasts``, ``situations``, ``songs``, ``stations``,
				``videos`` set to ``True`` will include that result type in the
				returned dict.
				Setting none of them will include all result types in the returned dict.

		Returns:
			dict: A dict of results separated into keys: ``'albums'``, ``'artists'``,
				``'genres'``, ``'playlists'``, ```'podcasts'``, ``'situations'``,
				``'songs'``, ``'stations'``, ``'videos'``.

		Note:
			Free account search is restricted so may not contain hits for all result types.
		"""

		results = defaultdict(list)

		for type_, results_ in self.search_library(query, max_results=max_results, **kwargs).items():
			results[type_].extend(results_)

		for type_, results_ in self.search_google(query, max_results=max_results, **kwargs).items():
			results[type_].extend(results_)

		return dict(results)

	def search_google(self, query, *, max_results=100, **kwargs):
		"""Search Google Music for content.

		Parameters:
			query (str): Search text.
			max_results (int, Optional): Maximum number of results per type to retrieve.
				Google only accepts values up to 100.
				Default: ``100``
			kwargs (bool, Optional): Any of ``albums``, ``artists``, ``genres``,
				``playlists``, ``podcasts``, ``situations``, ``songs``, ``stations``,
				``videos`` set to ``True`` will include that result type in the
				returned dict.
				Setting none of them will include all result types in the returned dict.

		Returns:
			dict: A dict of results separated into keys: ``'albums'``, ``'artists'``,
				``'genres'``, ``'playlists'``, ```'podcasts'``, ``'situations'``,
				``'songs'``, ``'stations'``, ``'videos'``.

		Note:
			Free account search is restricted so may not contain hits for all result types.
		"""

		response = self._call(mc_calls.Query, query, max_results=max_results, **kwargs)

		clusters = response.body.get('clusterDetail', [])
		results = defaultdict(list)

		for cluster in clusters:
			result_type = f"{QueryResultType(int(cluster['cluster']['type'])).name}s"

			entries = cluster.get('entries', [])
			if len(entries) > 0:
				for entry in entries:
					item_key = next(
						key
						for key in entry
						if key not in ['cluster', 'score', 'type']
					)
					results[result_type].append(entry[item_key])

		return dict(results)

	def search_library(self, query, *, max_results=100, **kwargs):
		"""Search Google Music for content.

		Parameters:
			query (str): Search text.
			max_results (int, Optional): Maximum number of results per type to retrieve.
				Google only accepts values up to 100.
				Setting to ``None`` allows up to 1000 results per type but won't return playlist results.
				Default: ``100``
			kwargs (bool, Optional): Any of ``playlists``, ``podcasts``,
				``songs``, ``stations``, ``videos`` set to ``True``
				will include that result type in the returned dict.
				Setting none of them will include all result types in the returned dict.

		Returns:
			dict: A dict of results separated into keys:
				``'playlists'``, ``'podcasts'``, ``'songs'``, ``'stations'``.
		"""

		def match_fields(item, fields):
			return any(
				query.casefold() in item.get(field, '').casefold()
				for field in fields
			)

		types = [
			('playlists', ['description', 'name'], self.playlists),
			('podcasts', ['author', 'description', 'title'], self.podcasts),
			('songs', ['album', 'albumArtist', 'artist', 'composer', 'genre', 'title'], self.songs),
			('stations', ['byline', 'description', 'name'], self.stations)
		]

		results = {}

		for type_, fields, func in types:
			if (not kwargs) or (type_ in kwargs):
				results[type_] = [
					item
					for item in func()
					if match_fields(item, fields)
				][:max_results]

		return results

	def search_suggestion(self, query):
		"""Get search query suggestions for query.

		Parameters:
			query (str): Search text.

		Returns:
			list: Suggested query strings.
		"""

		response = self._call(mc_calls.QuerySuggestion, query)
		suggested_queries = response.body.get('suggested_queries', [])

		return [
			suggested_query['suggestion_string']
			for suggested_query in suggested_queries
		]

	def shuffle_album(self, album, *, num_songs=100, only_library=False, recently_played=None):
		"""Get a listing of album shuffle/mix songs.

		Parameters:
			album (dict): An album dict.
			num_songs (int, Optional): The maximum number of songs to return from the station.
				Default: ``100``
			only_library (bool, Optional): Only return content from library.
				Default: False
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'}
				where ``id`` is a song ID and ``type`` is 0 for a library song and 1 for a store song.

		Returns:
			list: List of album shuffle/mix songs.
		"""

		station_info = {
			'seed': {
				'albumId': album['albumId'], 'seedType': str(StationSeedType.album.value)
			},
			'num_entries': num_songs, 'library_content_only': only_library
		}

		if recently_played is not None:
			station_info['recently_played'] = recently_played

		response = self._call(mc_calls.RadioStationFeed, station_infos=[station_info])
		station_feed = response.body.get('data', {}).get('stations', [])

		try:
			station = station_feed[0]
		except IndexError:
			station = {}

		return station.get('tracks', [])

	def shuffle_artist(self, artist, *, num_songs=100, only_library=False, recently_played=None, only_artist=False):
		"""Get a listing of artist shuffle/mix songs.

		Parameters:
			artist (dict): An artist dict.
			num_songs (int, Optional): The maximum number of songs to return from the station.
				Default: ``100``
			only_library (bool, Optional): Only return content from library.
				Default: False
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'}
				where ``id`` is a song ID and ``type`` is 0 for a library song and 1 for a store song.
			only_artist (bool, Optional): If ``True``, only return songs from the artist,
					else return songs from artist and related artists.
					Default: ``False``

		Returns:
			list: List of artist shuffle/mix songs.
		"""

		station_info = {
			'num_entries': num_songs, 'library_content_only': only_library
		}

		if only_artist:
			station_info['seed'] = {
				'artistId': artist['artistId'], 'seedType': str(StationSeedType.artist_only.value)
			}
		else:
			station_info['seed'] = {
				'artistId': artist['artistId'], 'seedType': str(StationSeedType.artist_related.value)
			}

		if recently_played is not None:
			station_info['recently_played'] = recently_played

		response = self._call(mc_calls.RadioStationFeed, station_infos=[station_info])
		station_feed = response.body.get('data', {}).get('stations', [])

		try:
			station = station_feed[0]
		except IndexError:
			station = {}

		return station.get('tracks', [])

	def shuffle_genre(self, genre, *, num_songs=100, only_library=False, recently_played=None):
		"""Get a listing of genre shuffle/mix songs.

		Parameters:
			genre (dict): A genre dict.
			num_songs (int, Optional): The maximum number of songs to return from the station. Default: ``100``
			only_library (bool, Optional): Only return content from library.
				Default: False
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'} where ``id`` is a song ID and
				``type`` is 0 for a library song and 1 for a store song.

		Returns:
			list: List of genre shuffle/mix songs.
		"""

		station_info = {
			'seed': {'genreId': genre['id'], 'seedType': str(StationSeedType.genre.value)}, 'num_entries': num_songs,
			'library_content_only': only_library
		}

		if recently_played is not None:
			station_info['recently_played'] = recently_played

		response = self._call(mc_calls.RadioStationFeed, station_infos=[station_info])
		station_feed = response.body.get('data', {}).get('stations', [])

		try:
			station = station_feed[0]
		except IndexError:
			station = {}

		return station.get('tracks', [])

	def shuffle_song(self, song, *, num_songs=100, only_library=False, recently_played=None):
		"""Get a listing of song shuffle/mix songs.

		Parameters:
			song (dict): A song dict.
			num_songs (int, Optional): The maximum number of songs to return from the station.
				Default: ``100``
			only_library (bool, Optional): Only return content from library.
				Default: False
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'}
				where ``id`` is a song ID and ``type`` is 0 for a library song and 1 for a store song.

		Returns:
			list: List of artist shuffle/mix songs.
		"""

		station_info = {
			'num_entries': num_songs, 'library_content_only': only_library
		}

		if 'storeId' in song:
			station_info['seed'] = {'trackId': song['storeId'], 'seedType': str(StationSeedType.store_track.value)}
		else:
			station_info['seed'] = {'trackLockerId': song['id'], 'seedType': str(StationSeedType.library_track.value)}

		if recently_played is not None:
			station_info['recently_played'] = recently_played

		response = self._call(mc_calls.RadioStationFeed, station_infos=[station_info])
		station_feed = response.body.get('data', {}).get('stations', [])

		try:
			station = station_feed[0]
		except IndexError:
			station = {}

		return station.get('tracks', [])

	def situations(self, *, tz_offset=None):
		"""Get a listing of situations.

		Parameters:
			tz_offset (int, Optional): A time zone offset from UTC in seconds.
		"""

		response = self._call(mc_calls.ListenNowSituations, tz_offset)
		situation_list = response.body.get('situations', [])

		return situation_list

	def song(self, song_id):
		"""Get information about a song.

		Parameters:
			song_id (str): A song ID.

		Returns:
			dict: Song information.
		"""

		if song_id.startswith('T'):
			song_info = self._call(mc_calls.FetchTrack, song_id).body
		else:
			song_info = next(
				(
					song
					for song in self.songs()
					if song['id'] == song_id
				),
				None
			)

		return song_info

	def song_add(self, song):
		"""Add a store song to your library.

		Parameters:
			song (dict): A store song dict.

		Returns:
			str: Song's library ID.
		"""

		return self.songs_add([song])[0]

	def songs_add(self, songs):
		"""Add store songs to your library.

		Parameters:
			songs (list): A list of store song dicts.

		Returns:
			list: Songs' library IDs.
		"""

		response = self._call(mc_calls.TrackBatchCreate, songs)
		song_ids = [
			res['id']
			for res in response.body['mutate_response']
			if res['response_code'] == 'OK'
		]

		return song_ids

	def song_delete(self, song):
		"""Delete song from library.

		Parameters:
			song (str): A library song dict.

		Returns:
			str: Successfully deleted song ID.
		"""

		return self.songs_delete([song])[0]

	def songs_delete(self, songs):
		"""Delete songs from library.

		Parameters:
			song (list): A list of song dicts.

		Returns:
			list: Successfully deleted song IDs.
		"""

		response = self._call(mc_calls.TrackBatchDelete, [song['id'] for song in songs])

		success_ids = [
			res['id']
			for res in response.body['mutate_response']
			if res['response_code'] == 'OK'
		]

		# TODO: Report failures.
		# failure_ids = [
		# 	res['id']
		# 	for res in response.body['mutate_response']
		# 	if res['response_code'] != 'OK'
		# ]

		return success_ids

	def song_play(self, song):
		"""Add play to song play count.

		Parameters:
			song (dict): A song dict.

		Returns:
			bool: ``True`` if successful, ``False`` if not.
		"""

		if 'storeId' in song:
			song_id = song['storeId']
		elif 'trackId' in song:
			song_id = song['trackId']
		else:
			song_id = song['id']

		song_duration = song['durationMillis']

		response = self._call(mc_calls.ActivityRecordPlay, song_id, song_duration)

		return True if response.body['eventResults'][0]['code'] == 'OK' else False

	def song_rate(self, song, rating):
		"""Rate song.

		Parameters:
			song (dict): A song dict.
			rating (int): 0 (not rated), 1 (thumbs down), or 5 (thumbs up).

		Returns:
			bool: ``True`` if successful, ``False`` if not.
		"""

		if 'storeId' in song:
			song_id = song['storeId']
		elif 'trackId' in song:
			song_id = song['trackId']
		else:
			song_id = song['id']

		response = self._call(mc_calls.ActivityRecordRate, song_id, rating)

		return True if response.body['eventResults'][0]['code'] == 'OK' else False

	def songs(self):
		"""Get a listing of library songs.

		Returns:
			list: Song dicts.
		"""

		song_list = []
		for chunk in self.songs_iter(page_size=49995):
			song_list.extend(chunk)

		return song_list

	def songs_iter(self, *, page_size=250):
		"""Get a paged iterator of library songs.

		Parameters:
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Song dicts.
		"""

		start_token = None

		while True:
			response = self._call(mc_calls.TrackFeed, max_results=page_size, start_token=start_token)
			items = response.body.get('data', {}).get('items', [])

			if items:
				yield items

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	# TODO: Investigate library_content_only.
	# TODO: Figure out 'radio/stationfeed'.
	def station(self, station_id, *, num_songs=25, recently_played=None):
		"""Get information about a station.

		Parameters:
			station_id (str): A station ID. Use 'IFL' for I'm Feeling Lucky.
			num_songs (int, Optional): The maximum number of songs to return from the station.
				Default: ``25``
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'}
				where ``id`` is a song ID and ``type`` is 0 for a library song and 1 for a store song.

		Returns:
			dict: Station information.
		"""

		station_info = {
			'station_id': station_id,
			'num_entries': num_songs,
			'library_content_only': False
		}

		if recently_played is not None:
			station_info['recently_played'] = recently_played

		response = self._call(mc_calls.RadioStationFeed, station_infos=[station_info])
		station_feed = response.body.get('data', {}).get('stations', [])

		try:
			station = station_feed[0]
		except IndexError:
			station = {}

		return station

	# TODO: Figure out 'radio/stationfeed'.
	def station_feed(self, *, num_songs=25, num_stations=4):
		"""Generate stations.

		Note:
			A Google Music subscription is required.

		Parameters:
			num_songs (int, Optional): The total number of songs to return. Default: ``25``
			num_stations (int, Optional): The number of stations to return when no station_infos is provided.
				Default: ``5``

		Returns:
			list: Station information dicts.
		"""

		response = self._call(mc_calls.RadioStationFeed, num_entries=num_songs, num_stations=num_stations)
		station_feed = response.body.get('data', {}).get('stations', [])

		return station_feed

	def station_songs(self, station, *, num_songs=25, recently_played=None):
		"""Get a listing of songs from a station.

		Parameters:
			station (str): A station dict.
			num_songs (int, Optional): The maximum number of songs to return from the station. Default: ``25``
			recently_played (list, Optional): A list of dicts in the form of {'id': '', 'type'}
				where ``id`` is a song ID and ``type`` is 0 for a library song and 1 for a store song.
		"""

		station_id = station['id']

		station = self.station(station_id, num_songs=num_songs, recently_played=recently_played)

		return station.get('tracks', [])

	def stations(self, *, generated=True, library=True):
		"""Get a listing of library stations.

		The listing can contain stations added to the library and generated from the library.

		Parameters:
			generated (bool, Optional): Include generated stations.
				Default: True
			library (bool, Optional): Include library stations.
				Default: True

		Returns:
			list: Station information dicts.
		"""

		station_list = []
		for chunk in self.stations_iter(page_size=49995):
			for station in chunk:
				if (generated and not station.get('inLibrary')) or (library and station.get('inLibrary')):
					station_list.append(station)

		return station_list

	def stations_iter(self, *, page_size=250):
		"""Get a paged iterator of library stations.

		Parameters:
			page_size (int, Optional): The maximum number of results per returned page.
				Max allowed is ``49995``.
				Default: ``250``

		Yields:
			list: Station dicts.
		"""

		start_token = None

		while True:
			response = self._call(mc_calls.RadioStation, max_results=page_size, start_token=start_token)
			yield response.body.get('data', {}).get('items', [])

			start_token = response.body.get('nextPageToken')
			if start_token is None:
				break

	def stream(self, item, *, device_id=None, quality='hi', session_token=None):
		"""Get MP3 stream of a podcast episode, library song, station_song, or store song.

		Note:
			Streaming requires a ``device_id`` from a valid, linked mobile device.

		Parameters:
			item (str): A podcast episode, library song, station_song, or store song.
				A Google Music subscription is required to stream store songs.
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.
			quality (str, Optional): Stream quality is one of ``'hi'`` (320Kbps), ``'med'`` (160Kbps), or ``'low'`` (128Kbps).
				Default: ``'hi'``.
			session_token (str): Session token from a station dict required for unsubscribed users to stream a station song.
				station['sessionToken'] as returend by :meth:`station` only exists for free accounts.

		Returns:
			bytes: An MP3 file.
		"""

		if device_id is None:
			device_id = self.device_id

		stream_url = self.stream_url(item, device_id=device_id, quality=quality, session_token=session_token)
		response = self.session.get(stream_url)
		audio = response.content

		return audio

	def stream_url(self, item, *, device_id=None, quality='hi', session_token=None):
		"""Get a URL to stream a podcast episode, library song, station_song, or store song.

		Note:
			Streaming requires a ``device_id`` from a valid, linked mobile device.

		Parameters:
			item (str): A podcast episode, library song, station_song, or store song.
				A Google Music subscription is required to stream store songs.
			device_id (str, Optional): A mobile device ID.
				Default: Use ``device_id`` of the :class:`MobileClient` instance.
			quality (str, Optional): Stream quality is one of ``'hi'`` (320Kbps), ``'med'`` (160Kbps), or ``'low'`` (128Kbps).
				Default: ``'hi'``.
			session_token (str): Session token from a station dict required for unsubscribed users to stream a station song.
				station['sessionToken'] as returend by :meth:`station` only exists for free accounts.

		Returns:
			str: A URL to an MP3 file.
		"""

		if device_id is None:
			device_id = self.device_id

		if 'episodeId' in item:  # Podcast episode.
			response = self._call(
				mc_calls.PodcastEpisodeStreamURL, item['episodeId'], quality=quality, device_id=device_id
			)
		elif 'wentryid' in item:  # Free account station song.
			response = self._call(
				mc_calls.RadioStationTrackStreamURL, item['storeId'], item['wentryid'], session_token, quality=quality, device_id=device_id
			)
		elif 'trackId' in item:  # Playlist song.
			response = self._call(mc_calls.TrackStreamURL, item['trackId'], quality=quality, device_id=device_id)
		elif 'storeId' in item and self.is_subscribed:  # Store song.
			response = self._call(mc_calls.TrackStreamURL, item['storeId'], quality=quality, device_id=device_id)
		elif 'id' in item:  # Library song.
			response = self._call(mc_calls.TrackStreamURL, item['id'], quality=quality, device_id=device_id)
		else:
			# TODO: Create an exception for not being subscribed or use a better builtin exception for this case.
			if 'storeId' in item and not self.is_subscribed:
				msg = "Can't stream a store song without a subscription."
			else:
				msg = "Item does not contain an ID field."

			raise ValueError(msg)

		try:
			stream_url = response.headers['Location']
		except KeyError:
			stream_url = response.body['url']

		return stream_url

	def thumbs_up_songs(self, *, library=True, store=True):
		"""Get a listing of 'Thumbs Up' store songs.

		Parameters:
			library (bool, Optional): Include 'Thumbs Up' songs from library.
				Default: True
			generated (bool, Optional): Include 'Thumbs Up' songs from store.
				Default: True

		Returns:
			list: Dicts of 'Thumbs Up' songs.
		"""

		thumbs_up_songs = []

		if library is True:
			thumbs_up_songs.extend(
				song
				for song in self.songs()
				if song['rating'] == '5'
			)

		if store is True:
			response = self._call(mc_calls.EphemeralTop)
			thumbs_up_songs.extend(response.body.get('data', {}).get('items', []))

		return thumbs_up_songs

	def top_charts(self):
		"""Get a listing of the default top charts."""

		response = self._call(mc_calls.BrowseTopChart)
		top_charts = response.body

		return top_charts

	def top_charts_for_genre(self, genre_id):
		"""Get a listing of top charts for a top chart genre.

		Parameters:
			genre_id (str): A top chart genre ID as found with :meth:`top_charts_genres`.
		"""

		response = self._call(mc_calls.BrowseTopChartForGenre, genre_id)
		top_chart_for_genre = response.body

		return top_chart_for_genre

	def top_charts_genres(self):
		"""Get a listing of genres from the browse top charts tab."""

		response = self._call(mc_calls.BrowseTopChartGenres)
		top_chart_genres = response.body.get('genres', [])

		return top_chart_genres
