import os
import sqlite3
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass

directory = os.path.dirname(os.path.abspath(__file__))
db = os.getenv("DB")
db_path = os.path.join(directory, db)

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