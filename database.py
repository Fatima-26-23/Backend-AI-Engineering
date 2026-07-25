import sqlite3

# Connect to (or create) the database
conn = sqlite3.connect("tasks.db", check_same_thread=False)
cursor = conn.cursor()

# Create the tasks table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    done BOOLEAN NOT NULL DEFAULT 0
)
""")

# Check if the table is empty
cursor.execute("SELECT COUNT(*) FROM tasks")
count = cursor.fetchone()[0]

# Insert sample tasks only if the table is empty
if count == 0:
    sample_tasks = [
        ("Learn Python", False),
        ("Build CRUD API", True),
        ("Connect SQLite Database", False)
    ]

    cursor.executemany(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        sample_tasks
    )
    conn.commit()