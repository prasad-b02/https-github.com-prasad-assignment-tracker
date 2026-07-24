from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import webbrowser
from threading import Timer
from datetime import datetime
from database import create_table

app = Flask(__name__)
create_table()

DATABASE = "assignments.db"
MIN_DATE = "2026-07-23"

def get_user_profile():
    try:
        conn = sqlite3.connect(DATABASE)
        user = conn.execute("SELECT student_name, college_name, branch_name FROM user_profile WHERE id=1").fetchone()
        conn.close()
        return user if user else None
    except Exception:
        return None

def open_browser():
    """Automatically launches default browser to project URL."""
    webbrowser.open_new("http://127.0.0.1:5000/")

# ------------------ Page 1: Subjects Concepts Hub ------------------
@app.route("/")
def learn_hub():
    user = get_user_profile()
    return render_template("learn/index.html", user=user)

# ------------------ Page 2: All About Project Guide ------------------
@app.route("/about-project")
def project_guide():
    user = get_user_profile()
    return render_template("project_guide.html", user=user)

# ------------------ Page 3: User Profile & Performance ------------------
@app.route("/profile", methods=["GET", "POST"])
def profile_setup():
    conn = sqlite3.connect(DATABASE)

    if request.method == "POST":
        name = request.form["student_name"]
        college = request.form["college_name"]
        branch = request.form["branch_name"]
        
        conn.execute("""
        INSERT OR REPLACE INTO user_profile (id, student_name, college_name, branch_name) 
        VALUES (1, ?, ?, ?)
        """, (name, college, branch))
        conn.commit()
        conn.close()
        return redirect(url_for("profile_setup"))

    user = get_user_profile()
    
    total = conn.execute("SELECT COUNT(*) FROM assignments").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status='Completed'").fetchone()[0]
    pending = conn.execute("SELECT COUNT(*) FROM assignments WHERE status='Pending'").fetchone()[0]
    postponed = conn.execute("SELECT COUNT(*) FROM assignments WHERE status='Postponed'").fetchone()[0]

    assignments = conn.execute("SELECT * FROM assignments ORDER BY deadline ASC").fetchall()
    conn.close()

    completion_rate = round((completed / total * 100), 1) if total > 0 else 0

    return render_template("profile.html", 
                           user=user,
                           total=total,
                           completed=completed,
                           pending=pending,
                           postponed=postponed,
                           completion_rate=completion_rate,
                           assignments=assignments)

# ------------------ Page 4: Assignment Dashboard ------------------
@app.route("/dashboard")
def index():
    user = get_user_profile()
    if not user:
        return redirect(url_for("profile_setup"))

    conn = sqlite3.connect(DATABASE)
    assignments = conn.execute("SELECT * FROM assignments ORDER BY deadline ASC").fetchall()
    conn.close()

    return render_template("index.html", 
                           assignments=assignments, 
                           student_name=user[0], 
                           college_name=user[1], 
                           branch_name=user[2])

# ------------------ Add Assignment ------------------
@app.route("/add", methods=["GET", "POST"])
def add_assignment():
    if request.method == "POST":
        subject = request.form["subject"]
        title = request.form["title"]
        deadline = request.form["deadline"]
        priority = request.form["priority"]
        status = request.form["status"]

        # Backend check: Ensure deadline is present date (2026-07-23) or future date
        if deadline < MIN_DATE:
            deadline = MIN_DATE

        conn = sqlite3.connect(DATABASE)
        conn.execute(
            "INSERT INTO assignments (subject, title, deadline, priority, status) VALUES (?, ?, ?, ?, ?)",
            (subject, title, deadline, priority, status)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    return render_template("add_assignment.html")

# ------------------ Edit Assignment ------------------
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_assignment(id):
    conn = sqlite3.connect(DATABASE)

    if request.method == "POST":
        subject = request.form["subject"]
        title = request.form["title"]
        deadline = request.form["deadline"]
        priority = request.form["priority"]
        status = request.form["status"]

        # Backend check: Ensure deadline is present date (2026-07-23) or future date
        if deadline < MIN_DATE:
            deadline = MIN_DATE

        conn.execute(
            "UPDATE assignments SET subject=?, title=?, deadline=?, priority=?, status=? WHERE id=?",
            (subject, title, deadline, priority, status, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    assignment = conn.execute("SELECT * FROM assignments WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("edit_assignment.html", assignment=assignment)

# ------------------ Delete Assignment ------------------
@app.route("/delete/<int:id>")
def delete_assignment(id):
    conn = sqlite3.connect(DATABASE)
    conn.execute("DELETE FROM assignments WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

# ------------------ Subject Lessons Routes ------------------
@app.route("/learn/python")
def learn_python():
    return render_template("learn/python.html")

@app.route("/learn/dsa")
def learn_dsa():
    return render_template("learn/dsa.html")

@app.route("/learn/math")
def learn_math():
    return render_template("learn/math.html")

@app.route("/learn/c")
def learn_c():
    return render_template("learn/c.html")

@app.route("/learn/it")
def learn_it():
    return render_template("learn/it.html")

if __name__ == "__main__":
    Timer(1.2, open_browser).start()
    app.run(debug=False)