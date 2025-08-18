import os
import sqlite3
import time
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import spotipy
from spotipy.oauth2 import SpotifyOAuth

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
    scope="user-read-recently-played user-read-playback-state"
))

# Connect to SQLite
conn = sqlite3.connect('spotify_history.db', check_same_thread=False)
cursor = conn.cursor()

# Create table with track_id
cursor.execute('''
CREATE TABLE IF NOT EXISTS spotify_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id TEXT,
    song_name TEXT,
    artist_name TEXT,
    album_name TEXT,
    duration_ms INTEGER,
    timestamp DATETIME
)
''')
conn.commit()

def get_last_stored_timestamp():
    cursor.execute('SELECT MAX(timestamp) FROM spotify_history')
    result = cursor.fetchone()[0]
    return datetime.fromisoformat(result).replace(tzinfo=timezone.utc) if result else None

def store_recent_tracks():
    last_timestamp = get_last_stored_timestamp()
    new_tracks = []

    # 1. Recently played
    try:
        results = sp.current_user_recently_played(limit=50)
        for item in results['items']:
            played_at = datetime.fromisoformat(item['played_at'].replace('Z', '+00:00'))
            if last_timestamp is None or played_at > last_timestamp:
                track = item['track']
                new_tracks.append((
                    track['id'],
                    track['name'],
                    track['artists'][0]['name'],
                    track['album']['name'],
                    track['duration_ms'],
                    played_at.isoformat()
                ))
    except Exception as e:
        print(f"Error fetching recently played: {e}")

    # 2. Currently playing
    try:
        current = sp.current_playback()
        if current and current['is_playing']:
            track = current['item']
            track_id = track['id']

            # Check if this track is already stored in the last 5 minutes
            five_minutes_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(minutes=5)
            cursor.execute('''
                SELECT COUNT(*) FROM spotify_history
                WHERE track_id = ? AND timestamp > ?
            ''', (track_id, five_minutes_ago.isoformat()))
            already_exists = cursor.fetchone()[0]

            if not already_exists:
                new_tracks.append((
                    track['id'],
                    track['name'],
                    track['artists'][0]['name'],
                    track['album']['name'],
                    track['duration_ms'],
                    datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
                ))
    except Exception as e:
        print(f"Error checking current playback: {e}")

    # 3. Insert new tracks
    if new_tracks:
        cursor.executemany('''
            INSERT INTO spotify_history (track_id, song_name, artist_name, album_name, duration_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', new_tracks)
        conn.commit()
        print(f"[{datetime.now().isoformat()}] Stored {len(new_tracks)} new tracks.")
    else:
        print(f"[{datetime.now().isoformat()}] No new tracks to store.")

# Polling loop
print("Polling every 30 seconds. Press Ctrl+C to stop.")
try:
    while True:
        store_recent_tracks()
        time.sleep(30)
except KeyboardInterrupt:
    print("Stopping polling...")
finally:
    conn.close()
