import os
import sqlite3
from flask import Flask, jsonify, request, g
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

try:
    load_dotenv()
except Exception:
    pass

directory = os.path.dirname(os.path.abspath(__file__))
db = os.getenv("DB")
db_path = os.path.join(directory, db)

# Spotify client setup
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    open_browser=False,
    scope="user-read-currently-playing"
), requests_timeout=10)

app = Flask(__name__)

def get_db() -> sqlite3.Connection:
    if "_db" not in g:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        g._db = conn
    return g._db
    
@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("_db", None)
    if db is not None:
        db.close()

@app.get("/recent")
def recent():
    try:
        limit = int(request.args.get("limit", "5"))
    except Exception:
        limit = 5
    limit = max(1, min(limit, 5))
    
    # Get current playing track from Spotify
    current_track_id = None
    is_currently_playing = False
    try:
        current = sp.current_user_playing_track()
        if current and current.get('item'):
            current_track_id = current['item'].get('id')
            is_currently_playing = current.get('is_playing', False)
    except Exception as e:
        print(f"Error fetching current track: {e}")
    
    # Get recent tracks from database
    rows = get_db().execute(
        """
        SELECT
            id,
            played_at,
            track_id,
            track_name,
            artist_name_01 AS artist_name,
            album_name,
            album_cover_url,
            duration_ms
        FROM
            spotify_history
        ORDER BY cast(played_at AS INTEGER) DESC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    
    # Add is_playing flag to tracks
    result = []
    for i, row in enumerate(rows):
        track_data = dict(row)
        track_data['is_playing'] = (
            i == 0 and 
            track_data['track_id'] == current_track_id and 
            is_currently_playing
        )
        result.append(track_data)
    
    return jsonify(result)

@app.get("/analytics")
def analytics():
    db = get_db()
    
    # Get current playing status
    current_track_id = None
    is_currently_playing = False
    try:
        current = sp.current_user_playing_track()
        if current and current.get('item'):
            current_track_id = current['item'].get('id')
            is_currently_playing = current.get('is_playing', False)
    except Exception as e:
        print(f"Error fetching current track: {e}")
    
    # Total plays
    total_plays = db.execute(
        "SELECT COUNT(*) as count FROM spotify_history"
    ).fetchone()['count']
    
    # Unique tracks
    unique_tracks = db.execute(
        "SELECT COUNT(DISTINCT track_id) as count FROM spotify_history"
    ).fetchone()['count']
    
    # Unique artists
    unique_artists = db.execute(
        "SELECT COUNT(DISTINCT artist_name_01) as count FROM spotify_history"
    ).fetchone()['count']
    
    # Top 5 tracks by play count
    top_tracks = db.execute(
        """
        SELECT 
            track_id,
            track_name,
            artist_name_01 as artist_name,
            album_name,
            album_cover_url,
            COUNT(*) as play_count,
            MAX(played_at) as last_played
        FROM spotify_history
        GROUP BY track_id
        ORDER BY play_count DESC
        LIMIT 5
        """
    ).fetchall()
    
    # Top 8 artists by play count
    top_artists = db.execute(
        """
        SELECT 
            artist_name_01 as artist_name,
            COUNT(*) as play_count
        FROM spotify_history
        WHERE artist_name_01 IS NOT NULL
        GROUP BY artist_name_01
        ORDER BY play_count DESC
        LIMIT 8
        """
    ).fetchall()
    
    # Recent 10 plays
    recent_plays = db.execute(
        """
        SELECT 
            id,
            track_id,
            track_name,
            artist_name_01 as artist_name,
            album_name,
            album_cover_url,
            played_at,
            duration_ms
        FROM spotify_history
        ORDER BY cast(played_at AS INTEGER) DESC
        LIMIT 10
        """
    ).fetchall()
    
    # Add is_playing flag to recent plays (first track only)
    recent_plays_list = []
    for i, row in enumerate(recent_plays):
        track_data = dict(row)
        track_data['is_playing'] = (
            i == 0 and 
            track_data['track_id'] == current_track_id and 
            is_currently_playing
        )
        recent_plays_list.append(track_data)
    
    return jsonify({
        "stats": {
            "total_plays": total_plays,
            "unique_tracks": unique_tracks,
            "unique_artists": unique_artists
        },
        "top_tracks": [dict(row) for row in top_tracks],
        "top_artists": [dict(row) for row in top_artists],
        "recent_plays": recent_plays_list
    })
   
if __name__ == "__main__":
    app.run()
