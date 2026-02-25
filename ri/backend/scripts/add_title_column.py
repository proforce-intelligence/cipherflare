import asyncio
import os
import sys
import sqlite3

# Add the current directory to sys.path
sys.path.append(os.getcwd())

async def add_title_column():
    db_path = "./dark_web.db"
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if title column already exists
        cursor.execute("PRAGMA table_info(monitoring_jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'title' not in columns:
            print("Adding 'title' column to 'monitoring_jobs' table...")
            # We can't add NOT NULL to an existing table without a default value
            cursor.execute("ALTER TABLE monitoring_jobs ADD COLUMN title VARCHAR(120)")
            conn.commit()
            print("Successfully added 'title' column.")
            
            # Update existing rows with a default title based on URL
            cursor.execute("UPDATE monitoring_jobs SET title = 'Job for ' || target_url WHERE title IS NULL")
            conn.commit()
            print("Updated existing rows with default titles.")
        else:
            print("'title' column already exists in 'monitoring_jobs' table.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(add_title_column())
