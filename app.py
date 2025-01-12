# import the necessary packages
import os
import h5py
import numpy as np
import tensorflow as tf
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from tensorflow.keras.preprocessing.image import load_img, img_to_array
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash

# Global variables
folder_dict = {'0': 'Apple___Apple_scab', '1': 'Apple___Black_rot', '2': 'Apple___Cedar_apple_rust', '3': 'Apple___healthy', '4': 'Blueberry___healthy', '5': 'Cherry_(including_sour)___Powdery_mildew', '6': 'Cherry_(including_sour)___healthy', '7': 'Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot', '8': 'Corn_(maize)___Common_rust_', '9': 'Corn_(maize)___Northern_Leaf_Blight', '10': 'Corn_(maize)___healthy', '11': 'Grape___Black_rot', '12': 'Grape___Esca_(Black_Measles)', '13': 'Grape___Leaf_blight_(Isariopsis_Leaf_Spot)', '14': 'Grape___healthy', '15': 'Orange___Haunglongbing_(Citrus_greening)', '16': 'Peach___Bacterial_spot', '17': 'Peach___healthy', '18': 'Pepper,_bell___Bacterial_spot', '19': 'Pepper,_bell___healthy', '20': 'Potato___Early_blight', '21': 'Potato___Late_blight', '22': 'Potato___healthy', '23': 'Raspberry___healthy', '24': 'Soybean___healthy', '25': 'Squash___Powdery_mildew', '26': 'Strawberry___Leaf_scorch', '27': 'Strawberry___healthy', '28': 'Tomato___Bacterial_spot', '29': 'Tomato___Early_blight', '30': 'Tomato___Late_blight', '31': 'Tomato___Leaf_Mold', '32': 'Tomato___Septoria_leaf_spot', '33': 'Tomato___Spider_mites Two-spotted_spider_mite', '34': 'Tomato___Target_Spot', '35': 'Tomato___Tomato_Yellow_Leaf_Curl_Virus', '36': 'Tomato___Tomato_mosaic_virus', '37': 'Tomato___healthy'}

# functions used in the app
def predict_image(filepath):
    model = tf.keras.models.load_model('static/models/plant_disease_mobilenetv2.h5')

    # Load and preprocess the image
    image = load_img(filepath, target_size=(224, 224))
    image_array = img_to_array(image) / 255.0
    image_array = np.expand_dims(image_array, axis=0)

    # Make a prediction
    prediction = model.predict(image_array)
    class_index = np.argmax(prediction)

    return folder_dict[str(class_index + 1)]

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = '2d6899c71c83a9c805ebb6d3aa5ceb0c'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_BINDS'] = {'classinfo': 'sqlite:///classinfo.db'}
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)
db = SQLAlchemy(app)

# Configure the upload folder
UPLOAD_FOLDER = os.path.abspath('static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Classes
# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

# ClassInfo model for storing class names and disease info
class ClassInfo(db.Model):
    __bind_key__ = 'classinfo'
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

# routes

# Home route
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

#=====================================================================================

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find the user in the database
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session.permanent = True
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.')
            return redirect(url_for('login'))

    return render_template('login.html')

#=====================================================================================

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        session.clear()
        flash('Registration successful! Please log in.')
        return redirect(url_for('home'))

    return render_template('register.html')

#=====================================================================================

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page.')
        return redirect(url_for('home'))
    return render_template('dashboard.html')

#=====================================================================================

# Route to add or update class information
@app.route('/add_class_info', methods=['GET', 'POST'])
def add_class_info():
    if request.method == 'POST':
        class_name = request.form['class_name']
        description = request.form['description']

        # Check if class name already exists
        existing_class = ClassInfo.query.filter_by(class_name=class_name).first()
        if existing_class:
            # Update the existing class description
            existing_class.description = description
            db.session.commit()
            flash(f'Class "{class_name}" updated successfully.')
        else:
            # Add new class info
            new_class = ClassInfo(class_name=class_name, description=description)
            db.session.add(new_class)
            db.session.commit()
            flash(f'Class "{class_name}" added successfully.')

        return redirect(url_for('dashboard'))

    return render_template('addclassinfo.html', folder_dict=folder_dict)

#=====================================================================================

# Upload route
@app.route('/dashboard/upload', methods=['POST'])
def upload():
    if 'user_id' not in session:
        flash('Please log in to access this page.')
        return redirect(url_for('home'))

    if 'file' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        flash('No selected file.')
        return redirect(url_for('dashboard'))

    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        flash('File uploaded successfully.')
        image_url = url_for('static', filename=f'uploads/{filename}')
        return render_template('dashboard.html', image_url=image_url)

    return redirect(url_for('dashboard'))

#=====================================================================================

# Predict route
@app.route('/dashboard/predict', methods=['POST'])
def predict():
    if 'user_id' not in session:
        flash('Please log in to access this page.')
        return redirect(url_for('home'))

    image_path = request.form['image_path'].replace('/static/', 'static/')

    # Make a prediction
    class_name = predict_image(image_path)

    # Fetch class info from the ClassInfo table
    class_info = ClassInfo.query.filter_by(class_name=class_name).first()

    if class_info:
        description = class_info.description
    else:
        description = "No information available for this class."
    image_path = '/' + image_path
    print(f"imagepath = {image_path}")
    # Redirect to the results page and pass the prediction and description
    return render_template('results.html', prediction=class_name, description=description, image_path=image_path)

#=====================================================================================

# Logout route
@app.route('/logout', methods=['GET','POST'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.')
    return redirect(url_for('home'))




#=====================================================================================
# Run the app
if __name__ == '__main__':
    # app.run(debug=True)
    app.run(host='0.0.0.0', port=8080, debub=False)

