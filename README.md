# Formspree-HUB

A comprehensive file upload and survey management system built with Flask and modern web technologies.

## Features

- Advanced file upload system with drag-and-drop support
- Real-time file analysis
- Progress tracking
- Survey management
- Theme switching (Light/Dark/Nature)
- Responsive design
- Form handling with Formspree integration

## Local Development Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/Formspree-HUB.git
cd Formspree-HUB
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configurations
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the development server:
```bash
flask run
```

The application will be available at `http://localhost:5000`

## Production Deployment

The static frontend is deployed on GitHub Pages, while the Flask backend should be deployed on a production server.

### GitHub Pages Setup

The static frontend is served from the `docs/` directory. Any changes to the frontend should be made in the appropriate files in this directory.

### Backend Deployment

1. Set environment variables:
```bash
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
DATABASE_URL=your-database-url
```

2. Run with a production server:
```bash
gunicorn -w 4 "app:create_app('production')"
```

## Project Structure

```
├── app.py              # Flask application
├── config.py           # Configuration settings
├── requirements.txt    # Python dependencies
├── docs/              # Static frontend (GitHub Pages)
│   └── index.html     # Main frontend page
├── static/            # Static assets
│   └── js/           # JavaScript files
├── templates/         # Flask templates
│   └── surveys/      # Survey templates
└── uploads/          # File upload directory
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
