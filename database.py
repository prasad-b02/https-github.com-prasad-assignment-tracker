import sqlite3

DATABASE = "assignments.db"

def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        college TEXT,
        branch TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY,
        student_name TEXT NOT NULL,
        college_name TEXT NOT NULL,
        branch_name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER DEFAULT 1,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        deadline TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    assignment_columns = {row[1] for row in cursor.execute('PRAGMA table_info(assignments)').fetchall()}
    if 'student_id' not in assignment_columns:
        cursor.execute('ALTER TABLE assignments ADD COLUMN student_id INTEGER DEFAULT 1')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
    print("Database tables initialized successfully!")