// backend/routes/files.js
const express = require('express');
const router = express.Router();

// Placeholder for file routes
router.get('/health', (req, res) => {
  res.json({ status: 'File routes OK' });
});

module.exports = router;