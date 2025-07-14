import sqlite3
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


conn = sqlite3.connect('c:/github/spotify_dashboard/spotify_history.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM spotify_history")
rows = cursor.fetchall()

for row in rows:
    print(row)