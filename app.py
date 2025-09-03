import os
import sqlite3
from flask import Flask, jsonify, request, g
from dotenv import load_dotenv

try:
    load_dotenv()
except Exception:
    pass

directory = os.path.dirname(os.path.abspath(__file__))
db = os.getenv("DB")
db_path = os.path.join(directory, db)

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
    
    rows = get_db().execute(
        """
        SELECT
            id,
            played_at,
            track_id,
            track_name,
            artist_name_01 AS artist_name,
            album_name,
            duration_ms
        FROM
            spotify_history
        ORDER BY cast(played_at AS INTEGER) DESC
        LIMIT ?;
        """,
        (limit,),
    ).fetchall()
    
    return jsonify([dict(r) for r in rows])
   
    
if __name__ == "__main__":
    app.run()
