import os
import sqlite3
from flask import Flask, jsonify, request, g
from flask_cors import CORS
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

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
REDIRECT_URI = os.getenv('REDIRECT_URL')

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    open_browser=False,
    scope="user-read-currently-playing user-read-playback-state"
), requests_timeout=10)

app = Flask(__name__)
CORS(app)

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

@app.get("/")
def health():
    """Health check and API info"""
    return jsonify({
        "status": "ok",
        "endpoints": [
            "/analytics",
            "/listening-time",
            "/recent?limit=10"
        ]
    })

@app.get("/currently-playing")
def currently_playing():
    """Get currently playing track directly from Spotify API"""
    try:
        # Call Spotify API directly
        current = sp.current_playback()
        
        if not current or not current.get('item'):
            # Nothing playing, return recent from database
            db = get_db()
            recent = db.execute("""
                SELECT 
                    t.track_id,
                    t.track_name,
                    ar.artist_name,
                    a.album_name,
                    a.album_image_url,
                    t.track_duration_ms
                FROM tracks t
                JOIN albums a ON t.album_id = a.album_id
                JOIN track_artists ta ON t.played_at = ta.played_at
                JOIN artists ar ON ta.artist_id = ar.artist_id
                WHERE ta.artist_position = 0
                ORDER BY t.played_at DESC
                LIMIT 3
            """).fetchall()
            
            return jsonify({
                "is_playing": False,
                "tracks": [dict(row) for row in recent]
            })
        
        track = current['item']
        
        # Get play count from database
        db = get_db()
        play_count_result = db.execute(
            "SELECT COUNT(*) as count FROM tracks WHERE track_id = ?",
            (track['id'],)
        ).fetchone()
        play_count = play_count_result['count'] if play_count_result else 0
        
        return jsonify({
            "is_playing": current.get('is_playing', False),
            "progress_ms": current.get('progress_ms', 0),
            "track": {
                "track_id": track['id'],
                "track_name": track['name'],
                "artist_name": ', '.join([artist['name'] for artist in track['artists']]),
                "album_name": track['album']['name'],
                "album_image_url": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "track_duration_ms": track['duration_ms'],
                "track_spotify_url": track['external_urls']['spotify'],
                "play_count": play_count
            }
        })
        
    except Exception as e:
        print(f"Error fetching currently playing: {e}")
        return jsonify({"is_playing": False, "tracks": []}), 500

@app.get("/analytics")
def analytics():
    """Get analytics and statistics"""
    try:
        db = get_db()
        
        # Total plays
        total_plays = db.execute(
            "SELECT COUNT(*) as count FROM tracks"
        ).fetchone()['count']
        
        # Unique tracks
        unique_tracks = db.execute(
            "SELECT COUNT(DISTINCT track_id) as count FROM tracks"
        ).fetchone()['count']
        
        # Unique artists
        unique_artists = db.execute(
            """
            SELECT COUNT(DISTINCT artist_id) as count 
            FROM track_artists 
            WHERE artist_position = 0
            """
        ).fetchone()['count']
        
        # Top 5 tracks by play count
        top_tracks = db.execute(
            """
            SELECT 
                t.track_id,
                t.track_name,
                a.album_name,
                a.album_image_url,
                COUNT(*) as play_count,
                MAX(t.played_at) as last_played
            FROM 
                tracks t
            JOIN
                albums a ON t.album_id = a.album_id
            GROUP BY 
                t.track_id
            ORDER BY 
                play_count DESC
            LIMIT 
                5
            """
        ).fetchall()

        top_tracks_list = []
        for row in top_tracks:
            track_data = dict(row)

            artist = db.execute(
                """
                SELECT
                    a.artist_name
                FROM
                    track_artists ta
                JOIN
                    artists a ON ta.artist_id = a.artist_id
                JOIN
                    tracks t ON ta.played_at = t.played_at
                WHERE
                    t.track_id = ? AND ta.artist_position = 0
                LIMIT
                    1
                """,
                (track_data['track_id'],)
            ).fetchone()

            track_data['artist_name'] = artist['artist_name'] if artist else 'Unknown'
            top_tracks_list.append(track_data)
        
        # Top 8 artists by count
        top_artists = db.execute(
            """
            SELECT
                ar.artist_id,
                ar.artist_name,
                COUNT(*) as play_count  
            FROM
                track_artists ta
            JOIN
                artists ar ON ta.artist_id = ar.artist_id
            WHERE
                ta.artist_position = 0
            GROUP BY
                ar.artist_id
            ORDER BY
                play_count DESC
            LIMIT
                8
            """
        ).fetchall()
        
        # Recent 10 plays
        recent_plays = db.execute(
            """
            SELECT 
                t.played_at,
                t.track_id,
                t.track_name,
                t.track_duration_ms,
                a.album_name,
                a.album_image_url,
                ar.artist_name
            FROM 
                tracks t
            JOIN 
                albums a ON t.album_id = a.album_id
            JOIN 
                track_artists ta ON t.played_at = ta.played_at
            JOIN 
                artists ar ON ta.artist_id = ar.artist_id
            WHERE 
                ta.artist_position = 0
            ORDER BY 
                t.played_at DESC
            LIMIT 
                10
            """
        ).fetchall()
        
        return jsonify({
            "stats": {
                "total_plays": total_plays,
                "unique_tracks": unique_tracks,
                "unique_artists": unique_artists
            },
            "top_tracks": top_tracks_list,
            "top_artists": [dict(row) for row in top_artists],
            "recent_plays": [dict(row) for row in recent_plays]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.get("/listening-time")
def listening_time():
    """Total listening time and stats"""
    try:
        db = get_db()
        
        stats = db.execute("""
            SELECT 
                SUM(track_duration_ms) / 1000.0 / 60.0 as total_minutes,
                AVG(track_duration_ms) / 1000.0 / 60.0 as avg_track_minutes,
                COUNT(*) as total_plays
            FROM tracks
        """).fetchone()
        
        total_hours = stats['total_minutes'] / 60 if stats['total_minutes'] else 0
        total_days = total_hours / 24
        
        return jsonify({
            "total_minutes": round(stats['total_minutes'], 2) if stats['total_minutes'] else 0,
            "total_hours": round(total_hours, 2),
            "total_days": round(total_days, 2),
            "avg_track_minutes": round(stats['avg_track_minutes'], 2) if stats['avg_track_minutes'] else 0,
            "total_plays": stats['total_plays']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)