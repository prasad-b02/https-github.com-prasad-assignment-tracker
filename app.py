import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = "super_secret_assignment_tracker_key"

# --------------------------------------------------------------------
# DATABASE SETUP
# --------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect('assignments.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create assignments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            title TEXT NOT NULL,
            deadline TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')

    # Create student profile table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT,
            college TEXT,
            branch TEXT
        )
    ''')

    # Default profile setup if empty
    cursor.execute('SELECT COUNT(*) FROM profile')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO profile (id, name, college, branch) VALUES (1, 'prakash', 'kiet korngi', 'CSE(AIML)')")

    conn.commit()
    conn.close()

init_db()

def get_student_profile():
    conn = get_db_connection()
    user = conn.execute('SELECT name, college, branch FROM profile WHERE id = 1').fetchone()
    conn.close()
    if user:
        return user['name'], user['branch'], user['college'], user
    return "prakash", "CSE(AIML)", "kiet korngi", ("prakash", "kiet korngi", "CSE(AIML)")

# --------------------------------------------------------------------
# ROUTES
# --------------------------------------------------------------------
@app.route('/')
@app.route('/dashboard')
def index():
    name, branch, college, _ = get_student_profile()
    conn = get_db_connection()
    assignments = conn.execute('SELECT * FROM assignments ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', assignments=assignments, student_name=name, branch_name=branch, college_name=college)

@app.route('/add', methods=['GET', 'POST'])
def add_assignment():
    if request.method == 'POST':
        # Accept field names from both simple & multi-step forms
        subject = request.form.get('subject') or request.form.get('subject_name') or 'General'
        title = request.form.get('title') or request.form.get('assignment_title') or 'Untitled'
        deadline = request.form.get('deadline') or request.form.get('deadline_date') or '2026-08-01'
        priority = request.form.get('priority') or 'Medium'
        status = request.form.get('status') or 'Pending'

        # Insert directly into SQLite database
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO assignments (subject, title, deadline, priority, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (subject, title, deadline, priority, status))
        conn.commit()
        conn.close()

        # Redirect straight back to dashboard to view the new entry
        return redirect(url_for('index'))

    return render_template('add_assignment.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_assignment(id):
    conn = get_db_connection()
    assignment = conn.execute('SELECT * FROM assignments WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        subject = request.form.get('subject')
        title = request.form.get('title')
        deadline = request.form.get('deadline')
        priority = request.form.get('priority')
        status = request.form.get('status')

        conn.execute('''
            UPDATE assignments
            SET subject = ?, title = ?, deadline = ?, priority = ?, status = ?
            WHERE id = ?
        ''', (subject, title, deadline, priority, status, id))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))

    conn.close()
    return render_template('edit_assignment.html', assignment=assignment)

@app.route('/delete/<int:id>')
def delete_assignment(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM assignments WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
@app.route('/profile_setup', methods=['GET', 'POST'])
def profile():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('student_name') or request.form.get('name')
        college = request.form.get('college_name') or request.form.get('college')
        branch = request.form.get('branch_name') or request.form.get('branch')

        conn.execute('''
            UPDATE profile
            SET name = ?, college = ?, branch = ?
            WHERE id = 1
        ''', (name, college, branch))
        conn.commit()

    user_row = conn.execute('SELECT name, college, branch FROM profile WHERE id = 1').fetchone()
    user = (user_row['name'], user_row['college'], user_row['branch']) if user_row else ('prakash', 'kiet korngi', 'CSE(AIML)')

    total = conn.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'Completed'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE status != 'Completed'").fetchone()[0]
    postponed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'Postponed'").fetchone()[0]
    conn.close()

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

    return render_template('profile.html', user=user, total=total, completed=completed, pending=pending, postponed=postponed, completion_rate=completion_rate)

@app.route('/project_guide')
def project_guide():
    return render_template('project_guide.html')

@app.route('/learn')
def learn_hub():
    return render_template('learn/index.html')

@app.route('/learn/c')
def learn_c():
    return render_template('learn/c.html')

@app.route('/learn/dsa')
def learn_dsa():
    return render_template('learn/dsa.html')

@app.route('/learn/python')
def learn_python():
    return render_template('learn/python.html')

@app.route('/learn/math')
def learn_math():
    return render_template('learn/math.html')

@app.route('/learn/it')
def learn_it():
    return render_template('learn/it.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)