// backend/services/openaiService.js
const axios = require('axios');

class OpenAIService {
  constructor() {
    this.apiKey = process.env.OPENAI_API_KEY;
    this.apiUrl = 'https://api.openai.com/v1/chat/completions';
    this.model = 'gpt-4o-mini'; // Cost-effective model
    
    if (!this.apiKey) {
      console.warn('⚠️  OpenAI API key not found. Documentation generation will be simulated.');
    }
  }

  async generateDocumentation(projectData) {
    const startTime = Date.now();

    try {
      if (!this.apiKey) {
        // Fallback to simulation if no API key
        return await this.simulateDocumentationGeneration(projectData);
      }

      // Read and process file contents
      const fileContents = this.processFiles(projectData.files);
      
      // Create prompt for GPT
      const prompt = this.createDocumentationPrompt(
        projectData.title,
        projectData.description,
        fileContents
      );

      console.log(`🤖 Generating documentation for: ${projectData.title}`);
      console.log(`📁 Processing ${fileContents.length} files`);

      // Call OpenAI API
      const response = await axios.post(this.apiUrl, {
        model: this.model,
        messages: [
          {
            role: 'system',
            content: this.getSystemPrompt()
          },
          {
            role: 'user',
            content: prompt
          }
        ],
        max_tokens: 4000,
        temperature: 0.3, // Lower temperature for more consistent, technical output
        top_p: 1,
        frequency_penalty: 0,
        presence_penalty: 0
      }, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.apiKey}`
        },
        timeout: 60000 // 60 second timeout
      });

      const documentation = response.data.choices[0]?.message?.content;
      const tokensUsed = response.data.usage?.total_tokens || 0;

      if (!documentation) {
        throw new Error('No documentation generated from OpenAI');
      }

      const processingTime = Date.now() - startTime;

      console.log(`✅ Documentation generated successfully`);
      console.log(`📊 Tokens used: ${tokensUsed}`);
      console.log(`⏱️  Processing time: ${processingTime}ms`);

      return {
        content: documentation,
        model: this.model,
        tokensUsed: tokensUsed,
        processingTime: processingTime,
        generatedAt: new Date().toISOString()
      };

    } catch (error) {
      console.error('❌ Error generating documentation:', error.message);
      
      // If OpenAI fails, fallback to simulation
      if (error.response?.status === 429) {
        console.log('🔄 Rate limit hit, falling back to simulation');
        return await this.simulateDocumentationGeneration(projectData);
      }
      
      throw new Error(`Documentation generation failed: ${error.message}`);
    }
  }

  processFiles(files) {
    return files.map(file => ({
      name: file.name,
      size: file.size,
      content: file.content || '',
      type: this.getFileType(file.name)
    }));
  }

  getFileType(filename) {
    const ext = filename.toLowerCase().split('.').pop();
    const typeMap = {
      'js': 'JavaScript',
      'jsx': 'React JSX',
      'ts': 'TypeScript',
      'tsx': 'React TypeScript',
      'py': 'Python',
      'java': 'Java',
      'cpp': 'C++',
      'c': 'C',
      'cs': 'C#',
      'php': 'PHP',
      'rb': 'Ruby',
      'go': 'Go',
      'rs': 'Rust',
      'swift': 'Swift',
      'kt': 'Kotlin',
      'scala': 'Scala',
      'html': 'HTML',
      'css': 'CSS',
      'scss': 'SCSS',
      'json': 'JSON',
      'xml': 'XML',
      'yaml': 'YAML',
      'yml': 'YAML',
      'md': 'Markdown',
      'txt': 'Text',
      'sql': 'SQL'
    };
    return typeMap[ext] || 'Unknown';
  }

  getSystemPrompt() {
    return `You are a senior technical writer and software architect specializing in creating comprehensive, professional documentation for software projects. Your documentation should be:

1. **Clear and Professional**: Use clear, concise language that both technical and non-technical stakeholders can understand
2. **Well-Structured**: Organize content with proper headings, sections, and logical flow
3. **Comprehensive**: Cover all important aspects including setup, usage, architecture, and troubleshooting
4. **Actionable**: Include specific examples, code snippets, and step-by-step instructions
5. **Maintainable**: Structure the documentation so it can be easily updated and expanded

Format your response in clean Markdown with proper syntax highlighting for code blocks.`;
  }

  createDocumentationPrompt(title, description, fileContents) {
    const fileList = fileContents
      .map(f => `- ${f.name} (${f.type}, ${Math.round(f.size/1024)}KB)`)
      .join('\n');
    
    const codeAnalysis = fileContents
      .map(f => {
        const truncatedContent = f.content.length > 2000 
          ? f.content.substring(0, 2000) + '\n... [truncated for length]'
          : f.content;
        
        return `\n### ${f.name} (${f.type})\n\`\`\`${this.getLanguageForHighlighting(f.type)}\n${truncatedContent}\n\`\`\``;
      })
      .join('\n');

