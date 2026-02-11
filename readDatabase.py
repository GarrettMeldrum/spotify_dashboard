import sqlite3

conn = sqlite3.connect('spotify_data.db')
conn.row_factory = sqlite3.Row  # Dict-like access
cursor = conn.cursor()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()

print("=" * 80)
print("ALL DATABASE CONTENTS")
print("=" * 80)

for table in tables:
    table_name = table['name']
    
    # Get all rows
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name} ({len(rows)} rows)")
    print(f"{'=' * 80}\n")
    
    if len(rows) == 0:
        print("  (empty table)")
        continue
    
    # Print each row
    for i, row in enumerate(rows, 1):
        print(f"Row {i}:")
        for key in row.keys():
            print(f"  {key:<25} = {row[key]}")
        print()  # Blank line between rows

conn.close()
