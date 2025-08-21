const fs = require('fs').promises;
const path = require('path');

class FileService {
  async readFileContent(filePath) {
    try {
      return await fs.readFile(filePath, 'utf8');
    } catch (error) {
      console.error('Error reading file:', error);
      return '';
    }
  }

  async cleanupProjectFiles(files) {
    for (const file of files) {
      try {
        await fs.unlink(file.path);
      } catch (error) {
        console.error('Error deleting file:', file.path, error);
      }
    }
  }
}

module.exports = new FileService();