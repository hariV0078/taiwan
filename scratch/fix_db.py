import sqlite3
import os

db_path = 'circularx.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE notification ADD COLUMN title TEXT;")
        conn.commit()
        print("Column 'title' added to 'notification' table.")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database {db_path} not found.")
