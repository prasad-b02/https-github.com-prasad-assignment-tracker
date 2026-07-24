import os
import sqlite3
from datetime import date
from flask import Flask, abort, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_assignment_tracker_key")

# --------------------------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect('assignments.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Assignments Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            title TEXT,
            deadline TEXT,
            priority TEXT,
            status TEXT
        )
    ''')

    assignment_columns = {row[1] for row in cursor.execute('PRAGMA table_info(assignments)').fetchall()}
    if 'priority' not in assignment_columns:
        cursor.execute('ALTER TABLE assignments RENAME TO assignments_legacy')
        cursor.execute('''
            CREATE TABLE assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                title TEXT,
                deadline TEXT,
                priority TEXT,
                status TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO assignments (id, subject, title, deadline, priority, status)
            SELECT id, subject, title, deadline,
                   CASE
                       WHEN UPPER(COALESCE(priority_tag, '')) LIKE '%HIGH%' THEN 'High'
                       WHEN UPPER(COALESCE(priority_tag, '')) LIKE '%MEDIUM%' THEN 'Medium'
                       ELSE 'Low'
                   END,
                   CASE WHEN status = 'In Progress' THEN 'Pending' ELSE status END
            FROM assignments_legacy
        ''')
        cursor.execute('DROP TABLE assignments_legacy')

    # 2. Student Profile Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT,
            college TEXT,
            branch TEXT
        )
    ''')

    cursor.execute('SELECT COUNT(*) FROM profile')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO profile (id, name, college, branch) VALUES (1, 'prakash', 'kiet korngi', 'CSE(AIML)')")

    conn.commit()
    conn.close()

init_db()

# Helper function to fetch student profile details
def get_student_profile():
    try:
        conn = get_db_connection()
        user = conn.execute('SELECT name, college, branch FROM profile WHERE id = 1').fetchone()
        conn.close()
        if user:
            return user['name'], user['branch'], user['college'], (user['name'], user['college'], user['branch'])
    except Exception:
        pass
    return "prakash", "CSE(AIML)", "kiet korngi", ("prakash", "kiet korngi", "CSE(AIML)")

def validate_deadline(value):
    try:
        deadline = date.fromisoformat(value)
    except (TypeError, ValueError):
        return "Enter a valid deadline date."
    if deadline < date.today():
        return "Deadline cannot be in the past. Choose today or a future date."
    return None

def predict_priority(title, deadline, previous_assignments):
    deadline_date = date.fromisoformat(deadline)
    days_remaining = (deadline_date - date.today()).days
    urgency_score = 100 if days_remaining <= 2 else 75 if days_remaining <= 7 else 50 if days_remaining <= 14 else 25

    previous_dates = sorted(date.fromisoformat(assignment['deadline']) for assignment in previous_assignments)
    earlier_deadlines = sum(previous_date <= deadline_date for previous_date in previous_dates)
    deadline_rank_score = round((len(previous_dates) - earlier_deadlines + 1) / (len(previous_dates) + 1) * 100)

    priority_scores = {'High': 100, 'Medium': 60, 'Low': 20}
    historical_scores = [priority_scores.get(assignment['priority'], 60) for assignment in previous_assignments]
    history_score = sum(historical_scores) / len(historical_scores)

    urgent_words = ('exam', 'final', 'urgent', 'lab', 'project', 'submission')
    keyword_score = 20 if any(word in title.lower() for word in urgent_words) else 0
    total_score = urgency_score * 0.55 + deadline_rank_score * 0.25 + history_score * 0.2 + keyword_score

    if total_score >= 70:
        return 'High', 'AI prediction: urgent deadline or priority pattern detected.'
    if total_score >= 45:
        return 'Medium', 'AI prediction: deadline and previous assignments indicate medium priority.'
    return 'Low', 'AI prediction: deadline is later than the higher-priority assignments.'

# --------------------------------------------------------------------
# PAGE 1: SUBJECTS CONCEPTS HUB (DEFAULT HOME PAGE)
# --------------------------------------------------------------------
@app.route('/')
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

# --------------------------------------------------------------------
# PAGE 2: ALL ABOUT PROJECT
# --------------------------------------------------------------------
@app.route('/project_guide')
@app.route('/about_project')
def project_guide():
    return render_template('project_guide.html')

