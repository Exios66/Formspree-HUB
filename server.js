const express = require('express');
const multer = require('multer');
const path = require('path');
const cors = require('cors');
const fs = require('fs');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Configure multer for file upload
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = 'uploads';
        // Create uploads directory if it doesn't exist
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir);
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        // Create unique filename with timestamp
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: 5 * 1024 * 1024 // 5MB limit
    },
    fileFilter: (req, file, cb) => {
        // Define allowed file types
        const allowedTypes = /jpeg|jpg|png|gif|pdf|doc|docx|txt/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);

        if (extname && mimetype) {
            return cb(null, true);
        }
        cb(new Error('Invalid file type. Only images, PDFs, and documents are allowed.'));
    }
});

// Database configuration (using MongoDB as an example)
const mongoose = require('mongoose');
mongoose.connect('mongodb://localhost/fileupload', {
    useNewUrlParser: true,
    useUnifiedTopology: true
});

// File upload schema
const FileSchema = new mongoose.Schema({
    filename: String,
    originalName: String,
    path: String,
    size: Number,
    mimetype: String,
    uploadDate: { type: Date, default: Date.now },
    uploadedBy: String
});

const File = mongoose.model('File', FileSchema);

// Routes
app.post('/api/upload', upload.single('upload'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        // Create file record in database
        const fileRecord = new File({
            filename: req.file.filename,
            originalName: req.file.originalname,
            path: req.file.path,
            size: req.file.size,
            mimetype: req.file.mimetype,
            uploadedBy: req.body.email
        });

        await fileRecord.save();

        // Send progress updates (simulation)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 25;
            if (progress <= 100) {
                res.write(JSON.stringify({ progress }));
            }
            if (progress === 100) {
                clearInterval(progressInterval);
                res.end();
            }
        }, 500);

        res.status(200).json({
            message: 'File uploaded successfully',
            file: {
                name: req.file.originalname,
                size: req.file.size,
                path: req.file.path
            }
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get file list
app.get('/api/files', async (req, res) => {
    try {
        const files = await File.find().sort({ uploadDate: -1 });
        res.json(files);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Delete file
app.delete('/api/files/:id', async (req, res) => {
    try {
        const file = await File.findById(req.params.id);
        if (!file) {
            return res.status(404).json({ error: 'File not found' });
        }

        // Delete from filesystem
        fs.unlink(file.path, async (err) => {
            if (err) {
                return res.status(500).json({ error: err.message });
            }
            // Delete from database
            await File.findByIdAndDelete(req.params.id);
            res.json({ message: 'File deleted successfully' });
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});