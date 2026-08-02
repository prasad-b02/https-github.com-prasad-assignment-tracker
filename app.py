import os
import sqlite3
import threading
import webbrowser
from datetime import date
from flask import Flask, abort, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super_secret_assignment_tracker_key")
DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(app.root_path, "assignments.db"))

# --------------------------------------------------------------------
# DATABASE INITIALIZATION
# --------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY DEFAULT 1,
            name TEXT,
            college TEXT,
            branch TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            college TEXT,
            branch TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER DEFAULT 1,
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
                student_id INTEGER DEFAULT 1,
                subject TEXT,
                title TEXT,
                deadline TEXT,
                priority TEXT,
                status TEXT
            )
        ''')
        cursor.execute('''
            INSERT INTO assignments (id, student_id, subject, title, deadline, priority, status)
            SELECT id, 1, subject, title, deadline,
                   CASE
                       WHEN UPPER(COALESCE(priority_tag, '')) LIKE '%HIGH%' THEN 'High'
                       WHEN UPPER(COALESCE(priority_tag, '')) LIKE '%MEDIUM%' THEN 'Medium'
                       ELSE 'Low'
                   END,
                   CASE WHEN status = 'In Progress' THEN 'Pending' ELSE status END
            FROM assignments_legacy
        ''')
        cursor.execute('DROP TABLE assignments_legacy')

    if 'student_id' not in assignment_columns:
        cursor.execute('ALTER TABLE assignments ADD COLUMN student_id INTEGER DEFAULT 1')
        cursor.execute('UPDATE assignments SET student_id = 1 WHERE student_id IS NULL')

    cursor.execute('SELECT COUNT(*) FROM students')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO students (name, college, branch) VALUES ('prakash', 'kiet korngi', 'CSE(AIML)')")

    cursor.execute('SELECT COUNT(*) FROM profile')
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO profile (id, name, college, branch) VALUES (1, 'prakash', 'kiet korngi', 'CSE(AIML)')")

    cursor.execute('UPDATE assignments SET student_id = (SELECT id FROM students WHERE LOWER(name) = LOWER("prakash")) WHERE student_id IS NULL OR student_id = 0')
    cursor.execute('UPDATE assignments SET student_id = 1 WHERE student_id IS NULL OR student_id = 0')
    conn.commit()
    conn.close()

init_db()

# --------------------------------------------------------------------
# STUDENT SESSION HELPERS
# --------------------------------------------------------------------
def get_current_student():
    student_id = session.get('student_id')
    if not student_id:
        return None
    conn = get_db_connection()
    student = conn.execute('SELECT id, name, college, branch FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    return dict(student) if student else None

def get_or_create_student(name):
    conn = get_db_connection()
    normalized_name = (name or 'prakash').strip() or 'prakash'
    existing = conn.execute('SELECT id, name, college, branch FROM students WHERE LOWER(name) = LOWER(?)', (normalized_name,)).fetchone()
    if existing:
        conn.close()
        return dict(existing)

    conn.execute(
        'INSERT INTO students (name, college, branch) VALUES (?, ?, ?)',
        (normalized_name, 'kiet korngi', 'CSE(AIML)')
    )
    conn.commit()
    new_student = conn.execute('SELECT id, name, college, branch FROM students WHERE LOWER(name) = LOWER(?)', (normalized_name,)).fetchone()
    conn.close()
    return dict(new_student)

def require_student_session():
    student = get_current_student()
    if not student:
        return None
    return student

# Helper function to fetch student profile details
def get_student_profile():
    student = get_current_student()
    if student:
        return student['name'], student['branch'], student['college'], (student['name'], student['college'], student['branch'])
    return "prakash", "CSE(AIML)", "kiet korngi", ("prakash", "kiet korngi", "CSE(AIML)")

def validate_deadline(value):
    try:
        deadline = date.fromisoformat(value)
    except (TypeError, ValueError):
        return "Enter a valid deadline date."
    if deadline < date.today():
        return "Deadline cannot be in the past. Choose today or a future date."
    return None

def _get_deadline_bucket_counts(total_unique_deadlines):
    if total_unique_deadlines <= 0:
        return 0, 0, 0
    if total_unique_deadlines == 1:
        return 1, 0, 0
    if total_unique_deadlines == 2:
        return 1, 1, 0

    high_count = max(1, (total_unique_deadlines + 2) // 3)
    medium_count = max(1, (total_unique_deadlines - high_count + 1) // 2)
    low_count = total_unique_deadlines - high_count - medium_count

    if low_count < 0:
        low_count = 0

    return high_count, medium_count, low_count


def _priority_for_deadline(deadline_value, all_deadline_values):
    deadline_date = date.fromisoformat(deadline_value)
    unique_deadlines = sorted({date.fromisoformat(value) for value in all_deadline_values})
    total_unique_deadlines = len(unique_deadlines)

    if total_unique_deadlines == 0:
        return 'Medium'

    high_count, medium_count, _ = _get_deadline_bucket_counts(total_unique_deadlines)
    deadline_rank = unique_deadlines.index(deadline_date)

    if deadline_rank < high_count:
        return 'High'
    if deadline_rank < high_count + medium_count:
        return 'Medium'
    return 'Low'


def recalculate_pending_priorities(student_id):
    conn = get_db_connection()
    pending_assignments = conn.execute(
        'SELECT id, deadline, status FROM assignments WHERE student_id = ? AND status != ? ORDER BY deadline ASC, id ASC',
        (student_id, 'Completed')
    ).fetchall()

    if not pending_assignments:
        conn.close()
        return

    grouped_deadlines = {}
    for row in pending_assignments:
        grouped_deadlines.setdefault(row['deadline'], []).append(row)

    ordered_deadlines = sorted(grouped_deadlines.keys(), key=lambda value: date.fromisoformat(value))
    high_count, medium_count, _ = _get_deadline_bucket_counts(len(ordered_deadlines))

    deadline_priority_map = {}
    for index, deadline in enumerate(ordered_deadlines):
        if index < high_count:
            deadline_priority_map[deadline] = 'High'
        elif index < high_count + medium_count:
            deadline_priority_map[deadline] = 'Medium'
        else:
            deadline_priority_map[deadline] = 'Low'

    for deadline, rows in grouped_deadlines.items():
        level_name = deadline_priority_map[deadline]
        for row in rows:
            conn.execute('UPDATE assignments SET priority = ? WHERE id = ?', (level_name, row['id']))

    conn.commit()
    conn.close()


def predict_priority(title, deadline, previous_assignments):
    deadline_values = [assignment['deadline'] for assignment in previous_assignments]
    deadline_values.append(deadline)
    priority = _priority_for_deadline(deadline, deadline_values)
    return priority, 'AI prediction: deadline-only priority assignment.'


def sort_assignments_by_deadline(assignments):
    today = date.today()
    pending = []
    completed = []

    def extract_fields(assignment):
        if isinstance(assignment, sqlite3.Row):
            return assignment['id'], assignment['deadline'], assignment['status']
        if isinstance(assignment, dict):
            return assignment.get('id'), assignment.get('deadline'), assignment.get('status')
        if len(assignment) >= 7:
            return assignment[0], assignment[4], assignment[6]
        if len(assignment) >= 6:
            return assignment[0], assignment[3], assignment[5]
        if len(assignment) >= 4:
            return assignment[0], assignment[2], assignment[3]
        return None, None, None

    for assignment in assignments:
        assignment_id, deadline_value, status = extract_fields(assignment)
        if status == 'Completed':
            completed.append(assignment)
        else:
            pending.append(assignment)

    def deadline_key(assignment):
        assignment_id, deadline_value, status = extract_fields(assignment)
        try:
            deadline_date = date.fromisoformat(deadline_value)
            days_remaining = (deadline_date - today).days
            return (days_remaining, deadline_date.isoformat(), assignment_id)
        except (TypeError, ValueError):
            return (999999, str(deadline_value), assignment_id)

    pending.sort(key=deadline_key)
    return pending + completed

# --------------------------------------------------------------------
# PAGE 1: SUBJECTS CONCEPTS HUB (DEFAULT HOME PAGE)
# --------------------------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
@app.route('/learn', methods=['GET', 'POST'])
def learn_hub():
    if request.method == 'POST':
        student_name = (request.form.get('student_name') or request.form.get('name') or '').strip()
        if student_name:
            student = get_or_create_student(student_name)
            session['student_id'] = student['id']
            session['student_name'] = student['name']
            return redirect(url_for('dashboard'))

    active_student = get_current_student()
    return render_template('learn/index.html', active_student=active_student)

@app.route('/logout')
def logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    return redirect(url_for('learn_hub'))

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
    student = get_current_student()
    if not student:
        return redirect(url_for('learn_hub'))

    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form.get('student_name') or request.form.get('name') or student['name']
        college = request.form.get('college_name') or request.form.get('college') or student['college']
        branch = request.form.get('branch_name') or request.form.get('branch') or student['branch']

        conn.execute('''
            UPDATE students
            SET name = ?, college = ?, branch = ?
            WHERE id = ?
        ''', (name, college, branch, student['id']))
        conn.commit()
        session['student_name'] = name

    student_row = conn.execute('SELECT id, name, college, branch FROM students WHERE id = ?', (student['id'],)).fetchone()
    user = (student_row['name'], student_row['college'], student_row['branch']) if student_row else (student['name'], student['college'], student['branch'])

    total = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ?", (student['id'],)).fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Completed'", (student['id'],)).fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status != 'Completed'", (student['id'],)).fetchone()[0]
    postponed = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Postponed'", (student['id'],)).fetchone()[0]
    conn.close()

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0.0

    return render_template('profile.html', user=user, total=total, completed=completed, pending=pending, postponed=postponed, completion_rate=completion_rate)

@app.route('/analytics')
def analytics():
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))
    conn = get_db_connection()
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Completed'", (student['id'],)).fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status != 'Completed'", (student['id'],)).fetchone()[0]
    postponed = conn.execute("SELECT COUNT(*) FROM assignments WHERE student_id = ? AND status = 'Postponed'", (student['id'],)).fetchone()[0]
    conn.close()
    return render_template('analytics.html', student_name=student['name'], completed=completed, pending=pending, postponed=postponed)

@app.route('/performance')
def performance():
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))
    conn = get_db_connection()
    assignments = conn.execute('SELECT * FROM assignments WHERE student_id = ? ORDER BY deadline ASC, id ASC', (student['id'],)).fetchall()
    conn.close()
    return render_template('performance.html', student_name=student['name'], assignments=assignments)

# --------------------------------------------------------------------
# PAGE 4: ASSIGNMENT DASHBOARD TABLE
# --------------------------------------------------------------------
@app.route('/dashboard')
@app.route('/index')
def dashboard():
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))
    conn = get_db_connection()
    assignments = conn.execute('SELECT * FROM assignments WHERE student_id = ? ORDER BY id DESC', (student['id'],)).fetchall()
    conn.close()
    assignments = sort_assignments_by_deadline(assignments)
    return render_template('index.html', assignments=assignments, student_name=student['name'], branch_name=student['branch'], college_name=student['college'])

# Endpoint alias for templates calling url_for('index')
@app.route('/index_alias')
def index():
    return redirect(url_for('dashboard'))

# --------------------------------------------------------------------
# ADD ASSIGNMENT FORM HANDLER (4-STEP FORM)
# --------------------------------------------------------------------
@app.route('/add', methods=['GET', 'POST'])
def add_assignment():
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))

    if request.method == 'POST':
        subject = request.form.get('subject') or request.form.get('subject_name') or 'Python'
        title = request.form.get('title') or request.form.get('assignment_title') or 'Assignment'
        deadline = request.form.get('deadline') or request.form.get('deadline_date') or ''
        status = request.form.get('status') or 'Pending'

        deadline_error = validate_deadline(deadline)
        if deadline_error:
            conn = get_db_connection()
            assignment_count = conn.execute('SELECT COUNT(*) FROM assignments WHERE student_id = ?', (student['id'],)).fetchone()[0]
            conn.close()
            return render_template('add_assignment.html', deadline_error=deadline_error, form_data=request.form, today=date.today().isoformat(), assignment_count=assignment_count), 400

        conn = get_db_connection()
        existing_assignment = conn.execute(
            '''
            SELECT id
            FROM assignments
            WHERE student_id = ?
              AND LOWER(subject) = LOWER(?)
              AND LOWER(title) = LOWER(?)
              AND deadline = ?
            LIMIT 1
            ''',
            (student['id'], subject, title, deadline)
        ).fetchone()

        if existing_assignment is not None:
            assignment_count = conn.execute('SELECT COUNT(*) FROM assignments WHERE student_id = ?', (student['id'],)).fetchone()[0]
            conn.close()
            return render_template(
                'add_assignment.html',
                duplicate_error='This assignment already exists. Please check your assignment list or enter a different assignment.',
                form_data=request.form,
                today=date.today().isoformat(),
                assignment_count=assignment_count,
            ), 400

        previous_assignments = conn.execute('SELECT deadline, priority FROM assignments WHERE student_id = ? ORDER BY deadline ASC, id ASC', (student['id'],)).fetchall()
        if previous_assignments:
            priority, prediction_message = predict_priority(title, deadline, previous_assignments)
        else:
            priority = request.form.get('priority') or 'Medium'
            prediction_message = None
        conn.execute('''
            INSERT INTO assignments (student_id, subject, title, deadline, priority, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student['id'], subject, title, deadline, priority, status))
        conn.commit()
        conn.close()
        recalculate_pending_priorities(student['id'])

        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    assignment_count = conn.execute('SELECT COUNT(*) FROM assignments WHERE student_id = ?', (student['id'],)).fetchone()[0]
    conn.close()
    return render_template('add_assignment.html', today=date.today().isoformat(), assignment_count=assignment_count)

# --------------------------------------------------------------------
# EDIT & DELETE HANDLERS
# --------------------------------------------------------------------
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_assignment(id):
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))

    conn = get_db_connection()
    assignment = conn.execute('SELECT * FROM assignments WHERE id = ? AND student_id = ?', (id, student['id'])).fetchone()

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
            WHERE id = ? AND student_id = ?
        ''', (subject, title, deadline, priority, status, id, student['id']))
        conn.commit()
        conn.close()
        recalculate_pending_priorities(student['id'])

        return redirect(url_for('dashboard'))

    conn.close()
    return render_template('edit_assignment.html', assignment=assignment, today=date.today().isoformat())

@app.route('/delete/<int:id>')
def delete_assignment(id):
    student = require_student_session()
    if not student:
        return redirect(url_for('learn_hub'))

    conn = get_db_connection()
    conn.execute('DELETE FROM assignments WHERE id = ? AND student_id = ?', (id, student['id']))
    conn.commit()
    conn.close()
    recalculate_pending_priorities(student['id'])
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    threading.Timer(1.0, lambda: webbrowser.open_new(f"http://127.0.0.1:{port}/dashboard")).start()
    app.run(host='0.0.0.0', port=port, debug=False)