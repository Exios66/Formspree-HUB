from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_wtf.csrf import CSRFProtect, CSRFError
from werkzeug.utils import secure_filename
import time
from flask_wtf import FlaskForm
from wtforms import StringField
from config import config

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    csrf.init_app(app)

    # Ensure upload folder exists
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

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

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    # Routes
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
                
                survey = Survey(
                    title=filename,
                    category='upload',
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
            files = Survey.query.all()
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

    return app

if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    port = int(os.getenv('PORT', 5000))
    
    print("\n" + "=" * 50)
    print(f"Flask server running on port {port}")
    print(f"URL: http://localhost:{port}")
    print("=" * 50 + "\n")
    
    try:
        app.run(host='0.0.0.0', port=port)
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        time.sleep(2)
