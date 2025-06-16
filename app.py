from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from config import Config
import pandas as pd
import os, joblib, cv2, numpy as np
from glob import glob
from sklearn.neighbors import KNeighborsClassifier

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# --------------------------
# Database Model
# --------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

# --------------------------
# Helper: Face Training
# --------------------------
def train_model():
    data, labels = [], []
    for user_dir in os.listdir('static/faces'):
        folder = os.path.join('static/faces', user_dir)
        if os.path.isdir(folder):
            for img in os.listdir(folder):
                img_path = os.path.join(folder, img)
                image = cv2.imread(img_path)
                if image is not None:
                    resized = cv2.resize(image, (50, 50)).flatten()
                    data.append(resized)
                    labels.append(user_dir)
    if data:
        model = KNeighborsClassifier(n_neighbors=5)
        model.fit(data, labels)
        joblib.dump(model, 'static/face_recognition_model.pkl')

# --------------------------
# Helper: Face Capture
# --------------------------
def capture_faces(folder, max_images=50):
    cap = cv2.VideoCapture(0)
    count = 0
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    while count < max_images:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            roi = frame[y:y+h, x:x+w]
            resized = cv2.resize(roi, (50, 50))
            file_path = os.path.join(folder, f"{count}.jpg")
            cv2.imwrite(file_path, resized)
            count += 1
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f"Captured: {count}/{max_images}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("Register Face", frame)
        if cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