# --------------------------------------------------------------------
# PAGE 3: USER PROFILE & METRICS
# --------------------------------------------------------------------
@app.route('/profile', methods=['GET', 'POST'])
@app.route('/profile_setup', endpoint='profile_setup', methods=['GET', 'POST'])
def profile():
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('student_name') or request.form.get('name') or 'prakash'
        college = request.form.get('college_name') or request.form.get('college') or 'kiet korngi'
        branch = request.form.get('branch_name') or request.form.get('branch') or 'CSE(AIML)'

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

@app.route('/analytics')
def analytics():
    name, _, _, _ = get_student_profile()
    conn = get_db_connection()
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'Completed'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE status != 'Completed'").fetchone()[0]
    postponed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'Postponed'").fetchone()[0]
    conn.close()
    return render_template('analytics.html', student_name=name, completed=completed, pending=pending, postponed=postponed)

@app.route('/performance')
def performance():
    name, _, _, _ = get_student_profile()
    conn = get_db_connection()
    assignments = conn.execute('SELECT * FROM assignments ORDER BY deadline ASC, id ASC').fetchall()
    conn.close()
    return render_template('performance.html', student_name=name, assignments=assignments)

# --------------------------------------------------------------------
# PAGE 4: ASSIGNMENT DASHBOARD TABLE
# --------------------------------------------------------------------
@app.route('/dashboard')
@app.route('/index')
def dashboard():
    name, branch, college, _ = get_student_profile()
    conn = get_db_connection()
    assignments = conn.execute('SELECT * FROM assignments ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('index.html', assignments=assignments, student_name=name, branch_name=branch, college_name=college)

# Endpoint alias for templates calling url_for('index')
@app.route('/index_alias')
def index():
    return redirect(url_for('dashboard'))

# --------------------------------------------------------------------
# ADD ASSIGNMENT FORM HANDLER (4-STEP FORM)
# --------------------------------------------------------------------
@app.route('/add', methods=['GET', 'POST'])
def add_assignment():
    if request.method == 'POST':
        # Extracts data from any field names used in your HTML form
        subject = request.form.get('subject') or request.form.get('subject_name') or 'Python'
        title = request.form.get('title') or request.form.get('assignment_title') or 'Assignment'
        deadline = request.form.get('deadline') or request.form.get('deadline_date') or ''
        status = request.form.get('status') or 'Pending'

        deadline_error = validate_deadline(deadline)
        if deadline_error:
            conn = get_db_connection()
            assignment_count = conn.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
            conn.close()
            return render_template('add_assignment.html', deadline_error=deadline_error, form_data=request.form, today=date.today().isoformat(), assignment_count=assignment_count), 400

        conn = get_db_connection()
        previous_assignments = conn.execute('SELECT deadline, priority FROM assignments ORDER BY deadline ASC, id ASC').fetchall()
        if previous_assignments:
            priority, prediction_message = predict_priority(title, deadline, previous_assignments)
        else:
            priority = request.form.get('priority') or 'Medium'
            prediction_message = None
        conn.execute('''
            INSERT INTO assignments (subject, title, deadline, priority, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (subject, title, deadline, priority, status))
        conn.commit()
        conn.close()

        # Redirects straight to the dashboard table to show your newly saved assignment
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    assignment_count = conn.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
    conn.close()
    return render_template('add_assignment.html', today=date.today().isoformat(), assignment_count=assignment_count)

# --------------------------------------------------------------------
# EDIT & DELETE HANDLERS
# --------------------------------------------------------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_assignment(id):
    conn = get_db_connection()
    assignment = conn.execute('SELECT * FROM assignments WHERE id = ?', (id,)).fetchone()

    if assignment is None:
        conn.close()
        abort(404)

    if request.method == 'POST':
        subject = request.form.get('subject')
        title = request.form.get('title')
        deadline = request.form.get('deadline')
        priority = request.form.get('priority')
        status = request.form.get('status')

        deadline_error = validate_deadline(deadline)
        if deadline_error:
            conn.close()
            return render_template('edit_assignment.html', assignment=assignment, deadline_error=deadline_error, today=date.today().isoformat()), 400

        conn.execute('''
            UPDATE assignments
            SET subject = ?, title = ?, deadline = ?, priority = ?, status = ?
            WHERE id = ?
        ''', (subject, title, deadline, priority, status, id))
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('edit_assignment.html', assignment=assignment, today=date.today().isoformat())

@app.route('/delete/<int:id>')
def delete_assignment(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM assignments WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)