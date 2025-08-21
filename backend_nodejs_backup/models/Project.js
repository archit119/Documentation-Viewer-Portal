// backend/models/Project.js
const mongoose = require('mongoose');

const fileSchema = new mongoose.Schema({
  originalName: {
    type: String,
    required: true,
    trim: true
  },
  fileName: {
    type: String,
    required: true
  },
  path: {
    type: String,
    required: true
  },
  size: {
    type: Number,
    required: true,
    min: 0
  },
  mimeType: {
    type: String,
    required: true
  },
  content: {
    type: String,
    default: ''
  },
  uploadedAt: {
    type: Date,
    default: Date.now
  }
});

const generationMetadataSchema = new mongoose.Schema({
  model: {
    type: String,
    default: 'gpt-4o-mini'
  },
  tokensUsed: {
    type: Number,
    min: 0
  },
  generatedAt: {
    type: Date,
    default: Date.now
  },
  processingTime: {
    type: Number, // in milliseconds
    min: 0
  },
  retryCount: {
    type: Number,
    default: 0,
    min: 0
  }
});

const projectSchema = new mongoose.Schema({
  title: {
    type: String,
    required: [true, 'Project title is required'],
    trim: true,
    minlength: [2, 'Title must be at least 2 characters long'],
    maxlength: [200, 'Title cannot exceed 200 characters']
  },
  description: {
    type: String,
    trim: true,
    maxlength: [2000, 'Description cannot exceed 2000 characters'],
    default: ''
  },
  status: {
    type: String,
    enum: {
      values: ['processing', 'completed', 'error'],
      message: 'Status must be processing, completed, or error'
    },
    default: 'processing'
  },
  files: {
    type: [fileSchema],
    validate: {
      validator: function(files) {
        return files && files.length > 0;
      },
      message: 'At least one file is required'
    }
  },
  documentation: {
    type: String,
    default: null
  },
  generationMetadata: {
    type: generationMetadataSchema,
    default: null
  },
  createdBy: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: [true, 'Created by user is required']
  },
  tags: [{
    type: String,
    trim: true,
    maxlength: [50, 'Tag cannot exceed 50 characters']
  }],
  isPublic: {
    type: Boolean,
    default: false
  },
  version: {
    type: String,
    default: '1.0.0'
  },
  error: {
    type: String,
    default: null
  },
  progress: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  statusMessage: {
    type: String,
    default: null
  }
}, {
  timestamps: true, // Automatically adds createdAt and updatedAt
  toJSON: {
    transform: function(doc, ret) {
      // Remove sensitive data when converting to JSON
      delete ret.__v;
      return ret;
    }
  }
});

// Indexes for better query performance
projectSchema.index({ createdBy: 1, createdAt: -1 });
projectSchema.index({ status: 1 });
projectSchema.index({ title: 'text', description: 'text' });
projectSchema.index({ tags: 1 });

// Virtual for file count
projectSchema.virtual('fileCount').get(function() {
  return this.files ? this.files.length : 0;
});

// Virtual for total file size
projectSchema.virtual('totalSize').get(function() {
  if (!this.files) return 0;
  return this.files.reduce((total, file) => total + file.size, 0);
});

// Pre-save middleware
projectSchema.pre('save', function(next) {
  // Update the updatedAt field manually if needed
  if (this.isModified() && !this.isNew) {
    this.updatedAt = new Date();
  }
  next();
});

// Static methods
projectSchema.statics.getProjectStats = async function(userId) {
  return await this.aggregate([
    { $match: { createdBy: mongoose.Types.ObjectId(userId) } },
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
};

// Instance methods
projectSchema.methods.updateProgress = function(progress, statusMessage) {
  this.progress = progress;
  this.statusMessage = statusMessage;
  this.updatedAt = new Date();
  return this.save();
};

projectSchema.methods.markAsCompleted = function(documentation, metadata) {
  this.status = 'completed';
  this.documentation = documentation;
  this.generationMetadata = metadata;
  this.progress = 100;
  this.statusMessage = 'Documentation generated successfully';
  this.error = null;
  this.updatedAt = new Date();
  return this.save();
};

projectSchema.methods.markAsError = function(errorMessage) {
  this.status = 'error';
  this.error = errorMessage;
  this.progress = 0;
  this.statusMessage = 'Documentation generation failed';
  this.updatedAt = new Date();
  return this.save();
};

// Export the model
module.exports = mongoose.model('Project', projectSchema)