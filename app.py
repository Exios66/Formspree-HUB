from flask import Flask, render_template, request, jsonify
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Initialize both Flask and FastAPI
app = Flask(__name__)
api = FastAPI()

# Configure Flask
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///surveys.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configure CORS for FastAPI
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Models
class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    responses = db.relationship('Response', backref='survey', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('survey.id'), nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Pydantic models for FastAPI
class SurveyCreate(BaseModel):
    category: str
    title: str

class SurveyResponse(BaseModel):
    survey_id: int
    answers: dict

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/survey/<category>')
def survey(category):
    return render_template(f'surveys/{category}.html')

# FastAPI Routes
@api.get("/api/surveys")
async def get_surveys():
    surveys = Survey.query.all()
    return [{
        "id": s.id,
        "category": s.category,
        "title": s.title,
        "created_at": s.created_at
    } for s in surveys]

@api.post("/api/surveys")
async def create_survey(survey: SurveyCreate):
    new_survey = Survey(
        category=survey.category,
        title=survey.title
    )
    db.session.add(new_survey)
    db.session.commit()
    return {"id": new_survey.id, "message": "Survey created successfully"}

@api.post("/api/responses")
async def submit_response(response: SurveyResponse):
    survey = Survey.query.get(response.survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    new_response = Response(
        survey_id=response.survey_id,
        answers=response.answers
    )
    db.session.add(new_response)
    db.session.commit()
    return {"message": "Response submitted successfully"}

@api.get("/api/responses/{survey_id}")
async def get_responses(survey_id: int):
    responses = Response.query.filter_by(survey_id=survey_id).all()
    return [{
        "id": r.id,
        "answers": r.answers,
        "created_at": r.created_at
    } for r in responses]

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Create the database tables
def init_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    init_db()
    # Run the Flask app with uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)