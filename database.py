import sqlite3

DATABASE = "assignments.db"

def create_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Table 1: User Profile Credentials
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY,
        student_name TEXT NOT NULL,
        college_name TEXT NOT NULL,
        branch_name TEXT NOT NULL
    )
    """)

    # Table 2: Assignments Data
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        title TEXT NOT NULL,
        deadline TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_table()
    print("Database tables initialized successfully!")