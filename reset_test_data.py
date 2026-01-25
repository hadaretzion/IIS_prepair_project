
import sqlite3
import os

db_path = "backend/data/app.db"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

user_id = "aadbea99-8b56-4df2-8192-41a72e42785e"

print("Cleaning up question_history for test user...")
cursor.execute("DELETE FROM question_history WHERE user_id = ?", (user_id,))
conn.commit()
print(f"Deleted {cursor.rowcount} rows.")

conn.close()
