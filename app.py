import sqlite3
import pandas as pd
from datetime import date
from flask import Flask, render_template, request, redirect, send_file, session
from reportlab.platypus import SimpleDocTemplate, Table
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

def send_attendance_alert(
    student_name,
    student_email,
    attendance_percentage
):

    sender_email = "tanmaybhavsardb@gmail.com"
    app_password = "jvbs lxuo kaqp gitw"

    subject = "Attendance Warning"

    body = f"""
Hello {student_name},

Your attendance is currently {attendance_percentage}%.

Please improve your attendance to reach the required 75%.

Attendance Management System
"""

    msg = MIMEText(body)

    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = student_email

    try:

        server = smtplib.SMTP(
            "smtp.gmail.com",
            587
        )

        server.starttls()

        server.login(
            sender_email,
            app_password
        )

        server.send_message(msg)

        server.quit()

        print(
            f"Email sent to {student_email}"
        )

    except Exception as e:

        print(
            "Email Error:",
            e
        )

app = Flask(__name__)

app.secret_key = "attendance_secret_key"

def init_db():

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # -------------------------
    # Students Table
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        course TEXT,
        email TEXT
    )
    """)

    # -------------------------
    # Users Table
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # -------------------------
    # Attendance Table
    # -------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT
    )
    """)

    # -------------------------
    # Default Admin User
    # -------------------------
    cursor.execute(
        "SELECT * FROM users WHERE username=?",
        ("admin",)
    )

    admin = cursor.fetchone()

    if not admin:

        cursor.execute(
            """
            INSERT INTO users(username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "admin",
                generate_password_hash("admin123"),
                "Admin"
            )
        )

    # -------------------------
    # Default Teacher User
    # -------------------------
    cursor.execute(
        "SELECT * FROM users WHERE username=?",
        ("teacher",)
    )

    teacher = cursor.fetchone()

    if not teacher:

        cursor.execute(
            """
            INSERT INTO users(username, password, role)
            VALUES (?, ?, ?)
            """,
            (
                "teacher",
                generate_password_hash("teacher123"),
                "Teacher"
            )
        )

    conn.commit()

    # Optional (only for testing)
    cursor.execute("SELECT username, role FROM users")
    print(cursor.fetchall())

    conn.close()


init_db()

@app.route("/")
def home():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM attendance
    WHERE status='Present'
    """)
    present_today = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM attendance
    WHERE status='Absent'
    """)
    absent_today = cursor.fetchone()[0]

    total_attendance = present_today + absent_today

    overall_percentage = 0

    if total_attendance > 0:
        overall_percentage = round(
            (present_today / total_attendance) * 100,
            2
        )

    cursor.execute("""
    SELECT students.name,
           attendance.status,
           attendance.date
    FROM attendance
    JOIN students
    ON students.id = attendance.student_id
    ORDER BY attendance.id DESC
    LIMIT 5
    """)

    recent_activity = cursor.fetchall()

    cursor.execute("""
    SELECT students.name,
           COUNT(attendance.id) as total,
           SUM(
               CASE
               WHEN attendance.status='Present'
               THEN 1
               ELSE 0
               END
           ) as present
    FROM students
    LEFT JOIN attendance
    ON students.id = attendance.student_id
    GROUP BY students.id
    """)

    attendance_data = cursor.fetchall()

    top_student = None
    top_percentage = 0
    low_attendance_students = []

    for row in attendance_data:

        name = row[0]
        total = row[1]
        present = row[2] or 0

        percentage = 0

        if total > 0:
            percentage = round(
                (present / total) * 100,
                2
            )

        if percentage > top_percentage:
            top_percentage = percentage
            top_student = name

        if total > 0 and percentage < 75:
            low_attendance_students.append(
                (name, percentage)
            )

    conn.close()

    return render_template(
        "index.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        recent_activity=recent_activity,
        overall_percentage=overall_percentage,
        top_student=top_student,
        top_percentage=top_percentage,
        low_attendance_students=low_attendance_students
    )
    
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    
    if "user" not in session:
        return redirect("/login")
    
    if session.get("role") != "Admin":
     return "Access Denied! Only Admin can add students."
    
    if request.method == "POST":

        name = request.form["name"]
        course = request.form["course"]
        email = request.form["email"]

        conn = sqlite3.connect("database.db")

        cursor = conn.cursor()

        cursor.execute(
    """
    INSERT INTO students(
        name,
        course,
        email
    )
    VALUES (?, ?, ?)
    """,
    (
        name,
        course,
        email
    )
    )

        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add_student.html")
@app.route("/students")
def students():
    
    if "user" not in session:
     return redirect("/login")

    conn = sqlite3.connect("database.db")

    cursor = conn.cursor()

    search = request.args.get("search", "")

    cursor.execute(
    """
    SELECT *
    FROM students
    WHERE name LIKE ?
    """,
    ('%' + search + '%',)
)

    students = cursor.fetchall()

    conn.close()

    return render_template(
    "students.html",
    students=students,
    total_found=len(students)
)
    
@app.route("/attendance", methods=["GET", "POST"])
    
def attendance():
    if "user" not in session:
       return redirect("/login")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

           student_id = request.form["student_id"]

           attendance_date = request.form["attendance_date"]

           status = request.form["status"]
 
           cursor.execute(
               """
                INSERT INTO attendance
                (student_id, date, status)
                VALUES (?, ?, ?)
                """,
                (
                   student_id,
                   attendance_date,
                   status
                )
            )
           
           conn.commit()

    cursor.execute("SELECT * FROM students")

    students = cursor.fetchall()

    conn.close()
    return render_template(
        "attendance.html",
        students=students
    )
@app.route("/history")
        
def history():
    
    if "user" not in session:
     return redirect("/login")
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT students.name,
           attendance.date,
           attendance.status
    FROM attendance
    JOIN students
    ON students.id = attendance.student_id
    """)

    records = cursor.fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records
    )
    
