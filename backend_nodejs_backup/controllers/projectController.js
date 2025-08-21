// backend/controllers/projectController.js
const Project = require('../models/Project');
const OpenAIService = require('../services/openaiService');
const FileService = require('../services/fileService');
const { validateProject } = require('../middleware/validation');

class ProjectController {
  // GET /api/projects - Get all projects for user
  async getAllProjects(req, res) {
    try {
      const projects = await Project.find({ createdBy: req.user.id })
        .select('-files.content') // Exclude file content for performance
        .sort({ updatedAt: -1 });

      res.json({
        success: true,
        data: projects,
        total: projects.length
      });
    } catch (error) {
      console.error('Error fetching projects:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch projects'
      });
    }
  }

  // POST /api/projects - Create new project
  async createProject(req, res) {
    try {
      const { title, description } = req.body;
      const files = req.files;

      // Validation
      const { error } = validateProject({ title, description });
      if (error) {
        return res.status(400).json({
          success: false,
          error: error.details[0].message
        });
      }

      if (!files || files.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'At least one file is required'
        });
      }

      // Process uploaded files
      const processedFiles = await Promise.all(
        files.map(async (file) => {
          const content = await FileService.readFileContent(file.path);
          return {
            originalName: file.originalname,
            fileName: file.filename,
            path: file.path,
            size: file.size,
            mimeType: file.mimetype,
            content: content
          };
        })
      );

      // Create project
      const project = new Project({
        title: title.trim(),
        description: description?.trim() || '',
        files: processedFiles,
        createdBy: req.user.id,
        status: 'processing'
      });

      await project.save();

      // Start documentation generation in background
      this.generateDocumentationAsync(project._id);

      // Return project without file content
      const projectResponse = await Project.findById(project._id)
        .select('-files.content')
        .populate('createdBy', 'name email');

      res.status(201).json({
        success: true,
        data: projectResponse,
        message: 'Project created successfully. Documentation generation started.'
      });

    } catch (error) {
      console.error('Error creating project:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to create project'
      });
    }
  }

  // GET /api/projects/:id - Get specific project
  async getProject(req, res) {
    try {
      const project = await Project.findOne({
        _id: req.params.id,
        createdBy: req.user.id
      }).populate('createdBy', 'name email');

      if (!project) {
        return res.status(404).json({
          success: false,
          error: 'Project not found'
        });
      }

      res.json({
        success: true,
        data: project
      });
    } catch (error) {
      console.error('Error fetching project:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch project'
      });
    }
  }

  // PUT /api/projects/:id - Update project
  async updateProject(req, res) {
    try {
      const { title, description, tags, isPublic } = req.body;

      const project = await Project.findOneAndUpdate(
        { _id: req.params.id, createdBy: req.user.id },
        {
          $set: {
            title: title?.trim(),
            description: description?.trim(),
            tags,
            isPublic,
            updatedAt: new Date()
          }
        },
        { new: true, runValidators: true }
      ).select('-files.content');

      if (!project) {
        return res.status(404).json({
          success: false,
          error: 'Project not found'
        });
      }

      res.json({
        success: true,
        data: project,
        message: 'Project updated successfully'
      });
    } catch (error) {
      console.error('Error updating project:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to update project'
      });
    }
  }

  // DELETE /api/projects/:id - Delete project
  async deleteProject(req, res) {
    try {
      const project = await Project.findOneAndDelete({
        _id: req.params.id,
        createdBy: req.user.id
      });

      if (!project) {
        return res.status(404).json({
          success: false,
          error: 'Project not found'
        });
      }

      // Clean up uploaded files
      await FileService.cleanupProjectFiles(project.files);

      res.json({
        success: true,
        message: 'Project deleted successfully'
      });
    } catch (error) {
      console.error('Error deleting project:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to delete project'
      });
    }
  }

  // POST /api/projects/:id/regenerate - Regenerate documentation
  async regenerateDocumentation(req, res) {
    try {
      const project = await Project.findOne({
        _id: req.params.id,
        createdBy: req.user.id
      });

      if (!project) {
        return res.status(404).json({
          success: false,
          error: 'Project not found'
        });
      }

      // Reset project status
      project.status = 'processing';
      project.documentation = null;
      project.generationMetadata = null;
      project.updatedAt = new Date();
      await project.save();

      // Start regeneration
      this.generateDocumentationAsync(project._id);

      res.json({
        success: true,
        message: 'Documentation regeneration started'
      });
    } catch (error) {
      console.error('Error regenerating documentation:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to regenerate documentation'
      });
    }
  }

  // Background documentation generation
  async generateDocumentationAsync(projectId) {
    try {
      const project = await Project.findById(projectId);
      if (!project) return;

      console.log(`🤖 Starting documentation generation for project: ${project.title}`);

      // Prepare project data for OpenAI
      const projectData = {
        title: project.title,
        description: project.description,
        files: project.files.map(f => ({
          name: f.originalName,
          size: f.size,
          content: f.content
        }))
      };

      // Generate documentation using OpenAI
      const docResult = await OpenAIService.generateDocumentation(projectData);

      // Update project with generated documentation
      await Project.findByIdAndUpdate(projectId, {
        $set: {
          status: 'completed',
          documentation: docResult.content,
          generationMetadata: {
            model: docResult.model,
            tokensUsed: docResult.tokensUsed,
            generatedAt: new Date(),
            processingTime: docResult.processingTime
          },
          updatedAt: new Date()
        }
      });

      console.log(`✅ Documentation generated successfully for project: ${project.title}`);

    } catch (error) {
      console.error(`❌ Error generating documentation for project ${projectId}:`, error);

      // Update project with error status
      await Project.findByIdAndUpdate(projectId, {
        $set: {
          status: 'error',
          error: error.message,
          updatedAt: new Date()
        }
      });
    }
  }

  // GET /api/projects/stats - Get project statistics
  async getProjectStats(req, res) {
    try {
      const stats = await Project.aggregate([
        { $match: { createdBy: req.user.id } },
        {
          $group: {
            _id: null,
            total: { $sum: 1 },
            completed: {
              $sum: { $cond: [{ $eq: ['$status', 'completed'] }, 1, 0] }
            },
            processing: {
              $sum: { $cond: [{ $eq: ['$status', 'processing'] }, 1, 0] }
            },
            error: {
              $sum: { $cond: [{ $eq: ['$status', 'error'] }, 1, 0] }
            },
            totalFiles: { $sum: { $size: '$files' } },
            avgTokensUsed: { $avg: '$generationMetadata.tokensUsed' }
          }
        }
      ]);

      const result = stats[0] || {
        total: 0,
        completed: 0,
        processing: 0,
        error: 0,
        totalFiles: 0,
        avgTokensUsed: 0
      };

      res.json({
        success: true,
        data: result
      });
    } catch (error) {
      console.error('Error fetching project stats:', error);
      res.status(500).json({
        success: false,
        error: 'Failed to fetch project statistics'
      });
    }
  }
}

module.exports = new ProjectController();