const express = require('express');
const router = express.Router();
const projectController = require('../controllers/projectController');
const auth = require('../middleware/auth');
const multer = require('multer');

const upload = multer({
  dest: 'uploads/',
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.html', '.css', '.scss', '.json', '.xml', '.yaml', '.yml', '.md', '.txt', '.sql'];
    const ext = require('path').extname(file.originalname).toLowerCase();
    cb(null, allowedTypes.includes(ext));
  }
});

router.get('/', auth, projectController.getAllProjects);
router.post('/', auth, upload.array('files'), projectController.createProject);
router.get('/stats', auth, projectController.getProjectStats);
router.get('/:id', auth, projectController.getProject);
router.put('/:id', auth, projectController.updateProject);
router.delete('/:id', auth, projectController.deleteProject);
router.post('/:id/regenerate', auth, projectController.regenerateDocumentation);

module.exports = router;