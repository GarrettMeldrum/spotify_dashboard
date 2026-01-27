import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

import sqlite3
import requests
from dotenv import load_dotenv
import time, os
from datetime import datetime


# Load secrets
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')
API_BASE = os.getenv("API_BASE")
LOGGER_TOKEN = os.getenv("LOGGER_TOKEN")


# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    open_browser = False,
    scope="user-read-currently-playing"
    ), requests_timeout=10
)

current = sp.current_user_playing_track()
#print(current['item'])
item = current.get('item')
album = item.get('album')
external_urls = item.get('external_urls')
artists = item.get('artists', {})

track_url = external_urls.get('spotify')
artist_url = ''
image_url = album['images'][0]['url']
image_url_2 = album['images'][1]['url']
print(item['artists'][0]['external_urls']['spotify'])
print(image_url)
print(image_url_2)
