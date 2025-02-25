import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sqlite3
import time

CLIENT_ID = '0a99e00c7ac24f10b1e6263402ad1bd6'
CLIENT_SECRET = '03fdb9d2e6894a77a73286313c9f9c8b'
REDIRECT_URI = 'http://localhost:8080/'

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
    timestamp DATETIME
)
''')
conn.commit()

# Function to store song data
def store_song_data(song_name, artist_name, album_name, timestamp):
    cursor.execute('''
    INSERT INTO spotify_history (song_name, artist_name, album_name, timestamp)
    VALUES (?, ?, ?, ?)
    ''', (song_name, artist_name, album_name, timestamp))
    conn.commit()
    print(f"Stored: {song_name} by {artist_name} at {timestamp}")

# Poll Spotify API for currently playing track
last_song_id = None
while True:
    current_track = sp.current_user_playing_track()
    if current_track is not None:
        track_id = current_track['item']['id']
        if track_id != last_song_id:  # New song detected
            song_name = current_track['item']['name']
            artist_name = current_track['item']['artists'][0]['name']
            album_name = current_track['item']['album']['name']
            timestamp = current_track['timestamp']  # Unix timestamp in milliseconds

            # Convert timestamp to a readable format
            from datetime import datetime
            timestamp = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')

            # Store the song data
            store_song_data(song_name, artist_name, album_name, timestamp)
            last_song_id = track_id

    time.sleep(5)  # Poll every 5 seconds