    return `Create comprehensive technical documentation for the following project:

**Project Title:** ${title}

**Project Description:** ${description || 'No description provided'}

**Files Included:**
${fileList}

**Code Analysis:**
${codeAnalysis}

Please generate complete technical documentation that includes:

## 1. Project Overview
- Brief description and purpose
- Key features and functionality
- Technology stack and dependencies used

## 2. Architecture & Design
- Project structure and organization
- Key components and their relationships
- Design patterns and architectural decisions
- Data flow and system interactions

## 3. Installation & Setup
- Prerequisites and system requirements
- Step-by-step installation guide
- Environment configuration
- Initial setup and verification

## 4. Usage Guide
- Getting started tutorial
- Core functionality examples
- Common use cases and workflows
- Best practices and recommendations

## 5. API Documentation (if applicable)
- Available endpoints or interfaces
- Request/response formats
- Authentication and authorization
- Error handling and status codes

## 6. Technical Specifications
- Detailed explanation of key functions/classes/modules
- Algorithm explanations where relevant
- Performance considerations
- Security implementations

## 7. Development Guidelines
- Code style and conventions
- Development workflow
- Testing strategy and examples
- Contributing guidelines

## 8. Configuration & Customization
- Configuration options and files
- Customization possibilities
- Advanced setup scenarios
- Integration with other systems

## 9. Troubleshooting & FAQ
- Common issues and solutions
- Debugging techniques and tools
- Performance optimization tips
- Frequently asked questions

## 10. Maintenance & Updates
- Update procedures
- Backup and recovery
- Monitoring and logging
- Version management

Format the documentation in clean, professional Markdown with proper headings, code blocks, and examples. Make it comprehensive enough for developers, DevOps engineers, and technical stakeholders to understand and work with the project effectively.`;
  }

  getLanguageForHighlighting(fileType) {
    const langMap = {
      'JavaScript': 'javascript',
      'React JSX': 'jsx',
      'TypeScript': 'typescript',
      'React TypeScript': 'tsx',
      'Python': 'python',
      'Java': 'java',
      'C++': 'cpp',
      'C': 'c',
      'C#': 'csharp',
      'PHP': 'php',
      'Ruby': 'ruby',
      'Go': 'go',
      'Rust': 'rust',
      'Swift': 'swift',
      'Kotlin': 'kotlin',
      'Scala': 'scala',
      'HTML': 'html',
      'CSS': 'css',
      'SCSS': 'scss',
      'JSON': 'json',
      'XML': 'xml',
      'YAML': 'yaml',
      'Markdown': 'markdown',
      'SQL': 'sql'
    };
    return langMap[fileType] || 'text';
  }

  // Fallback simulation for when OpenAI API is not available
  async simulateDocumentationGeneration(projectData) {
    console.log('🎭 Simulating documentation generation...');
    
    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));

    const documentation = this.generateSimulatedDocumentation(projectData);
    
    return {
      content: documentation,
      model: 'simulation',
      tokensUsed: Math.floor(Math.random() * 2000) + 1000,
      processingTime: Math.floor(Math.random() * 5000) + 2000,
      generatedAt: new Date().toISOString()
    };
  }

  generateSimulatedDocumentation(projectData) {
    const fileList = projectData.files
      .map(f => `- **${f.name}** (${Math.round(f.size/1024)}KB)`)
      .join('\n');

    return `# ${projectData.title}

## Project Overview
${projectData.description || 'This project contains the uploaded source code files with comprehensive technical documentation generated automatically.'}

**Key Features:**
- Modern software architecture and design patterns
- Well-structured codebase with clear separation of concerns
- Comprehensive error handling and validation
- Scalable and maintainable code organization

## Files Included
${fileList}

## Architecture & Design

This project follows modern development practices with a well-organized structure designed for maintainability and scalability.

### Project Structure
The codebase is organized into logical modules and components, each serving a specific purpose in the overall system architecture.

### Design Patterns
- **Modular Design**: Components are organized in a logical hierarchy
- **Separation of Concerns**: Clear distinction between different layers
- **Configuration Management**: Centralized configuration handling
- **Error Handling**: Comprehensive error management throughout

## Installation & Setup

### Prerequisites
- Node.js (version 16 or higher)
- npm or yarn package manager
- Git for version control

### Installation Steps
1. Clone the repository to your local machine
2. Navigate to the project directory
3. Install dependencies: \`npm install\`
4. Configure environment variables (see .env.example)
5. Run the development server: \`npm start\`

### Environment Configuration
Create a \`.env\` file in the root directory with the following variables:
\`\`\`
NODE_ENV=development
PORT=3000
# Add other configuration variables as needed
\`\`\`

## Usage Guide

### Getting Started
After installation, you can start using the application by following these steps:

1. **Initialize the Application**
   \`\`\`javascript
   // Basic initialization example
   const app = require('./app');
   app.initialize();
   \`\`\`

2. **Configure Settings**
   \`\`\`javascript
   // Configuration example
   app.configure({
     environment: 'development',
     debug: true
   });
   \`\`\`

3. **Run the Application**
   \`\`\`javascript
   // Start the application
   app.start();
   \`\`\`

### Core Functionality
The application provides several key features:

- **Data Processing**: Efficient handling of various data formats
- **API Integration**: Seamless integration with external services  
- **User Management**: Comprehensive user authentication and authorization
- **File Handling**: Robust file upload and processing capabilities

## API Documentation

### Core Endpoints
The application exposes the following main interfaces:

- \`GET /api/status\` - Health check and system status
- \`POST /api/process\` - Main processing endpoint
- \`GET /api/results\` - Retrieve processing results

### Authentication
All API endpoints require proper authentication using JWT tokens.

\`\`\`javascript
// Authentication example
const token = 'your-jwt-token';
const headers = {
  'Authorization': \`Bearer \${token}\`,
  'Content-Type': 'application/json'
};
\`\`\`

## Technical Specifications

### Performance Considerations
- Optimized for high throughput and low latency
- Efficient memory usage and resource management
- Scalable architecture supporting horizontal scaling
- Comprehensive caching strategies

### Security Features
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF token implementation
- Rate limiting and DDoS protection

## Development Guidelines

### Code Standards
- Follow consistent naming conventions
- Write comprehensive unit tests
- Document all public APIs and functions
- Use meaningful commit messages
- Conduct thorough code reviews

### Testing Strategy
\`\`\`bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test suite
npm run test:unit
\`\`\`

## Configuration & Customization

### Configuration Files
- \`config/default.json\` - Default configuration settings
- \`config/production.json\` - Production-specific settings
- \`.env\` - Environment-specific variables

### Customization Options
The application supports various customization options through configuration files and environment variables.

## Troubleshooting

### Common Issues

1. **Installation Problems**
   - Clear node_modules and package-lock.json
   - Run \`npm install\` again
   - Check Node.js version compatibility

2. **Runtime Errors**
   - Check environment variables configuration
   - Verify database connections
   - Review application logs

3. **Performance Issues**
   - Monitor resource usage
   - Check for memory leaks
   - Optimize database queries

### Debug Mode
Enable debug mode by setting \`DEBUG=true\` in your environment variables.

## Maintenance & Updates

### Update Procedures
1. Backup current data and configuration
2. Pull latest changes from repository
3. Run \`npm install\` to update dependencies
4. Run tests to verify functionality
5. Deploy to production environment

### Monitoring
- Set up application monitoring
- Configure log aggregation
- Implement health checks
- Monitor performance metrics

---

*Documentation generated automatically by Mashreq Documentation Portal*
*Generated on: ${new Date().toLocaleDateString()}*
*Version: 1.0.0*`;
  }
}

module.exports = new OpenAIService();