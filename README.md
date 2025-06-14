
# 🧠 Smart Face Attendance System

A face recognition-based attendance app built with **Flask**, **OpenCV**, and **KNN classifier**. It supports:
- Admin login & user registration
- Face registration (admin only)
- Public face-based attendance marking (no login needed)
- Attendance analytics with charts & export options
- Daily user attendance history

---

## 🚀 Features

✅ Face-based attendance (KNN-based)  
✅ One attendance allowed per user per day  
✅ Admin dashboard to manage users  
✅ Public attendance without login  
✅ View & export attendance analytics (PDF/Excel)  
✅ Image preview of registered faces  
✅ Mobile responsive UI  
✅ Optional: Beep & popup alerts during recognition

---
## 📂 Folder Structure

├── app.py # Main Flask app
├── static/
│ ├── faces/ # Captured face images
│ ├── face_recognition_model.pkl
├── templates/
│ ├── base.html
│ ├── login.html
│ ├── home.html
│ ├── analytics.html
│ ├── register_face.html
│ ├── my_history.html
│ ├── public.html
│ └── registered_faces.html
├── Attendance/ # CSV & export files
├── config.py # Secret key & DB config
├── requirements.txt
└── README.md

## ⚙️ Requirements

- Python 3.7+
- OpenCV
- Flask
- SQLAlchemy
- Pandas
- Scikit-learn
- joblib
- openpyxl
- reportlab

---

## 📦 Installation

1. **Clone the repo**
```bash
git clone https://github.com/yourusername/face-attendance-app.git
cd face-attendance-app
```

2. **Create a virtual environment (optional)**
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the app**
```bash
python app.py
```

Visit: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 👤 User Roles

- **Admin**: Login, register users, add face data, view analytics, and manage users
- **User**: Can log in, view their attendance history, or mark attendance from public page

---

## 📸 How Face Attendance Works

1. Admin registers face (50 images captured via webcam).
2. Trains a KNN model and saves it as `face_recognition_model.pkl`.
3. Public users can mark attendance using their registered face.
4. Attendance is logged into a date-wise CSV file inside `/Attendance/`.

---

## ✨ Enhancements (Already Added)

- Prevent duplicate attendance per day
- Face data preview + delete option
- Notification popups on attendance mark
- Admin-only face registration
- Mobile-friendly layout

---

## 📤 Export & Analytics

- View attendance summary by date (admin only)
- Export to PDF and Excel
- Chart visualizations using Chart.js

---

## 📌 TODO (optional ideas)

- Email/SMS notifications
- Daily/weekly summary reports
- OTP verification for registration
- Face recognition confidence score

---

## 🛡️ License

This project is for educational/demo purposes. Feel free to adapt and enhance.

✍️ Author
Om Ranjan
📧 Email: omranjankvrajgir@gmail.com
🌐 Portfolio: https://portfolio-ejug.vercel.app
🔗 LinkedIn: linkedin.com/in/omranjan07

Default Admin Login
Username: admin

Password: admin123
👉 (Change this after first login)