# --------------------------
# Root + Auth Routes
# --------------------------
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    session.clear()  # 🧹 Clear session every time login page is opened

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and user.check_password(request.form['password']):
            session['user'] = user.username
            session['role'] = user.role
            return redirect(url_for('home'))
        flash('Invalid username or password.', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --------------------------
# Register Face (Admin Only)
# --------------------------
@app.route('/register-face', methods=['GET', 'POST'])
def register_face():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form.get('username').strip()
        roll = request.form.get('roll').strip()

        if not username or not roll:
            flash("Both username and roll are required.", "warning")
            return redirect(url_for('register_face'))

        # Confirm user exists in DB
        user_exists = User.query.filter_by(username=username).first()
        if not user_exists:
            flash("❌ User not found. Please add the user first.", "warning")
            return redirect(url_for('register_face'))

        # Ensure roll is not already used in any folder
        face_dir = 'static/faces'
        existing_rolls = [folder for folder in os.listdir(face_dir) if folder.endswith(f"_{roll}")]
        if existing_rolls:
            flash("⚠️ This roll number is already registered with another user.", "danger")
            return redirect(url_for('register_face'))

        # Proceed to register
        folder_name = f"{username}_{roll}"
        folder_path = os.path.join(face_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)

        capture_faces(folder_path)
        train_model()

        flash(f"✅ Face registered for {folder_name} and model retrained.", "success")
        return redirect(url_for('register_face'))

    return render_template('register_face.html')



# --------------------------
# Admin Dashboard
# --------------------------
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    query = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    per_page = 10

    if query:
        users = User.query.filter(User.username.ilike(f"%{query}%")).all()
        pagination = None
    else:
        pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
        users = pagination.items

    # Count roles
    counts = {'admin': 0, 'user': 0}
    for u in User.query.all():
        counts[u.role] += 1

    return render_template(
        'admin_dashboard.html',
        users=users,
        total_users=User.query.count(),
        role_counts=counts,
        pagination=pagination,
        query=query
    )


# --------------------------
#  reset password Admin 
# --------------------------
@app.route('/reset-password/<int:user_id>', methods=['GET', 'POST'])
def reset_password(user_id):
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        user.set_password(new_password)
        db.session.commit()
        flash(f"🔐 Password reset for {user.username}", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('reset_password.html', user=user)



# --------------------------
# Update User
# --------------------------
@app.route('/update-user/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_username = request.form.get('username')
        new_role = request.form.get('role')

        user.username = new_username
        user.role = new_role
        db.session.commit()

        flash("✅ User updated successfully.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('update_user.html', user=user)



# --------------------------
# Delete User
# --------------------------

@app.route('/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    user = User.query.get(user_id)

    if not user:
        flash("❌ User not found.", "warning")
        return redirect(url_for('admin_dashboard'))

    # Prevent deleting self
    if user.username == session['user']:
        flash("❌ You cannot delete your own admin account.", "danger")
        return redirect(url_for('admin_dashboard'))

    # If admin is being deleted, check total number of admins
    if user.role == 'admin':
        total_admins = User.query.filter_by(role='admin').count()
        if total_admins <= 1:
            flash("⚠️ At least one admin must remain in the system.", "warning")
            return redirect(url_for('admin_dashboard'))

    db.session.delete(user)
    db.session.commit()
    flash(f"✅ User '{user.username}' deleted successfully.", "success")
    return redirect(url_for('admin_dashboard'))




# --------------------------
# Home Dashboard (Daily Attendance)
# --------------------------
@app.route('/home')
def home():
    if 'user' not in session:
        return redirect(url_for('login'))

    today_str = date.today().strftime("%m_%d_%y")
    path = f"Attendance/Attendance-{today_str}.csv"
    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("Name,Roll,Time\n")

    names, rolls, times = [], [], []
    if os.path.exists(path) and os.stat(path).st_size > 0:
        df = pd.read_csv(path)
        names = df['Name'].tolist()
        rolls = df['Roll'].tolist()
        times = df['Time'].tolist()

    totalreg = len(os.listdir('static/faces'))
    return render_template('home.html', names=names, rolls=rolls, times=times, l=len(names), totalreg=totalreg)

# --------------------------
# Analytics (Admin Only)
# --------------------------
@app.route('/analytics', methods=['GET', 'POST'])
def analytics():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    selected_date, names, counts, records = None, [], [], []
    if request.method == 'POST':
        try:
            selected_date = request.form.get('selected_date')
            file_path = f"Attendance/Attendance-{pd.to_datetime(selected_date).strftime('%m_%d_%y')}.csv"
            if os.path.exists(file_path) and os.stat(file_path).st_size > 0:
                df = pd.read_csv(file_path)
                records = df.to_dict(orient='records')
                summary = df['Name'].value_counts()
                names, counts = list(summary.index), list(map(int, summary.values))
            else:
                flash("No data found.", "warning")
        except Exception as e:
            flash(str(e), "danger")

    return render_template('analytics.html', names=names, counts=counts, selected_date=selected_date, records=records)

# --------------------------
# Add User (Admin Only)
# --------------------------
@app.route('/add-user', methods=['GET', 'POST'])
def add_user():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "warning")
        else:
            new_user = User(username=username, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("User registered successfully.", "success")
            return redirect(url_for('admin_dashboard'))

    return render_template('add_user.html')


# --------------------------
# User Attendance History
# --------------------------
@app.route('/my-history')
def my_history():
    if 'user' not in session or session['role'] == 'admin':
        return redirect(url_for('login'))

    user = session['user']
    records = []
    for file in sorted(glob('Attendance/Attendance-*.csv')):
        if os.stat(file).st_size > 0:
            df = pd.read_csv(file)
            filtered = df[df['Name'].astype(str).str.startswith(user + '_')]
            if not filtered.empty:
                date_str = file.split('-')[-1].split('.')[0]
                filtered['Date'] = pd.to_datetime(date_str, format="%m_%d_%y").strftime("%d-%b-%Y")
                records.extend(filtered.to_dict(orient='records'))
    return render_template('my_history.html', records=records)

# --------------------------
# Public Attendance Marking Page
# --------------------------
@app.route('/public')
def public_home():
    return render_template('public.html')

@app.route('/mark-attendance')
def mark_attendance():
    import winsound  # ✅ Beep sound (Windows only)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    model = joblib.load('static/face_recognition_model.pkl')

    cap = cv2.VideoCapture(0)
    recognized = False
    matched_user = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            roi = frame[y:y+h, x:x+w]
            resized = cv2.resize(roi, (50, 50)).flatten().reshape(1, -1)

            try:
                prediction = model.predict(resized)[0]
                matched_user = prediction
                recognized = True

                if log_attendance(matched_user):
                    flash(f"✅ Attendance marked for {matched_user}.", "success")
                    winsound.Beep(1000, 200)
                    cv2.putText(frame, f"{matched_user} - Marked", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                else:
                    flash(f"⚠️ Attendance already marked for {matched_user}.", "warning")
                    cv2.putText(frame, f"{matched_user} - Already Marked", (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                break

            except Exception as e:
                print("Prediction error:", e)

        if not recognized:
            cv2.putText(frame, "Capturing... Please hold still", (10, 450),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)

        cv2.imshow("Face Attendance", frame)

        if recognized or cv2.waitKey(1) == 27:
            break

    cap.release()
    cv2.destroyAllWindows()
    return redirect(url_for('public_home'))


# --------------------------
# Helper: Log Attendance
# --------------------------
def log_attendance(username):
    from datetime import datetime
    today = datetime.today().strftime("%m_%d_%y")
    now = datetime.now().strftime("%H:%M:%S")
    path = f"Attendance/Attendance-{today}.csv"

    if not os.path.exists(path):
        with open(path, 'w') as f:
            f.write("Name,Roll,Time\n")

    df = pd.read_csv(path)
    # Prevent duplicate entry for today
    if username in df['Name'].astype(str).tolist():
        return False  # Already marked today

    roll = username.split('_')[1]
    with open(path, 'a') as f:
        f.write(f"{username},{roll},{now}\n")
    return True  # Marked successfully

# --------------------------
# Export PDF-Execl
# --------------------------
@app.route('/export-excel', methods=['POST'])
def export_excel():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    selected_date = request.form.get('selected_date')
    try:
        file_path = f"Attendance/Attendance-{pd.to_datetime(selected_date).strftime('%m_%d_%y')}.csv"
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            output_path = f"Attendance/Export-{selected_date}.xlsx"
            df.to_excel(output_path, index=False)
            return send_from_directory('Attendance', os.path.basename(output_path), as_attachment=True)
        else:
            flash("File not found.", "danger")
    except Exception as e:
        flash(f"Error exporting: {e}", "danger")

    return redirect(url_for('analytics'))

@app.route('/export-pdf', methods=['POST'])
def export_pdf():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    selected_date = request.form.get('selected_date')
    try:
        file_path = f"Attendance/Attendance-{pd.to_datetime(selected_date).strftime('%m_%d_%y')}.csv"
        pdf_path = f"Attendance/Export-{selected_date}.pdf"

        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            c = canvas.Canvas(pdf_path, pagesize=A4)
            width, height = A4

            c.setFont("Helvetica-Bold", 14)
            c.drawString(180, height - 50, f"Attendance Report - {selected_date}")
            c.setFont("Helvetica", 12)
            c.drawString(50, height - 80, "Generated by Smart Attendance System")

            # Table headers
            y = height - 120
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y, "Name")
            c.drawString(250, y, "Roll")
            c.drawString(400, y, "Time")

            c.setFont("Helvetica", 11)
            y -= 20
            for _, row in df.iterrows():
                if y < 50:  # page break
                    c.showPage()
                    y = height - 50
                c.drawString(50, y, str(row['Name']))
                c.drawString(250, y, str(row['Roll']))
                c.drawString(400, y, str(row['Time']))
                y -= 20

            c.save()
            return send_from_directory('Attendance', os.path.basename(pdf_path), as_attachment=True)
        else:
            flash("File not found.", "danger")
    except Exception as e:
        flash(f"Error exporting PDF: {e}", "danger")

    return redirect(url_for('analytics'))


# --------------------------
# Registerd face (Admin Only)
# --------------------------
@app.route('/registered-faces')
def registered_faces():
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    face_data = []
    base_path = 'static/faces'

    if os.path.exists(base_path):
        for folder in os.listdir(base_path):
            folder_path = os.path.join(base_path, folder)
            if os.path.isdir(folder_path):
                images = [
                    f"{folder}/{img}"
                    for img in os.listdir(folder_path)
                    if img.endswith(".jpg")
                ]
                face_data.append({
                    'user': folder,
                    'images': images[:5]  # show up to 5 previews
                })

    return render_template('registered_faces.html', face_data=face_data)
# ==================
# delete user 
# ==================
@app.route('/delete-face/<username>', methods=['POST'])
def delete_face(username):
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    folder_path = os.path.join('static/faces', username)
    if os.path.exists(folder_path):
        import shutil
        shutil.rmtree(folder_path)
        train_model()  # Retrain model after deletion
        flash(f"Deleted face data for {username}", "success")
    else:
        flash("Folder not found.", "warning")

    return redirect(url_for('registered_faces'))

# ==================
# Download face data 
# ==================

@app.route('/download-face/<username>')
def download_face_zip(username):
    if 'user' not in session or session['role'] != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))

    folder_path = os.path.join('static/faces', username)
    zip_path = os.path.join('static/faces', f"{username}.zip")

    if os.path.exists(zip_path):
        os.remove(zip_path)  # Remove old zip if exists

    if os.path.exists(folder_path):
        import zipfile
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, folder_path))

        return send_from_directory('static/faces', f"{username}.zip", as_attachment=True)
    else:
        flash("❌ Folder not found.", "danger")
        return redirect(url_for('registered_faces'))

# Application entry
if __name__ == '__main__':
    app.run(debug=True)