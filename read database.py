import sqlite3
import io
from pathlib import Path
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')



db_path = Path(__file__).resolve().parent / "spotify_history.db"
conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
cursor = conn.cursor()

cursor.execute("SELECT * FROM spotify_history ORDER BY played_at ASC")
rows = cursor.fetchall()

for row in rows:
    print(row)
