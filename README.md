# 📚 R23 Assignment Deadline Tracker with AI Priority Classifier

A full-stack web application built for engineering students to track assignment deadlines, review core subject unit concepts, and automatically categorize task priorities using an AI logic layer.

---

## 🌟 Key Project Features

1. **📖 Page 1: R23 Core Subjects Concepts Hub**
   - Detailed, beginner-friendly unit lessons covering Python Programming, Data Structures (DSA), Applied Mathematics (2x2 Matrices), C Programming & Algorithmic Logic, and IT Workshop.
2. **ℹ️ Page 2: All About Project**
   - Developer documentation detailing the project folder hierarchy, file roles, and priority color badges.
3. **👤 Page 3: User Profile & Performance Metrics**
   - Student credentials manager paired with visual Chart.js analytics tracking task completion progress.
4. **📊 Page 4: Assignment Dashboard Table**
   - Full CRUD management (Create, Read, Update, Delete) with continuous Serial Numbers (`1, 2, 3...`).
5. **🤖 AI Priority Classifier Layer**
   - Scans assignment titles for urgent keywords (e.g., *Exam, Final, Lab, Project*) and evaluates deadline proximity to automatically assign **🔴 High**, **🟡 Medium**, or **🟢 Low** priority badges.

---

## 📁 VS Code Directory Hierarchy

```text
ASSIGNMENT DEDLINE TRACKER WITH PRIORITY/
├── 📁 .vscode/
│   └── launch.json
├── 📁 ai_prompts/
│   ├── evaluation_rubric.md
│   └── prompt_log.md
├── 📁 output/
│   ├── demo_screenshot.png
│   └── sample_output.txt
├── 📁 report/
│   ├── ethics_reflection.md
│   └── technical_summary.md
├── 📁 static/
│   ├── 📁 css/
│   │   └── style.css          # Global styling rules
│   └── 📁 js/
│       └── script.js         # Dialog modal handlers
├── 📁 templates/
│   ├── 📁 learn/                # Page 1: Subject Unit HTML Pages
│   │   ├── c.html            # Unit 4: C Programming & Logic
│   │   ├── dsa.html          # Unit 2: Data Structures & Sorting
│   │   ├── index.html        # Page 1 Main Concepts Hub Grid
│   │   ├── it.html           # Unit 5: IT Workshop & AI Tools
│   │   ├── math.html         # Unit 3: Applied Mathematics (2x2 Matrices)
│   │   └── python.html       # Unit 1: Python Programming
│   ├── add_assignment.html   # Add Assignment Form
│   ├── analytics.html        # Task Distribution View
│   ├── edit_assignment.html  # Edit Assignment Form
│   ├── index.html            # Page 4: Main Assignment Dashboard
│   ├── performance.html      # Performance Score Chart View
│   ├── profile.html          # Page 3: User Profile & Metrics
│   └── project_guide.html    # Page 2: All About Project Guide
├── app.py                    # Main Flask Backend Controller + AI Layer
├── database.py               # SQLite Database Initializer
├── assignments.db            # Local Database File
├── README.md                 # Project Overview Documentation
└── requirements.txt          # Required Python Packages