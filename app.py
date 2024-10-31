from flask import Flask, render_template, request, jsonify
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.utils import secure_filename
import time

# Initialize Flask
from flask import Flask
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Make sure this is set
csrf = CSRFProtect(app)
app.config.update(
    SECRET_KEY='your-secret-key-here',  # Change this to a secure secret key
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,  # 5MB max file size
    UPLOAD_FOLDER='uploads',
    ALLOWED_EXTENSIONS={'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
)

# Initialize CSRF protection
csrf = CSRFProtect(app)

# Create uploads folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Configure SQLite database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'surveys.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Initialize FastAPI
api = FastAPI()

# Database Models
class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# File Upload Routes
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return str(e), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        if 'upload' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['upload']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400

        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # Create a new Survey record
            survey = Survey(
                title=filename,
                category='upload',
                # Add any other fields you need
            )
            db.session.add(survey)
            db.session.commit()

            return jsonify({
                'message': 'File uploaded successfully',
                'file': {
                    'id': survey.id,
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'path': filepath
                }
            })

    except Exception as e:
        app.logger.error(f"Error in upload route: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def get_files():
    try:
        # Add your file listing logic here
        files = Survey.query.all()  # Adjust based on your needs
        return jsonify({'files': [{'id': f.id, 'title': f.title} for f in files]})
    except Exception as e:
        app.logger.error(f"Error in files route: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Static Routes
@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/help')
def help():
    return render_template('help.html')

# Survey Routes
@app.route('/surveys/<path>')
def survey(path):
    try:
        template_path = f"surveys/{path}"
        return render_template(template_path)
    except Exception as e:
        app.logger.error(f"Error in survey route: {template_path}")
        return "Template not found", 404

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {str(error)}")
    return render_template('500.html'), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File is too large. Maximum size is 5MB'}), 413

@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return jsonify({'error': 'CSRF token missing or invalid'}), 400

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created")

if __name__ == '__main__':
    port = 5000  # or whatever port you're using
    print("\n" + "=" * 50)
    print(f"Flask server running on port {port}")
    print(f"URL: http://localhost:{port}")
    print("=" * 50 + "\n")
    
    # Keep the message visible by adding a delay
    try:
        app.run(debug=True, port=port)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        time.sleep(2)  # Give time to read shutdown message