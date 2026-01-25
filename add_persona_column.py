import sqlite3

db_path = r"c:\Users\gilad\OneDrive\Documents\IISprepairproject\backend\data\app.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if the column already exists
    cursor.execute("PRAGMA table_info(interview_sessions)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'persona' not in columns:
        cursor.execute("ALTER TABLE interview_sessions ADD COLUMN persona TEXT DEFAULT 'friendly'")
        conn.commit()
        print("✓ Successfully added 'persona' column to interview_sessions table")
    else:
        print("✓ Column 'persona' already exists")
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    conn.close()
