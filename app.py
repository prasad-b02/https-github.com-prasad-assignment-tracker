import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "super_secret_assignment_tracker_key"

# --------------------------------------------------------------------
# DATABASE SETUP & AUTO-SEEDING FOR CLOUD DEPLOYMENT
# --------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect('assignments.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Automatically creates table and seeds sample assignments on Render."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            subject TEXT NOT NULL,
            unit TEXT NOT NULL,
            deadline TEXT NOT NULL,
            estimated_hours REAL NOT NULL,
            difficulty TEXT NOT NULL,
            status TEXT NOT NULL,
            priority_score INTEGER,
            priority_tag TEXT
        )
    ''')
    
    # If the database is empty, automatically populate default sample tasks
    count = conn.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
    if count == 0:
        sample_data = [
            ("Implement Bubble Sort", "Data Structures & Algorithms", "Unit 2", "2026-07-26", 4.0, "Hard", "Pending", 85, "🔴 HIGH / CRITICAL"),
            ("Matrix Multiplication Lab", "Applied Mathematics", "Unit 1", "2026-07-30", 2.5, "Medium", "In Progress", 60, "🟡 MEDIUM PRIORITY"),
            ("Python Flask Setup", "Python Web Dev", "Unit 3", "2026-08-05", 1.5, "Easy", "Pending", 30, "🟢 LOW PRIORITY")
        ]
        conn.executemany('''
            INSERT INTO assignments (title, subject, unit, deadline, estimated_hours, difficulty, status, priority_score, priority_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_data)
        
    conn.commit()
    conn.close()

# Initialize database right when app boots up
init_db()

# --------------------------------------------------------------------
# AI PRIORITY CLASSIFIER ENGINE
# --------------------------------------------------------------------
def calculate_priority(deadline_str, estimated_hours, difficulty, subject):
    """Calculates AI Urgency Priority Score (0-100)."""
    try:
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (deadline_date - today).days

        if days_remaining < 0:
            days_remaining = 0

        weights = {
            "Data Structures & Algorithms": 1.5,
            "C Programming": 1.4,
            "Applied Mathematics": 1.3,
            "Python Web Dev": 1.2,
            "IT Workshop": 1.0
        }
        subject_weight = weights.get(subject, 1.1)
        effort_factor = float(estimated_hours) * 5.0

        urgency_component = (100.0 / (days_remaining + 1.0)) * 0.50
        effort_component = effort_factor * subject_weight

        priority_score = min(100, int(urgency_component + effort_component))

        if priority_score >= 75:
            priority_tag = "🔴 HIGH / CRITICAL"
        elif priority_score >= 45:
            priority_tag = "🟡 MEDIUM PRIORITY"
        else:
            priority_tag = "🟢 LOW PRIORITY"

        return priority_score, priority_tag, days_remaining

    except Exception:
        return 50, "🟡 MEDIUM PRIORITY", 3

# --------------------------------------------------------------------
# APPLICATION ROUTES
# --------------------------------------------------------------------

# 1. Main Dashboard
@app.route('/')
def index():
    conn = get_db_connection()
    assignments_raw = conn.execute('SELECT * FROM assignments ORDER BY deadline ASC').fetchall()
    conn.close()

    assignments = []
    for row in assignments_raw:
        item = dict(row)
        score, tag, days_left = calculate_priority(
            item['deadline'], 
            item['estimated_hours'], 
            item['difficulty'], 
            item['subject']
        )
        item['priority_score'] = score
        item['priority_tag'] = tag
        item['days_left'] = days_left
        assignments.append(item)

    return render_template('index.html', assignments=assignments)

# 2. Add Assignment
@app.route('/add', methods=['GET', 'POST'])
def add_assignment():
    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        unit = request.form['unit']
        deadline = request.form['deadline']
        estimated_hours = request.form['estimated_hours']
        difficulty = request.form['difficulty']
        status = "Pending"

        score, tag, _ = calculate_priority(deadline, estimated_hours, difficulty, subject)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO assignments (title, subject, unit, deadline, estimated_hours, difficulty, status, priority_score, priority_tag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, subject, unit, deadline, estimated_hours, difficulty, status, score, tag))
        conn.commit()
        conn.close()

        flash('Assignment added successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('add_assignment.html')

# 3. Edit Assignment
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_assignment(id):
    conn = get_db_connection()
    assignment = conn.execute('SELECT * FROM assignments WHERE id = ?', (id,)).fetchone()

    if request.method == 'POST':
        title = request.form['title']
        subject = request.form['subject']
        unit = request.form['unit']
        deadline = request.form['deadline']
        estimated_hours = request.form['estimated_hours']
        difficulty = request.form['difficulty']
        status = request.form['status']

        score, tag, _ = calculate_priority(deadline, estimated_hours, difficulty, subject)

        conn.execute('''
            UPDATE assignments
            SET title = ?, subject = ?, unit = ?, deadline = ?, estimated_hours = ?, difficulty = ?, status = ?, priority_score = ?, priority_tag = ?
            WHERE id = ?
        ''', (title, subject, unit, deadline, estimated_hours, difficulty, status, score, tag, id))
        conn.commit()
        conn.close()

        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('index'))

    conn.close()
    return render_template('edit_assignment.html', assignment=assignment)

# 4. Delete Assignment
@app.route('/delete/<int:id>')
def delete_assignment(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM assignments WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Assignment deleted.', 'danger')
    return redirect(url_for('index'))

# 5. Analytics
@app.route('/analytics')
def analytics():
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM assignments').fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status = 'Completed'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE status != 'Completed'").fetchone()[0]
    high_priority = conn.execute("SELECT COUNT(*) FROM assignments WHERE priority_tag LIKE '%HIGH%' OR priority_tag LIKE '%CRITICAL%'").fetchone()[0]
    conn.close()

    stats = {
        'total': total,
        'completed': completed,
        'pending': pending,
        'high_priority': high_priority
    }
    return render_template('analytics.html', stats=stats)

# 6. Profile & Project Guides
@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/project_guide')
def project_guide():
    return render_template('project_guide.html')

# 7. R23 Core Subject Study Guides
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
# SERVER LAUNCHER
# --------------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)