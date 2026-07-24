import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = "super_secret_assignment_tracker_key"

# Database Connection Helper
def get_db_connection():
    conn = sqlite3.connect('assignments.db')
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------------------------------------------------
# AI PRIORITY CLASSIFIER ENGINE (MATHEMATICAL MODEL)
# --------------------------------------------------------------------
def calculate_priority(deadline_str, estimated_hours, difficulty, subject):
    """
    Computes an AI Urgency Priority Score from 0 to 100 based on:
    - Days remaining until deadline
    - Estimated effort hours
    - Subject difficulty & R23 core academic weight
    """
    try:
        deadline_date = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_remaining = (deadline_date - today).days

        if days_remaining < 0:
            days_remaining = 0  # Overdue tasks treat days remaining as 0

        # Subject Difficulty Weights
        weights = {
            "Data Structures & Algorithms": 1.5,
            "C Programming": 1.4,
            "Applied Mathematics": 1.3,
            "Python Web Dev": 1.2,
            "IT Workshop": 1.0
        }
        subject_weight = weights.get(subject, 1.1)

        # Effort Weight
        effort_factor = float(estimated_hours) * 5.0

        # Urgency Calculation
        urgency_component = (100.0 / (days_remaining + 1.0)) * 0.50
        effort_component = effort_factor * subject_weight

        priority_score = min(100, int(urgency_component + effort_component))

        # Priority Tag Classification
        if priority_score >= 75:
            priority_tag = "🔴 HIGH / CRITICAL"
        elif priority_score >= 45:
            priority_tag = "🟡 MEDIUM PRIORITY"
        else:
            priority_tag = "🟢 LOW PRIORITY"

        return priority_score, priority_tag, days_remaining

    except Exception as e:
        return 50, "🟡 MEDIUM PRIORITY", 3

# --------------------------------------------------------------------
# APPLICATION ROUTES
# --------------------------------------------------------------------

# 1. Main Dashboard Route
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

# 2. Add Assignment Route
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

# 3. Edit Assignment Route
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

# 4. Delete Assignment Route
@app.route('/delete/<int:id>')
def delete_assignment(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM assignments WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Assignment deleted.', 'danger')
    return redirect(url_for('index'))

# 5. Analytics Route
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

# 6. Profile Route
@app.route('/profile')
def profile():
    return render_template('profile.html')

# 7. Project Guide Route
@app.route('/project_guide')
def project_guide():
    return render_template('project_guide.html')

# 8. R23 Core Subject Guides Routes
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
# SERVER LAUNCHER (CONFIGURED FOR LOCAL & RENDER CLOUD DEPLOYMENT)
# --------------------------------------------------------------------
if __name__ == '__main__':
    # Reads the environment port assigned by Render dynamically, defaulting to 5000 locally
    port = int(os.environ.get("PORT", 5000))
    # Binds to 0.0.0.0 so Render cloud services can detect and open public web ports
    app.run(host='0.0.0.0', port=port, debug=False)