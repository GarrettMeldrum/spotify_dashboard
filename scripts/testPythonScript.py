import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

# Load secrets
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    open_browser=False,
    scope="user-read-recently-played"
), requests_timeout=10)

recent = sp.current_user_recently_played(limit=50)

items = recent['items']
track = items[0].keys()
item1 = recent['items'][0]['track'].keys()

# Track duration
#track_duration_ms = recent['items'][0]['track']['duration_ms']
#track_disc_number = recent['items'][0]['track']['disc_number']
#track_explicit = recent['items'][0]['track']['explicit']
#track_spotify_url = recent['items'][0]['track']['external_urls']['spotify']
#track_isrc = recent['items'][0]['track']['external_ids']['isrc']
#track_href = recent['items'][0]['track']['href']
#track_id = recent['items'][0]['track']['id']
track_is_local = recent['items'][0]['track']['is_local']
#track_name = recent['items'][0]['track']['name']
#track_popularity = recent['items'][0]['track']['popularity']
#track_number = recent['items'][0]['track']['track_number']
#track_type = recent['items'][0]['track']['type']
#track_uri = recent['items'][0]['track']['uri']

#album_album_type = recent['items'][0]['track']['album']['album_type']
#album_type = recent['items'][0]['track']['album']['type']
#album_spotify_url = recent['items'][0]['track']['album']['external_urls']['spotify']
#album_href = recent['items'][0]['track']['album']['href']
#album_id = recent['items'][0]['track']['album']['id']
#album_name = recent['items'][0]['track']['album']['name']
#album_image_url = recent['items'][0]['track']['album']['images'][0]
#album_release_date = recent['items'][0]['track']['album']['release_date']
#album_release_date_precision = recent['items'][0]['track']['album']['release_date_precision']
#album_total_tracks = recent['items'][0]['track']['album']['total_tracks']
#ablum_uri = recent['items'][0]['track']['album']['uri']

artists = recent['items'][0]['track']['artists']

print(artists)