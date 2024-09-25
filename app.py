import os
import re
from datetime import datetime

import cv2
import face_recognition
import numpy as np
import requests
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from flask_session import Session
from pymongo import MongoClient
import secrets
import pytesseract
from PIL import Image

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Define UPLOAD_FOLDER
app.config['UPLOAD_FOLDER'] = 'uploads'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def allowed_file_mimetype(file):
    """Check if the file has an allowed MIME type."""
    allowed_mimetypes = {'image/jpeg', 'image/png'}
    return file.mimetype in allowed_mimetypes


# Connect to MongoDB
client = MongoClient(
    "mongodb+srv://adirasal2003:3PRW9xWDlRdvZNuy@clusterls.vsk8udc.mongodb.net/?retryWrites=true&w=majority&appName=ClusterLS")
db = client.get_database('locker_users')


@app.route('/')
def home():
    return render_template('register.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        # aadhar_number = request.form.get('aadharID')
        pan_number = request.form.get('panCardID')
        password = request.form.get('password')

        pan_file = request.files.get('pan_file_input')
        photo_file = request.files.get('user_photo_file_input')

        # Initialize filenames with default values
        pan_filename = None
        photo_filename = None

        isValid = False

        if pan_file:
            if allowed_file(pan_file.filename) and allowed_file_mimetype(pan_file):
                pan_filename = secure_filename(pan_file.filename)
                pan_file_path = os.path.join(app.config['UPLOAD_FOLDER'], pan_filename)
                pan_file.save(pan_file_path)

                # Extract PAN number using OCR
                pan_image = Image.open(pan_file_path)
                extracted_text = pytesseract.image_to_string(pan_image)

                # Extract the PAN number using regex
                pan_pattern = r'[A-Z]{5}[0-9]{4}[A-Z]{1}'
                extracted_pan_number = re.search(pan_pattern, extracted_text)

                if extracted_pan_number:
                    pan_number = extracted_pan_number.group(0)
                    url = "https://aadhaar-number-verification-api-using-pan-number.p.rapidapi.com/api/validation/pan_to_aadhaar"

                    # Define the payload with your PAN number and consent details
                    payload = {
                        "pan": pan_number,
                        "consent": "y",
                        "consent_text": "I hereby declare my consent agreement for fetching my information via AITAN Labs API"
                    }

                    headers = {
                        "x-rapidapi-key": "e97d3c8811msh612e502bdd56794p19b868jsned73cbe534b7",
                        "x-rapidapi-host": "aadhaar-number-verification-api-using-pan-number.p.rapidapi.com",
                        "Content-Type": "application/json"
                    }
                    # Send the POST request to the API
                    try:
                        response = requests.post(url, json=payload, headers=headers)
                        response.raise_for_status()  # Check if the request was successful

                        response_data = response.json()  # Attempt to parse the JSON response

                        # Check if response_data is not None and contains the expected structure
                        if response_data and isinstance(response_data, dict):
                            # Extract the 'link_status' from the response if it exists
                            link_status = response_data.get('result', {}).get('link_status')

                            if link_status:
                                isValid = True
                            else:
                                print("Link status not found or invalid in the response")
                        else:
                            print("Unexpected response format:", response_data)

                    except requests.exceptions.RequestException as e:
                        print("Error during API request:", e)
                    except ValueError as ve:
                        print("Error parsing JSON response:", ve)
                else:
                    return 'PAN number could not be extracted from the uploaded image.'
            else:
                return 'Invalid PAN file format. Please upload a jpg, jpeg, or png file.'

        if photo_file:
            if allowed_file(photo_file.filename) and allowed_file_mimetype(photo_file):
                photo_filename = secure_filename(photo_file.filename)
                photo_file.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_filename))
            else:
                return 'Invalid photo file format. Please upload a jpg, jpeg, or png file.'

        existing_user = db.users.find_one({'email': email})
        if existing_user:
            return 'Email already registered. Please login or use a different email.'

        pan_filename = pan_filename or ''
        photo_filename = photo_filename or ''

        if isValid:
            db.users.insert_one(
                {'username': username, 'email': email, 'panID': pan_number,
                 'password': password, 'pan_file': pan_filename,
                 'user_photo': photo_filename})
            session['user'] = {'username': username, 'email': email}
            return redirect(url_for('login'))
        else:
            return render_template('register.html', show_popup=True)

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = db.users.find_one({'email': email, 'password': password})
        if user:
            session['user'] = {'username': user['username'], 'email': user['email']}
            session['username'] = user['username']
            session['logged_in_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return redirect(url_for('homepage'))
        else:
            return 'Invalid email or password. Please try again.'

    return render_template('login.html')


@app.route('/home')
def homepage():
    user = session.get('username')
    logged_in_time = session.get('logged_in_time', 'Not available')
    if user:
        return render_template('home.html', user=user, disable_back_button=True, logged_in_time=logged_in_time)
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/download/<filename>')
def download_file(filename):
    """Serve a file from the upload folder."""
    safe_filename = secure_filename(filename)
    # Check if the file exists in the upload folder
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], safe_filename, as_attachment=True)
    else:
        return 'File not found', 404


@app.route('/access-locker', methods=['GET', 'POST'])
def access_locker():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = db.users.find_one({'username': session['username']})
    if not user or 'user_photo' not in user:
        return 'User photo not found in the database.'

    user_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], user['user_photo'])

    if request.method == 'POST':
        captured_photo = request.files['captured_photo']
        if captured_photo and allowed_file(captured_photo.filename):
            captured_photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'captured_photo.png')
            captured_photo.save(captured_photo_path)

            user_photo = face_recognition.load_image_file(user_photo_path)
            captured_image = face_recognition.load_image_file(captured_photo_path)

            user_photo_encoding = face_recognition.face_encodings(user_photo)[0]
            captured_image_encoding = face_recognition.face_encodings(captured_image)[0]

            results = face_recognition.compare_faces([user_photo_encoding], captured_image_encoding)

            if results[0]:
                # Detect blink for liveness
                captured_image_cv2 = cv2.imread(captured_photo_path)
                liveness_passed = detect_blink(captured_image_cv2)
                if liveness_passed:
                    #return 'Face Verified. Access granted.'
                    return render_template('locker.html')
                else:
                    return render_template('verificationFailed.html')
                    #return 'Liveness check failed. Possible spoofing detected. Access denied.'

            else:
                return render_template('verificationFailed.html')
                #return 'Face verification failed. Access denied.'

        return 'Invalid photo. Please try again.'

    return render_template('verification.html', user_photo=user['user_photo'])


def eye_aspect_ratio(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    ear = (A + B) / (2.0 * C)
    return ear


def detect_blink(captured_image):
    EYE_AR_THRESH = 0.25

    # Convert image to RGB (face_recognition uses RGB)
    rgb_image = cv2.cvtColor(captured_image, cv2.COLOR_BGR2RGB)

    # Find face landmarks
    face_landmarks_list = face_recognition.face_landmarks(rgb_image)

    if not face_landmarks_list:
        return False

    # Extract eye landmarks
    landmarks = face_landmarks_list[0]
    left_eye = np.array(landmarks['left_eye'])
    right_eye = np.array(landmarks['right_eye'])

    # Calculate EAR for each eye
    left_ear = eye_aspect_ratio(left_eye)
    right_ear = eye_aspect_ratio(right_eye)
    ear = (left_ear + right_ear) / 2.0

    # Blink detection
    if ear < EYE_AR_THRESH:
        return True

    return False


if __name__ == '__main__':
    app.run(debug=True, port=5000)
