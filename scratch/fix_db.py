
import sqlite3
import os

db_path = 'chatgpt.db'
if not os.path.exists(db_path):
    print(f"Database {db_path} not found.")
else:
    conn = sqlite3.connect(db_path)
    curr = conn.cursor()
    try:
        curr.execute('ALTER TABLE global_cache ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP')
        conn.commit()
        print("Column 'created_at' added successfully to 'global_cache'.")
    except sqlite3.OperationalError as e:
        print(f"OperationalError: {e}")
    finally:
        conn.close()
