const express = require('express');
const multer = require('multer');
const path = require('path');
const cors = require('cors');
const fs = require('fs');
const morgan = require('morgan');
const helmet = require('helmet');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const sharp = require('sharp');
const ffmpeg = require('fluent-ffmpeg');
const dotenv = require('dotenv');
const { v4: uuidv4 } = require('uuid');

// Load environment variables
dotenv.config();

const app = express();
const port = process.env.PORT || 3000;

// Security middleware
app.use(helmet());
app.use(compression());

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per windowMs
});
app.use('/api/', limiter);

// Logging middleware
app.use(morgan('combined'));

// Basic middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));

// Configure multer for file upload
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        const uploadDir = 'uploads';
        if (!fs.existsSync(uploadDir)) {
            fs.mkdirSync(uploadDir);
        }
        cb(null, uploadDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = uuidv4();
        cb(null, uniqueSuffix + path.extname(file.originalname));
    }
});

const upload = multer({
    storage: storage,
    limits: {
        fileSize: 10 * 1024 * 1024 // 10MB limit
    },
    fileFilter: (req, file, cb) => {
        const allowedTypes = /jpeg|jpg|png|gif|pdf|doc|docx|txt|mp4|mov|avi|mp3|wav/;
        const extname = allowedTypes.test(path.extname(file.originalname).toLowerCase());
        const mimetype = allowedTypes.test(file.mimetype);

        if (extname && mimetype) {
            return cb(null, true);
        }
        cb(new Error('Invalid file type. Only images, videos, audio, PDFs, and documents are allowed.'));
    }
});

// Database configuration
const mongoose = require('mongoose');
mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost/fileupload', {
    useNewUrlParser: true,
    useUnifiedTopology: true
}).catch(err => {
    console.error('MongoDB connection error:', err);
});

// File upload schema
const FileSchema = new mongoose.Schema({
    filename: String,
    originalName: String,
    path: String,
    size: Number,
    mimetype: String,
    uploadDate: { type: Date, default: Date.now },
    uploadedBy: String,
    metadata: {
        dimensions: {
            width: Number,
            height: Number
        },
        duration: Number,
        fileType: String,
        thumbnailPath: String
    },
    tags: [String],
    isPublic: { type: Boolean, default: false }
});

const File = mongoose.model('File', FileSchema);

// Helper function to process image files
async function processImage(filePath) {
    const metadata = await sharp(filePath).metadata();
    const thumbnailPath = `thumbnails/${path.basename(filePath)}`;
    
    await sharp(filePath)
        .resize(200, 200, { fit: 'inside' })
        .toFile(thumbnailPath);
        
    return {
        dimensions: {
            width: metadata.width,
            height: metadata.height
        },
        thumbnailPath
    };
}

// Helper function to process video files
function processVideo(filePath) {
    return new Promise((resolve, reject) => {
        ffmpeg.ffprobe(filePath, (err, metadata) => {
            if (err) return reject(err);
            resolve({
                duration: metadata.format.duration,
                dimensions: {
                    width: metadata.streams[0].width,
                    height: metadata.streams[0].height
                }
            });
        });
    });
}

// Routes
app.post('/api/upload', upload.single('upload'), async (req, res) => {
    try {
        if (!req.file) {
            return res.status(400).json({ error: 'No file uploaded' });
        }

        let metadata = {
            fileType: path.extname(req.file.originalname).toLowerCase().substr(1)
        };

        // Process files based on type
        if (req.file.mimetype.startsWith('image/')) {
            const imageData = await processImage(req.file.path);
            metadata = { ...metadata, ...imageData };
        } else if (req.file.mimetype.startsWith('video/')) {
            const videoData = await processVideo(req.file.path);
            metadata = { ...metadata, ...videoData };
        }

        const fileRecord = new File({
            filename: req.file.filename,
            originalName: req.file.originalname,
            path: req.file.path,
            size: req.file.size,
            mimetype: req.file.mimetype,
            uploadedBy: req.body.email,
            metadata,
            tags: req.body.tags ? req.body.tags.split(',') : [],
            isPublic: req.body.isPublic === 'true'
        });

        await fileRecord.save();

        res.status(200).json({
            message: 'File uploaded successfully',
            file: {
                id: fileRecord._id,
                name: req.file.originalname,
                size: req.file.size,
                path: req.file.path,
                metadata
            }
        });
    } catch (error) {
        if (req.file) {
            fs.unlink(req.file.path, () => {}); // Clean up on error
        }
        res.status(500).json({ error: error.message });
    }
});

