# Technical Summary & System Architecture

## 🚀 Overview
The **R23 Assignment Deadline Tracker** is a dynamic web application built with Python (Flask) and SQLite. It incorporates an AI Priority Classifier to dynamically categorize academic workloads based on deadlines, effort estimation, and subject weights.

---

## 🏗️ Technology Stack

| Layer | Technology Used |
| :--- | :--- |
| **Backend Framework** | Python (Flask) |
| **Database** | SQLite3 (`assignments.db`) |
| **Frontend UI** | HTML5, CSS3, JavaScript |
| **Styling & Icons** | Custom Responsive CSS |
| **Version Control** | Git & GitHub |

---

## ⚙️ Core System Capabilities

1. **AI Priority Engine:** Computes an urgency score using a weighted matrix based on days remaining and estimated completion time.
2. **Subject Unit Pages:** Dedicated learning references for 5 core R23 academic subjects (C, DSA, Python, Math, IT Workshop).
3. **Analytics Dashboard:** Graphical summary showing completed, pending, and critical assignments.