import os
import sqlite3
from dotenv import load_dotenv
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dateutil.parser import isoparse

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
    album_release_date TEXT,
    album_type TEXT,
    duration_ms INTEGER,
    played_at TEXT
)
''')
conn.commit()

# The 50 most recent played songs
results = sp.current_user_recently_played(limit=50)

def parse_played_at(ts):
    if ts is None:
        return None
    return isoparse(ts)

cursor.execute("SELECT played_at FROM spotify_history ORDER BY played_at DESC LIMIT 1")
last_played_row = cursor.fetchone()
last_played_at = last_played_row[0] if last_played_row else None
last_played_at_dt = parse_played_at(last_played_at)

new_tracks = []
for item in reversed(results['items']):
    track = item.get('track', {})
    album = track.get('album', {})
    artists = track.get('artists', [])

    ### Track information
    track_id = track.get('id')
    track_name = track.get('name')
    duration_ms = track.get('duration_ms')
    played_at = item.get('played_at')

    ### Artist information
    artist_01 = artists[0]['name'] if len(artists) > 0 else None
    artist_02 = artists[1]['name'] if len(artists) > 1 else None
    artist_03 = artists[2]['name'] if len(artists) > 2 else None
    artist_04 = artists[3]['name'] if len(artists) > 3 else None
    artist_05 = artists[4]['name'] if len(artists) > 4 else None

    ### Album information
    album_id = album.get('id')
    album_name = album.get('name')
    album_release_date = album.get('release_date')
    album_type = album.get('album_type')

    played_at_dt = parse_played_at(played_at)

    if last_played_at_dt is None or (played_at_dt and played_at_dt > last_played_at_dt):
        print(f"Adding: {track_name} at {played_at_dt}")
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
    new_tracks
)
conn.commit()
conn.close()


'''

cursor.execute("SELECT * FROM spotify_history")
rows = cursor.fetchall()

# Print each row
print("Contents of the 'users' table:")
for row in rows:
    print(row)
'''