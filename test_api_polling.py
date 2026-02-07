import sqlite3
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os
import time
from datetime import datetime

# Load secrets and credentials. If you are having issues, delete .cache and reauthenticate
load_dotenv()
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')
DB = os.getenv('DB')

# If the database/tables don't exists, create it based on the schema.sql
def init_database(cursor, schema_file='schema.sql'):
    with open(schema_file, 'r') as f:
        schema = f.read()
    cursor.executescript(schema)
    print("Database initialized")

# This is the main polling and grabbing function
def poll_spotify(sp, cursor):
    # Get last timestamp
    cursor.execute("SELECT MAX(played_at) FROM tracks")
    result = cursor.fetchone()[0]
    last_timestamp = result if result else "1970-01-01T00:00:00Z"
    
    # Get recently played
    recent = sp.current_user_recently_played(limit=50)
    
    new_tracks = []
    
    for item in recent['items']:
        if item['played_at'] <= last_timestamp:
            break
        
        track = item['track']
        
        # Insert album
        cursor.execute(
            """
                INSERT OR IGNORE INTO 
                albums (album_id, album_name, album_release_date, album_total_tracks, album_image_url, album_spotify_url, album_uri, album_type) 
                VALUES (?,?,?,?,?,?,?,?)
            """, 
            (
                track['album']['id'],
                track['album']['name'],
                track['album']['release_date'],
                track['album']['total_tracks'],
                track['album']['images'][0]['url'] if track['album']['images'] else None,
                track['album']['external_urls']['spotify'],
                track['album']['uri'],
                track['album']['album_type']
            )
        )
        
        # Insert track
        cursor.execute(
            """
                INSERT OR IGNORE INTO 
                tracks (played_at, track_id, track_name, track_popularity, track_duration_ms, track_explicit, track_disc_number, track_number, track_type, track_href, track_isrc, track_uri, track_spotify_url, album_id) 
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, 
            (
                item['played_at'],
                track['id'],
                track['name'],
                track['popularity'],
                track['duration_ms'],
                track['explicit'],
                track['disc_number'],
                track['track_number'],
                track['type'],
                track['href'],
                track.get('external_ids', {}).get('isrc'),
                track['uri'],
                track['external_urls']['spotify'],
                track['album']['id']
            )
        )
        
        # Insert artists
        artist_names = []
        for position, artist in enumerate(track['artists']):
            cursor.execute(
                """
                    INSERT OR IGNORE INTO 
                    artists (artist_id, artist_name, artist_url, artist_type)
                    VALUES (?, ?, ?, ?)
                """, 
                (
                    artist['id'],
                    artist['name'],
                    artist['external_urls']['spotify'],
                    artist['type']
                )
            )
            
            cursor.execute(
                """
                    INSERT OR IGNORE INTO 
                    track_artists (played_at, artist_id, artist_position)
                    VALUES (?, ?, ?)
                """, 
                (
                    item['played_at'],
                    artist['id'],
                    position
                )
            )
            artist_names.append(artist['name'])
        
        # Store track info for logging
        new_tracks.append({
            'track_name': track['name'],
            'artist_name': ', '.join(artist_names),
            'played_at': item['played_at']
        })
   
    return new_tracks

# main() controls the looping
def main():
    print("Spotify Polling Service Starting...")
    
    # Connect to database
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    init_database(cursor)
    conn.commit()
    
    # Authenticate with Spotify
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        open_browser=False,
        scope="user-read-recently-played"
    ), requests_timeout=10)
    
    print("Connected to Spotify")
    print("Polling every 30 seconds...")
    
    # Main polling loop
    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_tracks = poll_spotify(sp, cursor)
            conn.commit()
            
            if new_tracks:
                print(f"[{timestamp}] Added {len(new_tracks)} new track(s):")
                for track_info in new_tracks:
                    print(f"  → {track_info['track_name']} by {track_info['artist_name']} (played at {track_info['played_at']})")
            else:
                print(f"[{timestamp}] No new tracks")
            
        except Exception as e:
            print(f"[{timestamp}] Error: {e}")
        
        # Wait 30 seconds before next poll
        time.sleep(30)

# Run main when the script is called on
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopping Spotify polling script...")