@app.route("/report")
    
def report():
    
    print("REPORT FUNCTION STARTED")

    if "user" not in session:
     return redirect("/login")
 
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT students.name,
           COUNT(attendance.id),
           SUM(CASE WHEN attendance.status='Present'
                    THEN 1 ELSE 0 END)
    FROM students
    LEFT JOIN attendance
    ON students.id = attendance.student_id
    GROUP BY students.id
    """)

    data = cursor.fetchall()

    report_data = []

    for row in data:

        name = row[0]
        total = row[1]
        present = row[2] or 0

        percentage = 0

        if total > 0:
            percentage = round((present / total) * 100, 2)

        report_data.append(
            (name, total, present, percentage)
        )
    df = pd.DataFrame(
    report_data,
    columns=[
        "Student Name",
        "Total Classes",
        "Present",
        "Attendance %"
    ]
)

    df.to_csv(
            "reports/attendance_report.csv",
            index=False
    )
    df.to_excel(
        "reports/attendance_report.xlsx",
        index=False
    )
    
    pdf = SimpleDocTemplate(
    "reports/attendance_report.pdf"
)

    pdf_data = [
    [
        "Student Name",
        "Total Classes",
        "Present",
        "Attendance %"
    ]
]

    for row in report_data:
     pdf_data.append(list(row))

    table = Table(pdf_data)

    pdf.build([table])

    print("PDF CREATED")

    print("Excel file generated successfully")

    conn.close()

    return render_template(
            "report.html",
            report_data=report_data
        )
    
@app.route("/download_report")
def download_report():
    
    if "user" not in session:
        return redirect("/login")

    
    return send_file(
        "reports/attendance_report.csv",
        as_attachment=True
    )
    
@app.route("/download_excel")
def download_excel():

    if "user" not in session:
        return redirect("/login")

    return send_file(
        "reports/attendance_report.xlsx",
        as_attachment=True
    )
    
@app.route("/delete_student/<int:id>")
def delete_student(id):

    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "Admin":
        return "⛔ Access Denied! Only Admin can delete student records."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM students WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/students") 

@app.route("/edit_student/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    if "user" not in session:
        return redirect("/login")

    if session.get("role") != "Admin":
        return "⛔ Access Denied! Only Admin can edit student records."

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == "POST":

        name = request.form["name"]
        course = request.form["course"]

        cursor.execute(
            """
            UPDATE students
            SET name=?, course=?
            WHERE id=?
            """,
            (name, course, id)
        )

        conn.commit()
        conn.close()

        return redirect("/students")

    cursor.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cursor.fetchone()

    conn.close()

    return render_template(
        "edit_student.html",
        student=student
    )
           
@app.route("/student_profile/<int:id>")
def student_profile(id):

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE student_id=?
        """,
        (id,)
    )

    total_classes = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM attendance
        WHERE student_id=?
        AND status='Present'
        """,
        (id,)
    )

    present = cursor.fetchone()[0]

    absent = total_classes - present

    attendance_percentage = 0

    if total_classes > 0:
        attendance_percentage = round(
            (present / total_classes) * 100,
            2
        )

    conn.close()

    return render_template(
        "student_profile.html",
        student=student,
        total_classes=total_classes,
        present=present,
        absent=absent,
        attendance_percentage=attendance_percentage
    )

@app.route("/predictor", methods=["GET", "POST"])
def predictor():

    result = None

    if request.method == "POST":

        total_classes = int(
            request.form["total_classes"]
        )

        present_classes = int(
            request.form["present_classes"]
        )

        attendance_percentage = round(
            (present_classes / total_classes) * 100,
            2
        )

        needed_classes = 0

        current_present = present_classes
        current_total = total_classes

        while (
            current_present / current_total
        ) < 0.75:

            current_present += 1
            current_total += 1
            needed_classes += 1

        status = "Good ✅"

        if attendance_percentage < 75:
            status = "Below 75% ⚠️"

        result = {
            "attendance_percentage":
            attendance_percentage,

            "needed_classes":
            needed_classes,

            "status":
            status
        }

    return render_template(
        "predictor.html",
        result=result
    )

@app.route("/analytics", methods=["GET", "POST"])
def analytics():
    if "user" not in session:
     return redirect("/login")
    present = 0
    absent = 0
    attendance_percentage = 0
    
    trend_dates = []
    trend_counts = []
    
    from_date = ""
    to_date = ""

    if request.method == "POST":

        from_date = request.form["from_date"]
        to_date = request.form["to_date"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE status='Present'
            AND date BETWEEN ? AND ?
            """,
            (from_date, to_date)
        )

        present = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM attendance
            WHERE status='Absent'
            AND date BETWEEN ? AND ?
            """,
            (from_date, to_date)
        )

        absent = cursor.fetchone()[0]
        
        cursor.execute(
            """
            SELECT date,
                SUM(
                    CASE
                        WHEN status='Present'
                        THEN 1
                        ELSE 0
                    END
                )
            FROM attendance
            WHERE date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date
            """,
            (from_date, to_date)
        )

        trend_data = cursor.fetchall()

        for row in trend_data:

            trend_dates.append(row[0])

            trend_counts.append(row[1])

        total = present + absent

        if total > 0:
            attendance_percentage = round(
                (present / total) * 100,
                2
            )
            
        conn.close()

    return render_template(
    "analytics.html",
    present=present,
    absent=absent,
    attendance_percentage=attendance_percentage,
    from_date=from_date,
    to_date=to_date,
    trend_dates=trend_dates,
    trend_counts=trend_counts
)
    
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT username, password, role
            FROM users
            WHERE username=?
            """,
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            db_username = user[0]
            db_password = user[1]
            role = user[2]

            if check_password_hash(
                db_password,
                password
            ):

                session["user"] = db_username
                session["role"] = role

                return redirect("/")

        error = "Invalid Username or Password"

        return render_template(
            "login.html",
            error=error
        )

    return render_template("login.html")

@app.route("/logout")
def logout():

    session.pop("user", None)

    return redirect("/login")

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(students)")
print(cursor.fetchall())

conn.close()
           
@app.route("/test_email")
def test_email():

    send_attendance_alert(
        "Tanmay",
        "tanmaybhavsardb@gmail.com",
        62
    )

    return "Test Email Sent!"

@app.route("/send_alert/<student_name>/<float:percentage>")
def send_alert(student_name, percentage):

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT email
        FROM students
        WHERE name=?
        """,
        (student_name,)
    )

    result = cursor.fetchone()

    conn.close()

    if result:

        student_email = result[0]

        send_attendance_alert(
            student_name,
            student_email,
            percentage
        )

        return f"Alert sent to {student_name}"

    return "Student email not found"

if __name__ == "__main__":
    app.run(debug=True)
