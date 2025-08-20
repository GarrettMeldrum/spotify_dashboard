import spotipy
from spotipy.oauth2 import SpotifyOAuth
from spotipy.exceptions import SpotifyException

import sqlite3
from dotenv import load_dotenv
import time, os
from datetime import datetime


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
    scope="user-read-currently-playing"
    ), requests_timeout=10
)


# Connect to SQLite database
conn = sqlite3.connect('spotify_history.db')
cursor = conn.cursor()

# Create table if it doesn't exist
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


idle_count = 0
# Polling loop
while True:

    try:
        current = sp.current_user_playing_track()
        if current is None:
            print("Idle count:", idle_count)
            if idle_count >= (300): # 5 minutes
                idle_count += 30
                time.sleep(30)
            else:
                idle_count += 10
                time.sleep(10)
            continue
        idle_count = 0
        
        
        # Get all the API data available
        item = current.get('item', {})
        if item is None: continue
        album = item.get('album', {})
        if album is None: continue
        artists = item.get('artists', [])
        if artists is None: continue

        played_at = current.get('timestamp')
        duration_ms = item.get('duration_ms')
        track_id = item.get('id')
        track_name = item.get('name')

        artist_01 = artists[0]['name'] if len(artists) > 0 else None
        artist_02 = artists[1]['name'] if len(artists) > 1 else None
        artist_03 = artists[2]['name'] if len(artists) > 2 else None
        artist_04 = artists[3]['name'] if len(artists) > 3 else None
        artist_05 = artists[4]['name'] if len(artists) > 4 else None
        
        album_id = album.get('id')
        album_name = album.get('name')
        album_release_date = album.get('release_date')
        album_type = album.get('album_type')


        # Find the last inserted row into the table
        cursor.execute(
            "SELECT track_id FROM spotify_history ORDER BY played_at desc limit 1"
        )
        last_played_track_id_row = cursor.fetchone()
        last_played_track_id = last_played_track_id_row[0] if last_played_track_id_row else None

        # If current track not last stored track
        if track_id != last_played_track_id:
            timestamp_for_print = datetime.fromtimestamp(played_at / 1000).strftime('%Y-%m-%d %H:%M:%S')
            print(f'Adding new track... {track_name} by {artist_01} at timestamp {timestamp_for_print}')
            
            cursor.execute(
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                [track_id, track_name, 
                 artist_01, artist_02, artist_03, artist_04, artist_05, 
                 album_id, album_name, album_release_date, album_type, 
                 duration_ms, played_at]
            )
            conn.commit()
        time.sleep(1)
    

    # Exception handling
    except SpotifyException as e:
        if e.http_status == 429:
            retry_after = int(e.headers.get("Retry-After", 30))
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
        if e.http_status == 443:
            time.sleep(30)
        else:
            print(f"Unexpected Spotify exception has been raised... \n{e}")
            time.sleep(30)
    except Exception as e:
        print(e)
        time.sleep(30)


    '''
    cursor.execute("SELECT * FROM spotify_history")
    rows = cursor.fetchall()

    # Print each row
    print("Contents of the 'users' table:")
    for row in rows:
        print(row)
    '''


    '''
    timeouts and exceptions raised:
        HTTPSConnectionPool(host='api.spotify.com', port=443): Read timed out. (read timeout=5)
    '''
