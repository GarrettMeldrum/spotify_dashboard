import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
from dotenv import load_dotenv
from ftfy import fix_text
import time, unicodedata, os
import requests


load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')


# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-read-currently-playing"
))


# Connect to SQLite database
conn = sqlite3.connect('spotify_history.db')
cursor = conn.cursor()


# Create table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS spotify_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    duration_ms INTEGER,
    timestamp DATETIME
)
''')
conn.commit()


# Clean text to fit our format
def clean_text(text):
    fixed = fix_text(text)
    return unicodedata.normalize("NFC", fixed)


# Function to store song data
def store_song_data(song_name, artist_name, album_name, duration_ms, timestamp):
    minutes = (duration_ms // 1000) // 60
    seconds = (duration_ms // 1000) % 60
    duration_str = f"{minutes}:{seconds:02d}"

    cursor.execute('''
    INSERT INTO spotify_history (song_name, artist_name, album_name, duration_ms, timestamp) VALUES (?, ?, ?, ?, ?)
    ''', (song_name, artist_name, album_name, duration_ms, timestamp))
    conn.commit()
    print(f"Stored: {song_name} (song length: {duration_str}) by {artist_name} at {timestamp}", flush=True)


# Poll Spotify API for currently playing track
last_song_id = None
while True:
    try:
        current_track = sp.current_user_playing_track()
        if current_track and current_track.get('item'):
            track_id = current_track['item']['id']
            if track_id != last_song_id:  # New song detected
                song_name = clean_text(current_track['item']['name'])
                artist_name = clean_text(current_track['item']['artists'][0]['name'])
                album_name = clean_text(current_track['item']['album']['name'])
                duration_ms = current_track['item']['duration_ms']
                timestamp = current_track['timestamp']  # Unix timestamp in milliseconds

                # Convert timestamp to a readable format
                from datetime import datetime
                timestamp = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

                # Store the song data
                store_song_data(song_name, artist_name, album_name, duration_ms, timestamp)
                last_song_id = track_id
        else:
            pass
    except requests.exceptions.ConnectionError:
        pass
    except requests.exceptions.ReadTimeout:
        print("Spotify API timed out... Retrying connection now...")
    except Exception as e:
        print(f"Unexpected error: {e}")

    time.sleep(0.5)  # Poll every 0.25 seconds