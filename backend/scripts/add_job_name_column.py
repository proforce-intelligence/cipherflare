import asyncio
import os
import sys
import sqlite3

# Add the current directory to sys.path
sys.path.append(os.getcwd())

async def add_job_name_column():
    db_path = "./dark_web.db"
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if job_name column already exists
        cursor.execute("PRAGMA table_info(jobs)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'job_name' not in columns:
            print("Adding 'job_name' column to 'jobs' table...")
            cursor.execute("ALTER TABLE jobs ADD COLUMN job_name VARCHAR(255)")
            conn.commit()
            print("Successfully added 'job_name' column.")
            
            # Update existing rows with a default title based on keyword
            cursor.execute("UPDATE jobs SET job_name = 'Search: ' || keyword WHERE job_name IS NULL AND keyword IS NOT NULL")
            cursor.execute("UPDATE jobs SET job_name = 'Monitor: ' || target_url WHERE job_name IS NULL AND target_url IS NOT NULL")
            conn.commit()
            print("Updated existing rows with default job names.")
        else:
            print("'job_name' column already exists in 'jobs' table.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(add_job_name_column())