// Get file list with pagination and filtering
app.get('/api/files', async (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = parseInt(req.query.limit) || 10;
        const skip = (page - 1) * limit;
        const fileType = req.query.fileType;
        const sortBy = req.query.sortBy || 'uploadDate';
        const sortOrder = req.query.sortOrder === 'asc' ? 1 : -1;

        let query = {};
        if (fileType) {
            query['metadata.fileType'] = fileType;
        }

        const files = await File.find(query)
            .sort({ [sortBy]: sortOrder })
            .skip(skip)
            .limit(limit);

        const total = await File.countDocuments(query);

        res.json({
            files,
            currentPage: page,
            totalPages: Math.ceil(total / limit),
            totalFiles: total
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get single file by ID
app.get('/api/files/:id', async (req, res) => {
    try {
        const file = await File.findById(req.params.id);
        if (!file) {
            return res.status(404).json({ error: 'File not found' });
        }
        res.json(file);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Download file
app.get('/api/download/:id', async (req, res) => {
    try {
        const file = await File.findById(req.params.id);
        if (!file) {
            return res.status(404).json({ error: 'File not found' });
        }
        
        // Update download count or add analytics here if needed
        res.download(file.path, file.originalName);
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

        // Delete main file and thumbnail if exists
        const filesToDelete = [file.path];
        if (file.metadata.thumbnailPath) {
            filesToDelete.push(file.metadata.thumbnailPath);
        }

        await Promise.all(filesToDelete.map(filePath => 
            new Promise((resolve, reject) => {
                fs.unlink(filePath, (err) => {
                    if (err && err.code !== 'ENOENT') reject(err);
                    resolve();
                });
            })
        ));

        await File.findByIdAndDelete(req.params.id);
        res.json({ message: 'File deleted successfully' });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Search files with advanced filtering
app.get('/api/search', async (req, res) => {
    try {
        const { q, type, startDate, endDate, minSize, maxSize, tags } = req.query;
        
        let query = {};
        
        if (q) {
            query.$or = [
                { originalName: new RegExp(q, 'i') },
                { uploadedBy: new RegExp(q, 'i') }
            ];
        }
        
        if (type) {
            query['metadata.fileType'] = type;
        }
        
        if (startDate || endDate) {
            query.uploadDate = {};
            if (startDate) query.uploadDate.$gte = new Date(startDate);
            if (endDate) query.uploadDate.$lte = new Date(endDate);
        }
        
        if (minSize || maxSize) {
            query.size = {};
            if (minSize) query.size.$gte = parseInt(minSize);
            if (maxSize) query.size.$lte = parseInt(maxSize);
        }
        
        if (tags) {
            query.tags = { $all: tags.split(',') };
        }

        const files = await File.find(query).sort({ uploadDate: -1 });
        res.json(files);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Update file metadata
app.patch('/api/files/:id', async (req, res) => {
    try {
        const updates = {};
        const allowedUpdates = ['tags', 'isPublic'];
        
        Object.keys(req.body).forEach(key => {
            if (allowedUpdates.includes(key)) {
                updates[key] = req.body[key];
            }
        });

        const file = await File.findByIdAndUpdate(
            req.params.id,
            { $set: updates },
            { new: true }
        );

        if (!file) {
            return res.status(404).json({ error: 'File not found' });
        }

        res.json(file);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Get file statistics
app.get('/api/stats', async (req, res) => {
    try {
        const stats = await File.aggregate([
            {
                $group: {
                    _id: null,
                    totalFiles: { $sum: 1 },
                    totalSize: { $sum: '$size' },
                    avgSize: { $avg: '$size' },
                    fileTypes: { $addToSet: '$metadata.fileType' }
                }
            }
        ]);

        const typeStats = await File.aggregate([
            {
                $group: {
                    _id: '$metadata.fileType',
                    count: { $sum: 1 },
                    totalSize: { $sum: '$size' }
                }
            }
        ]);

        res.json({
            overall: stats[0],
            byType: typeStats
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something broke!' });
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});