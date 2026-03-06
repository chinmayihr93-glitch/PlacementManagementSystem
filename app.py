from flask import Flask, request, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask import render_template
from flask_jwt_extended import get_jwt
from flask_jwt_extended import jwt_required, get_jwt
from flask import redirect
from flask import session

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config['JWT_SECRET_KEY'] = 'super-secret-key'
jwt = JWTManager(app)

# ----------------- Database Connection -----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",            # your MySQL user
    password="Chin@2006",   # your MySQL password
    database="placement_management"
)

# ----------------- Root Route -----------------

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin')
def admin_page():
    return render_template('admin_login.html')

# ----------------- Student Registration -----------------
@app.route('/register_student', methods=['POST'])
def register_student():
    try:
        data = request.get_json()  # get JSON from request
        name = data['name']
        email = data['email']
        password = data['password']

        hashed_password = generate_password_hash(password)

        cursor = db.cursor()
        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        if cursor.fetchone():
            return jsonify({"message": "Email already registered!"}), 400

        cursor.execute(
            "INSERT INTO students (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        db.commit()

        return jsonify({"message": "Student Registered Successfully!"})

    except KeyError as e:
        return jsonify({"error": f"Missing field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------- Student Login -----------------
from flask_jwt_extended import create_access_token

@app.route('/student_login', methods=['POST'])
def student_login():

    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return "Email or Password missing!"

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
    user = cursor.fetchone()

    if user and user['password'] == password:

        # Store data in session
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['name'] = user['name']

        if user['role'] == 'admin':
            return redirect('/admin_dashboard')
        else:
            return redirect('/student_dashboard')

    return "Invalid Credentials"
# ----------------- Admin Login -----------------
@app.route('/admin_login', methods=['POST'])
def login_admin():
    try:
        data = request.get_json()
        username = data['username']
        password = data['password']

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admin WHERE username=%s", (username,))
        admin = cursor.fetchone()

        if admin:
            if password == admin['password']:
                return jsonify({"message": f"Welcome Admin {admin['username']}!"})
            else:
                return jsonify({"message": "Incorrect password!"}), 401
        else:
            return jsonify({"message": "Admin not found!"}), 404

    except KeyError as e:
        return jsonify({"error": f"Missing field: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/add_company', methods=['POST'])
def add_company():
    company_name = request.form['company_name']

    cursor = db.cursor()
    cursor.execute("INSERT INTO companies (company_name) VALUES (%s)", (company_name,))
    db.commit()

    return "Company Added Successfully!"
@app.route('/add_job', methods=['POST'])
def add_job():
    company_id = request.form['company_id']
    role = request.form['role']
    salary = request.form['salary']

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO jobs (company_id, role, salary) VALUES (%s, %s, %s)",
        (company_id, role, salary)
    )
    db.commit()

    return "Job Added Successfully!"
@app.route('/view_jobs', methods=['GET'])
def view_jobs():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT jobs.id, companies.company_name, jobs.role, jobs.salary,
                   jobs.eligibility_cgpa, jobs.required_skills
            FROM jobs
            JOIN companies ON jobs.company_id = companies.id
        """)
        jobs = cursor.fetchall()
        return jsonify(jobs)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ----------------- Student Apply Job -----------------
@app.route('/apply_job', methods=['POST'])
@jwt_required()
def apply_job():
    try:
        student_id = get_jwt_identity()
        data = request.get_json()
        job_id = data['job_id']

        cursor = db.cursor()

        cursor.execute(
            "SELECT * FROM applications WHERE student_id=%s AND job_id=%s",
            (student_id, job_id)
        )
        if cursor.fetchone():
            return jsonify({"message": "Already applied for this job!"}), 400

        cursor.execute(
            "INSERT INTO applications (student_id, job_id, status) VALUES (%s, %s, %s)",
            (student_id, job_id, "Applied")
        )
        db.commit()

        return jsonify({"message": "Applied successfully!"})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
# ----------------- Update Application Status (Admin) -----------------
@app.route('/update_status', methods=['PUT'])
@jwt_required()
def update_status():
    claims = get_jwt()

    if claims["role"] != "admin":
        return jsonify({"message": "Admins only!"}), 403

    data = request.get_json()
    application_id = data['application_id']
    new_status = data['status']

    cursor = db.cursor()
    cursor.execute(
        "UPDATE applications SET status=%s WHERE id=%s",
        (new_status, application_id)
    )
    db.commit()

    return jsonify({"message": "Status updated successfully!"})
# ---------------- View My Applications (Student) ----------------
@app.route('/my_applications', methods=['GET'])
@jwt_required()
def my_applications():
    student_id = get_jwt_identity()

    cursor = db.cursor(dictionary=True)

    query = """
    SELECT applications.id,
           companies.company_name,
           jobs.role,
           jobs.salary,
           applications.status
    FROM applications
    JOIN jobs ON applications.job_id = jobs.id
    JOIN companies ON jobs.company_id = companies.id
    WHERE applications.student_id = %s
    """

    cursor.execute(query, (student_id,))
    result = cursor.fetchall()

    return jsonify(result)
@app.route('/all_jobs', methods=['GET'])
def all_jobs():
    cursor = db.cursor(dictionary=True)

    query = """
    SELECT jobs.id, companies.company_name, jobs.role, jobs.salary
    FROM jobs
    JOIN companies ON jobs.company_id = companies.id
    """

    cursor.execute(query)
    result = cursor.fetchall()

    return jsonify(result)
@app.route('/all_applications', methods=['GET'])
@jwt_required()
def all_applications():
    claims = get_jwt()

    if claims["role"] != "admin":
        return jsonify({"message": "Admins only!"}), 403

    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT applications.id,
               students.name,
               companies.company_name,
               jobs.role,
               applications.status
        FROM applications
        JOIN students ON applications.student_id = students.id
        JOIN jobs ON applications.job_id = jobs.id
        JOIN companies ON jobs.company_id = companies.id
    """)
    result = cursor.fetchall()

    return jsonify(result)
@app.route('/admin_dashboard')
def admin_dashboard_page():

    cursor = db.cursor(dictionary=True)

    search = request.args.get('search')

    if search:
        cursor.execute("""
            SELECT a.id, s.name, c.company_name, j.role, a.status
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN jobs j ON a.job_id = j.id
            JOIN companies c ON j.company_id = c.id
            WHERE s.name LIKE %s
        """, ('%' + search + '%',))
    else:
        cursor.execute("""
            SELECT a.id, s.name, c.company_name, j.role, a.status
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN jobs j ON a.job_id = j.id
            JOIN companies c ON j.company_id = c.id
        """)

    applications = cursor.fetchall()

    return render_template('admin_dashboard.html', applications=applications)
@app.route('/update_status_from_dashboard', methods=['POST'])
def update_status_from_dashboard():

    application_id = request.form['application_id']
    status = request.form['status']

    cursor = db.cursor()
    cursor.execute(
        "UPDATE applications SET status=%s WHERE id=%s",
        (status, application_id)
    )
    db.commit()

    return redirect('/admin_dashboard')
@app.route('/student_dashboard')

def student_dashboard():

    if 'user_id' not in session:
        return redirect('/login_page')

    if session['role'] != 'student':
        return "Students Only!"

    student_id = session['user_id']

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT j.id, c.company_name, j.role, j.salary
        FROM jobs j
        JOIN companies c ON j.company_id = c.id
    """)
    jobs = cursor.fetchall()

    cursor.execute("""
        SELECT a.id, c.company_name, j.role, j.salary, a.status
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        JOIN companies c ON j.company_id = c.id
        WHERE a.student_id = %s
    """, (student_id,))
    applications = cursor.fetchall()

    return render_template(
        'student_dashboard.html',
        jobs=jobs,
        applications=applications
    )
    
@app.route('/apply_job_from_dashboard', methods=['POST'])
def apply_job_from_dashboard():

    if 'user_id' not in session:
        return redirect('/login_page')

    student_id = session['user_id']
    job_id = request.form['job_id']

    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO applications (student_id, job_id, status) VALUES (%s, %s, 'Applied')",
        (student_id, job_id)
    )
    db.commit()

    return redirect('/student_dashboard')

# ----------------- Run Server -----------------
if __name__ == "__main__":
    app.run(debug=True)