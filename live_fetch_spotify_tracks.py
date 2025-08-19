import os
import sqlite3
import time
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import json

# Load environment variables
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')

# Authenticate with Spotify
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-read-recently-played"
))

# Connect to SQLite
conn = sqlite3.connect('spotify_history.db', check_same_thread=False)
cursor = conn.cursor()

# Create table with track_id
cursor.execute('''
CREATE TABLE IF NOT EXISTS spotify_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id TEXT,
    track_name TEXT,
    artist_name_01 TEXT,
    artist_name_02 TEXT,
    artist_name_03 TEXT,
    artist_name_04 TEXT,
    artist_name_05 TEXT,
    album_id TEXT,
    album_name TEXT,
    album_release_date DATETIME,
    album_type TEXT,
    duration_ms INTEGER,
    played_at DATETIME
)
''')
conn.commit()

cursor.execute("SELECT played_at FROM spotify_history ORDER BY played_at DESC LIMIT 1")
last_played_row = cursor.fetchone()
last_played_at = last_played_row[0] if last_played_row else None
print(last_played_at)


# The 50 most recent played songs
results = sp.current_user_recently_played(limit=50)

new_tracks = []
for item in results['items']:
    ### Track information
    try:
        played_at = item['played_at']
    except Exception as e:
        pass

    try:
        track_id = item['track']['name']
    except Exception as e:
        pass

    try:
        track_name = item['track']['name']
    except Exception as e:
        pass

    try:
        duration_ms = item['track']['duration_ms']
    except Exception as e:
        pass


    ### Artist information
    artists = item['track']['artists']
    artist_01 = artists[0]['name']
    artist_02 = artists[1]['name'] if len(artists) > 1 else None
    artist_03 = artists[2]['name'] if len(artists) > 2 else None
    artist_04 = artists[3]['name'] if len(artists) > 3 else None
    artist_05 = artists[4]['name'] if len(artists) > 4 else None


    ### Album information
    try:
        album_id = item['track']['album']['id']
    except Exception as e:
        pass

    try:
        album_name = item['track']['album']['name']
    except Exception as e:
        pass

    try:
        album_release_date = item['track']['album']['release_date']
    except Exception as e:
        pass

    try:
        album_type = item['track']['album']['album_type']
    except Exception as e:
        pass


    if last_played_at is None or played_at > last_played_at:
        new_tracks.append((
            track_id, track_name, 
            artist_01, artist_02, artist_03, artist_04, artist_05, 
            album_id, album_name, album_release_date, album_type, 
            duration_ms, played_at
            ))



cursor.executemany(
    '''
    INSERT OR IGNORE INTO spotify_history (
        track_id, 
        track_name, 
        artist_name_01, 
        artist_name_02, 
        artist_name_03, 
        artist_name_04, 
        artist_name_05, 
        album_id, 
        album_name, 
        album_release_date, 
        album_type, 
        duration_ms, 
        played_at
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''',
    (new_tracks)
)
conn.commit()

cursor.execute("SELECT * FROM spotify_history")
rows = cursor.fetchall()

# Print each row
print("Contents of the 'users' table:")
for row in rows:
    print(row)