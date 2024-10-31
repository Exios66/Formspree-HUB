from flask import Flask, render_template, request, jsonify
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

# Initialize Flask
app = Flask(__name__)
app.config['DEBUG'] = True  # Enable debug mode

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

# Basic routes
@app.route('/')
def index():
    try:
        return render_template('index.html')
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return str(e), 500

@app.route('/survey/<category>')
def survey(category):
    try:
        return render_template(f'surveys/{category}.html')
    except Exception as e:
        app.logger.error(f"Error in survey route: {str(e)}")
        return str(e), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {str(error)}")
    return render_template('500.html'), 500

# Create database tables
def init_db():
    with app.app_context():
        db.create_all()
        app.logger.info("Database tables created")

if __name__ == '__main__':
    try:
        init_db()
        app.run(debug=True, port=8000)
    except Exception as e:
        print(f"Startup error: {str(e)}")