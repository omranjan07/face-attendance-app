import os
import cv2
import numpy as np
import joblib
from sklearn.neighbors import KNeighborsClassifier

def capture_faces(user_folder, max_images=50):
    os.makedirs(user_folder, exist_ok=True)
    cap = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    count = 0
    print("📸 Starting webcam. Press ESC to cancel.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)

        for (x, y, w, h) in faces:
            face_img = frame[y:y+h, x:x+w]
            face_resized = cv2.resize(face_img, (50, 50))
            img_path = os.path.join(user_folder, f'{count}.jpg')
            cv2.imwrite(img_path, face_resized)
            count += 1

            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, f'Images Captured: {count}/{max_images}', (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

            if count >= max_images:
                break

        cv2.imshow('Capturing Faces', frame)
        if cv2.waitKey(1) == 27 or count >= max_images:
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"✅ Saved {count} images to {user_folder}")


def train_model(base_dir='static/faces', model_path='static/face_recognition_model.pkl'):
    faces, labels = [], []

    for user_dir in os.listdir(base_dir):
        user_path = os.path.join(base_dir, user_dir)
        if os.path.isdir(user_path):
            for img_name in os.listdir(user_path):
                img_path = os.path.join(user_path, img_name)
                img = cv2.imread(img_path)
                if img is not None:
                    resized = cv2.resize(img, (50, 50)).flatten()
                    faces.append(resized)
                    labels.append(user_dir)

    if not faces:
        print("❌ No training data found.")
        return

    knn = KNeighborsClassifier(n_neighbors=5)
    knn.fit(faces, labels)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(knn, model_path)

    print(f"✅ Model trained and saved at {model_path}")


if __name__ == '__main__':
    print("👤 New User Registration")
    name = input("Enter full name (e.g., om): ").strip()
    roll = input("Enter roll number (e.g., 101): ").strip()
    user_folder = os.path.join('static/faces', f'{name}_{roll}')

    capture_faces(user_folder)
    train_model()
