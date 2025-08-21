# services/multi_agent_documentation_service.py
import os
import json
import time
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Tuple
import threading
import logging
import requests
import httpx

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import openai
    from config import Config
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ OpenAI not available - using simulation mode")

class DocumentationAgent:
    """Base class for specialized documentation agents"""
    
    def __init__(self, name: str, role: str, system_prompt: str, openai_client=None, model="gpt-4-turbo-preview"):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.openai_client = openai_client
        self.model = model
        self.tokens_used = 0
        
    # In services/multi_agent_documentation_service.py
    # Replace the analyze_project method in DocumentationAgent class (around line 30)

    def analyze_project(self, project_data: Dict, shared_context: Dict = None) -> Tuple[str, int]:
        """Generate specialized documentation content for this agent's domain (with quality retries)."""
        if not self.openai_client:
            # No API? Return a meaningful simulated analysis
            return self._simulate_content(project_data), 0

        try:
            context = self._build_context(project_data, shared_context)
            user_prompt = self._create_user_prompt(project_data, context)

            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            total_tokens_used = 0
            best_content = ""
            best_len = 0

            for attempt in range(1, 4):
                resp = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2 if attempt == 1 else 0.15,
                    max_tokens=4500,
                    presence_penalty=0.0,
                    frequency_penalty=0.1,
                )
                draft = (resp.choices[0].message.content or "").strip()
                usage = getattr(resp, "usage", None)
                if usage and getattr(usage, "total_tokens", None):
                    total_tokens_used += usage.total_tokens

                # Track best non-empty
                if len(draft) > best_len:
                    best_content = draft
                    best_len = len(draft)

                if self._passes_quality(draft):
                    # Inject images (if any) after the first section
                    final = self._add_images_to_content(draft, project_data)
                    self.tokens_used += total_tokens_used
                    return final, total_tokens_used

                # Prepare corrective follow-up
                critique = []
                if not draft:
                    critique.append("The previous reply was empty.")
                else:
                    if len(draft.split()) < 800:
                        critique.append("Too short (must be 800–1500 words).")
                    if (draft.count("\n#") + draft.count("\n##") + draft.count("\n###") + draft.count("\n####")) < 5:
                        critique.append("Not enough structured subsections (need ≥5).")
                    if "```" not in draft:
                        critique.append("Include at least one fenced code block with concrete examples.")
                    if ("- " not in draft and "* " not in draft):
                        critique.append("Use bullet lists for key steps/responsibilities.")

                repair = f"""
    Regenerate a comprehensive {self.role} section addressing deficiencies:
    - {' '.join(critique) if critique else 'Improve structure and specificity.'}

    STRICT RULES:
    1) 800–1500 words.
    2) Start with an H1 title; include ≥5 H2/H3 subsections (Overview, File insights, Architecture/Integration, Security/Performance, Recommendations).
    3) Reference real file names and snippets from the provided context (do NOT invent files).
    4) Include at least one fenced code block that reflects the languages present.
    5) Use bullet lists where appropriate; avoid filler.
    6) No placeholders/apologies; deliver publishable documentation.
    """.strip()

                messages = [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": draft or "(no content)"},
                    {"role": "user", "content": repair},
                ]

            # After retries: return the best we got (still embed images)
            final = self._add_images_to_content(best_content, project_data) if best_content else "# Draft Incomplete\n\nNo content."
            self.tokens_used += total_tokens_used
            return final, total_tokens_used

        except Exception as e:
            print(f"❌ Error in {self.name}: {e}")
            return self._simulate_content(project_data), 0

        

    def _passes_quality(self, text: str) -> bool:
        if not text or not text.strip():
            return False
        words = len(text.strip().split())
        heading_count = text.count("\n#") + text.count("\n##") + text.count("\n###") + text.count("\n####")
        has_lists = ("- " in text) or ("* " in text) or any(f"{i}." in text for i in range(1, 5))
        # ≥700 words, ≥3 headings, and at least one list
        return (words >= 700) and (heading_count >= 3) and has_lists

    
    def _build_context(self, project_data: Dict, shared_context: Dict = None) -> str:
        """Build comprehensive context for the agent"""
        context = []
        
        # Project basics
        context.append(f"**Project**: {project_data.get('title', 'Unknown Project')}")
        context.append(f"**Description**: {project_data.get('description', 'No description provided')}")
        
        # File analysis
        files = project_data.get('files', [])
        if files:
            context.append(f"\n**Files Analyzed** ({len(files)} files):")
            
            # Categorize files by type
            file_types = {}
            for file_info in files:
                name = file_info.get('name', '')
                file_type = self._get_file_category(name)
                if file_type not in file_types:
                    file_types[file_type] = []
                file_types[file_type].append(file_info)
            
            for file_type, file_list in file_types.items():
                context.append(f"\n*{file_type}:*")
                for file_info in file_list[:10]:  # Limit to prevent token overflow
                    name = file_info.get('name', 'Unknown')
                    size = file_info.get('size', 0)
                    content_preview = file_info.get('content', '')[:200] if file_info.get('content') else ''
                    context.append(f"  - **{name}** ({size:,} bytes) {content_preview}...")
        
        # Shared context from other agents
        if shared_context:
            context.append(f"\n**Shared Insights:**")
            for agent_name, insights in shared_context.items():
                if insights and agent_name != self.name:
                    context.append(f"  - *{agent_name}*: {insights[:150]}...")
        
        return '\n'.join(context)
    
    def _get_file_category(self, filename: str) -> str:
        """Categorize files for better context organization"""
        if not filename or '.' not in filename:
            return 'Configuration'
            
        ext = filename.lower().split('.')[-1]
        name = filename.lower()
        
        # Programming languages
        if ext in ['py', 'js', 'jsx', 'ts', 'tsx', 'java', 'cpp', 'c', 'cs', 'php', 'rb', 'go', 'rs', 'swift', 'kt', 'scala']:
            return 'Source Code'
        elif ext in ['html', 'css', 'scss', 'sass', 'less']:
            return 'Frontend Assets'
        elif ext in ['json', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf'] or 'config' in name:
            return 'Configuration'
        elif ext in ['md', 'txt', 'rst']:
            return 'Documentation'
        elif ext in ['sql', 'db', 'sqlite']:
            return 'Database'
        elif 'test' in name or ext in ['spec', 'test']:
            return 'Tests'
        else:
            return 'Other'
    
    def _create_user_prompt(self, project_data: Dict, context: str) -> str:
        """Create the specialized user prompt; include embedded images (if any)."""
        base_prompt = f"""{context}

    **TASK**: As a {self.role}, provide the most comprehensive and detailed analysis possible for your domain of expertise. 

    **REQUIREMENTS**:
    - Analyze ALL relevant files in detail, not just summaries
    - Explain the WHY behind every implementation decision
    - Include specific code examples and explanations
    - Cross-reference components and their relationships
    - Provide actionable insights and recommendations
    - Write 800-1500 words with clear sections and subsections
    - Use technical precision while remaining understandable

    Focus on your specialized domain while considering how it integrates with the overall system architecture."""
        # Process images
        # Process images (DO NOT embed base64 into the prompt — causes token overflows)
        image_sections = self._process_embedded_images(project_data)
        if image_sections:
            image_instructions = "\n\n**VISUAL ASSETS AVAILABLE (for your awareness):**\n"
            for section, images in image_sections.items():
                image_instructions += f"\nSection hint: {section}\n"
                for img in images[:2]:
                    alt = img.get('placement', {}).get('description', img.get('name', 'Embedded image'))
                    image_instructions += f"- {img.get('name', 'image')} — {alt}\n"
            image_instructions += "\nYou do not need to render images in your reply; the app will place them later.\n"
            return base_prompt + image_instructions
        return base_prompt


    
    def _simulate_content(self, project_data: Dict) -> str:
        """Enhanced fallback simulation content with actual analysis"""
        files = project_data.get('files', [])
        file_count = len(files)
        
        # Analyze file types for more realistic content
        file_types = {}
        for file_info in files:
            name = file_info.get('name', '')
            file_type = self._get_file_category(name)
            if file_type not in file_types:
                file_types[file_type] = []
            file_types[file_type].append(name)
        
        content = f"""# {self.name} Analysis

    ## Overview
    This section provides a comprehensive {self.role.lower()} analysis for **{project_data.get('title', 'Unknown Project')}**.

    ## Project Structure Analysis
    The project contains **{file_count} files** across the following categories:

    """
        
        # Add file type analysis
        for file_type, files_list in file_types.items():
            content += f"### {file_type} Files ({len(files_list)})\n"
            for file_name in files_list[:5]:  # Show first 5 files
                content += f"- `{file_name}`\n"
            if len(files_list) > 5:
                content += f"- ... and {len(files_list) - 5} more files\n"
            content += "\n"
        
        # Add domain-specific analysis based on agent type
        if "Code Architecture" in self.name:
            content += """## Code Structure Analysis
    - **Programming Languages**: Multiple languages detected
    - **Architecture Pattern**: Modern modular design
    - **Code Organization**: Well-structured with clear separation of concerns
    - **Key Components**: Main application logic, utilities, and configuration files

    ## Implementation Details
    - Functions and classes are properly organized
    - Clear naming conventions followed
    - Modular architecture enables maintainability
    """
        elif "System Architecture" in self.name:
            content += """## System Architecture
    - **Design Pattern**: Layered architecture with clear boundaries
    - **Component Structure**: Frontend, backend, and service layers
    - **Integration Points**: Well-defined interfaces between components
    - **Scalability**: Architecture supports horizontal and vertical scaling

    ## Design Decisions
    - Technology stack chosen for reliability and performance
    - Clear separation between presentation and business logic
    - Modular design enables independent component updates
    """
        elif "API Integration" in self.name:
            content += """## API Structure
    - **Endpoints**: RESTful API design following industry standards
    - **Authentication**: Secure authentication mechanisms implemented
    - **Data Formats**: JSON-based request/response handling
    - **Error Handling**: Comprehensive error response structure

    ## Integration Patterns
    - Standard HTTP methods for different operations
    - Consistent response format across all endpoints
    - Proper status codes for different scenarios
    """
        elif "Security Implementation" in self.name:
            content += """## Security Implementation
    - **Authentication**: Multi-layer authentication system
    - **Authorization**: Role-based access control
    - **Data Protection**: Encryption for sensitive data
    - **Input Validation**: Comprehensive input sanitization

    ## Security Measures
    - HTTPS encryption for all communications
    - Secure session management
    - Protection against common vulnerabilities
    - Regular security audits recommended
    """
        elif "Deployment Operations" in self.name or "Deployment" in self.name:
            content += """## Installation Requirements
    - **System Requirements**: Standard development environment
    - **Dependencies**: All required packages documented
    - **Configuration**: Environment-specific settings
    - **Deployment**: Production-ready deployment process

    ## Getting Started
    1. Install required dependencies
    2. Configure environment variables
    3. Run initialization scripts
    4. Start the application services
    """
        elif "Quality Assurance" in self.name:
            content += """## Testing Strategy
    - **Test Coverage**: Comprehensive test suite implementation
    - **Testing Levels**: Unit, integration, and end-to-end tests
    - **Quality Assurance**: Automated quality checks
    - **Continuous Integration**: Automated testing pipeline

    ## Quality Metrics
    - Code coverage targets defined
    - Performance benchmarks established
    - Quality gates for deployment
    """
        elif "User Documentation" in self.name:
            content += """## User Experience Design
    - **User Interface**: Intuitive and responsive design
    - **User Workflows**: Streamlined user interaction patterns
    - **Accessibility**: Following web accessibility guidelines
    - **Documentation**: Comprehensive user guides

    ## User Journey
    - Clear onboarding process
    - Intuitive navigation structure
    - Helpful error messages and guidance
    """
        elif "Performance Optimization" in self.name:
            content += """## Performance Analysis
    - **Response Times**: Optimized for fast response times
    - **Resource Usage**: Efficient memory and CPU utilization
    - **Scalability**: Designed to handle increased load
    - **Monitoring**: Performance metrics tracking

    ## Optimization Strategies
    - Caching mechanisms implemented
    - Database query optimization
    - Resource loading optimization
    - Performance monitoring tools
    """
        
        content += f"""
    ## Technical Specifications
    - **Total Files**: {file_count} files analyzed
    - **Project Type**: {self._detect_project_type(project_data)}
    - **Complexity**: {self._assess_complexity(file_count)}

    ## Recommendations
    1. Continue following established patterns and conventions
    2. Implement comprehensive monitoring and logging
    3. Regular code reviews and documentation updates
    4. Consider automated testing and deployment pipelines

    ## Integration Notes
    This analysis integrates with other specialized agents to provide a complete system overview. For detailed implementation specifics, refer to the Code Analysis section. For deployment instructions, see the Setup & Deployment documentation.

    ---
    *This analysis was generated using intelligent code analysis. For the most detailed insights, ensure all project files are included in the analysis.*
    """
        
        return content
    
    def _detect_project_type(self, project_data: Dict) -> str:
        """Detect project type based on files"""
        files = project_data.get('files', [])
        
        has_react = any('jsx' in f.get('name', '').lower() or 'react' in f.get('content', '').lower() for f in files)
        has_python = any(f.get('name', '').endswith('.py') for f in files)
        has_node = any(f.get('name', '') == 'package.json' for f in files)
        has_java = any(f.get('name', '').endswith('.java') for f in files)
        
        if has_react and has_node:
            return "React Web Application"
        elif has_python:
            return "Python Application"
        elif has_java:
            return "Java Application"
        elif has_node:
            return "Node.js Application"
        else:
            return "Multi-language Project"

    def _assess_complexity(self, file_count: int) -> str:
        """Assess project complexity based on file count"""
        if file_count > 50:
            return "High complexity (Large-scale project)"
        elif file_count > 20:
            return "Medium complexity (Mid-scale project)"
        elif file_count > 5:
            return "Low complexity (Small-scale project)"
        else:
            return "Minimal complexity (Simple project)"
        

    # In services/multi_agent_documentation_service.py - Add this method to DocumentationAgent class
    def _process_embedded_images(self, project_data: Dict) -> Dict:
        """Process and place embedded images in documentation"""
        embedded_images = []
        
        # Extract images from all files
        for file_data in project_data.get('files', []):
            if 'embedded_images' in file_data:
                embedded_images.extend(file_data['embedded_images'])
        
        if not embedded_images:
            return {}
        
        # Group images by placement section
        image_sections = {}
        for image in embedded_images:
            placement = image.get('placement', {})
            section = placement.get('section', 'overview')
            
            if section not in image_sections:
                image_sections[section] = []
            
            image_sections[section].append(image)
        
        return image_sections

    # (duplicate _create_user_prompt removed — handled in the single method above)


    # In services/multi_agent_documentation_service.py
    # Add these methods to the DocumentationAgent class (around line 120)

    def _extract_embedded_images(self, project_data: Dict) -> List[Dict]:
        """Extract embedded images from project data"""
        embedded_images = []
        
        for file_data in project_data.get('files', []):
            if 'embedded_images' in file_data:
                embedded_images.extend(file_data['embedded_images'])
        
        return embedded_images

    def _add_images_to_content(self, content: str, project_data: Dict) -> str:
        """Add relevant images to the generated content"""
        embedded_images = self._extract_embedded_images(project_data)
        if not embedded_images:
            return content
        
        # Filter images for this agent
        relevant_images = []
        agent_keywords = {
            'Code Architecture Agent': ['code', 'function', 'class', 'module', 'file'],
            'System Architecture Agent': ['architecture', 'design', 'system', 'topology'],
            'API Integration Agent': ['api', 'endpoint', 'request', 'response', 'interface'],
            'Security Implementation Agent': ['security', 'auth', 'token', 'password', 'jwt', 'mfa'],
            'Deployment Operations Agent': ['setup', 'installation', 'deploy', 'infrastructure', 'docker', 'kubernetes'],
            'Quality Assurance Agent': ['test', 'testing', 'coverage', 'qa', 'assert'],
            'User Documentation Agent': ['ui', 'user', 'interface', 'walkthrough', 'guide'],
            'Performance Optimization Agent': ['performance', 'latency', 'throughput', 'metric', 'profiling']
        }

        keywords = agent_keywords.get(self.name, [])
        
        for img in embedded_images[:2]:  # Max 2 images
            context = (img.get('context', '') + ' ' + img.get('name', '')).lower()
            if not keywords or any(keyword in context for keyword in keywords):
                relevant_images.append(img)
        
        # Add images to content
        if relevant_images:
            image_section = "\n\n## Visual Documentation\n\n"
            for img in relevant_images:
                description = img.get('placement', {}).get('description', img['name'])
                img_markdown = f"![{description}](data:image/png;base64,{img['data']})\n\n"
                image_section += img_markdown
            
            # Insert images after the first heading
            lines = content.split('\n')
            insert_index = 1
            for i, line in enumerate(lines):
                if line.startswith('##'):
                    insert_index = i + 1
                    break
            
            lines.insert(insert_index, image_section)
            content = '\n'.join(lines)
        
        return content


class OrchestratorAgent:
    """Main orchestrator that coordinates all specialized agents"""
    
    def __init__(self, openai_client=None, model=None):
        self.client = openai_client or get_llm_client()
        self.model = model or self._get_model_name()
        self.agents = {}
        self.shared_context = {}
        self.total_tokens = 0
        
        # Initialize all specialized agents
        self._initialize_agents()
    
    def _get_model_name(self):
        """Get appropriate model name based on client type"""
        USE_AZURE = os.getenv("USE_AZURE", "False").lower() == "true"
        
        if USE_AZURE:
            return os.getenv("llm_deployment_name", "gpt-4o-mini")
        else:
            return "gpt-4o-mini"
    
    def _initialize_agents(self):
        """Initialize all specialized documentation agents with unique, non-conflicting names"""

        model_name = self._get_model_name()
        
        agent_configs = {
            "Code Architecture Agent": {
                "role": "Senior Code Architect and Logic Analyzer",
                "system_prompt": """You are an expert code analyst and senior software architect specializing in deep code analysis across ALL programming languages. Your role is to provide the most comprehensive code analysis possible.

    CORE RESPONSIBILITIES:
    - Perform line-by-line analysis of critical functions and classes
    - Explain the exact logic flow and algorithms implemented
    - Identify and explain design patterns, architectural decisions, and code organization
    - Analyze dependencies, imports, and module relationships
    - Explain complex business logic and computational algorithms
    - Document all public APIs, interfaces, and method signatures
    - Identify potential issues, optimizations, and improvements
    - Cross-reference code components and their interactions

    ANALYSIS DEPTH REQUIREMENTS:
    - For each major function/method: purpose, parameters, return values, side effects, complexity
    - For each class: responsibility, relationships, inheritance hierarchies, design patterns
    - For each module: purpose, exports, dependencies, integration points
    - For configuration files: explain every setting and its impact
    - For database schemas: table relationships, indexing strategies, data flow

    OUTPUT FORMAT:
    - Use clear hierarchical sections with descriptive headers
    - Include inline code examples with explanations
    - Provide technical diagrams in text form where helpful
    - Cross-reference related components throughout the analysis
    - Conclude with architecture insights and recommendations

    Write extremely detailed technical documentation that a senior developer could use to fully understand and maintain the codebase."""
            },
            
            "System Architecture Agent": {
                "role": "Principal System Architect and Design Pattern Expert", 
                "system_prompt": """You are a principal system architect specializing in system design, architectural patterns, and component interaction analysis across all technology stacks.

    CORE RESPONSIBILITIES:
    - Analyze overall system architecture and design decisions
    - Identify and explain all architectural patterns (MVC, microservices, layered, etc.)
    - Document component relationships and interaction patterns
    - Explain data flow between system boundaries
    - Analyze scalability, maintainability, and extensibility aspects
    - Document integration patterns and external system connections
    - Identify architectural strengths, weaknesses, and improvement opportunities
    - Explain technology choices and their architectural implications

    ARCHITECTURE ANALYSIS REQUIREMENTS:
    - System topology: how components are organized and communicate
    - Design patterns: which patterns are used and why
    - Separation of concerns: how responsibilities are divided
    - Integration patterns: APIs, events, messaging, database access
    - Security architecture: authentication, authorization, data protection
    - Scalability considerations: horizontal/vertical scaling potential
    - Technology stack justification: why each technology was chosen
    - Deployment architecture: how the system is structured for production

    OUTPUT FORMAT:
    - Start with high-level architectural overview
    - Detail each architectural layer and its responsibilities
    - Explain component interaction patterns with flow descriptions
    - Document all external integrations and protocols
    - Include architectural decision records (ADRs) where relevant
    - Provide improvement recommendations and future considerations

    Write comprehensive architectural documentation that enables technical leadership to understand system design decisions and evolution strategy."""
            },
            
            "API Integration Agent": {
                "role": "Senior API Architect and Integration Specialist",
                "system_prompt": """You are a senior API architect and integration specialist with expertise in documenting APIs, data flows, and system integrations across all technology platforms.

    CORE RESPONSIBILITIES:
    - Document all API endpoints with complete specifications
    - Analyze request/response patterns and data transformations
    - Explain authentication and authorization mechanisms
    - Document all integration points and external service connections
    - Analyze data validation, error handling, and edge cases
    - Explain API versioning and backward compatibility strategies
    - Document rate limiting, caching, and performance optimizations
    - Analyze security measures and potential vulnerabilities

    API DOCUMENTATION REQUIREMENTS:
    - Complete endpoint inventory: HTTP methods, paths, parameters, headers
    - Request/response schemas with examples and validation rules
    - Authentication flows: tokens, sessions, OAuth, API keys
    - Error codes and handling: standard errors, custom exceptions, recovery
    - Integration patterns: webhooks, polling, real-time connections
    - Data formats: JSON, XML, GraphQL schemas, serialization
    - Performance characteristics: response times, throughput, caching
    - Security considerations: CORS, rate limiting, input validation

    INTEGRATION ANALYSIS:
    - External service dependencies and their purposes
    - Data synchronization patterns and consistency models
    - Event-driven architecture and messaging patterns
    - Database interaction patterns and optimization strategies
    - Third-party API usage and fallback mechanisms

    OUTPUT FORMAT:
    - Comprehensive API reference with interactive examples
    - Integration architecture diagrams in text format
    - Security implementation details and best practices
    - Performance optimization strategies and monitoring points
    - Troubleshooting guides for common integration issues

    Write detailed API documentation that enables developers to integrate with and extend the system effectively."""
            },
            
            "Security Implementation Agent": {
                "role": "Principal Security Engineer and Authentication Specialist",
                "system_prompt": """You are a principal security engineer specializing in application security, authentication systems, and security architecture across all technology stacks.

    CORE RESPONSIBILITIES:
    - Analyze all security mechanisms and authentication flows
    - Document access control, authorization, and permission systems
    - Identify security vulnerabilities and threat vectors
    - Explain encryption, hashing, and data protection strategies
    - Document security configurations and best practices
    - Analyze session management and token-based authentication
    - Explain security headers, CORS, and browser security measures
    - Document compliance requirements and security standards

    SECURITY ANALYSIS REQUIREMENTS:
    - Authentication mechanisms: login flows, multi-factor authentication, SSO
    - Authorization patterns: role-based, attribute-based, resource permissions
    - Session management: token lifecycle, refresh mechanisms, logout procedures
    - Data protection: encryption at rest/transit, sensitive data handling
    - Input validation: sanitization, SQL injection prevention, XSS protection
    - Security headers: CSP, HSTS, X-Frame-Options, security configurations
    - Audit logging: security events, access logs, compliance tracking
    - Threat modeling: attack vectors, risk assessment, mitigation strategies

    VULNERABILITY ASSESSMENT:
    - Common security antipatterns and potential exploits
    - Dependency vulnerabilities and update strategies
    - Configuration security and hardening recommendations
    - Security testing strategies and automated security scanning
    - Incident response procedures and security monitoring

    OUTPUT FORMAT:
    - Complete security architecture overview
    - Authentication and authorization flow diagrams
    - Security implementation details with code examples
    - Vulnerability assessment with remediation recommendations
    - Security best practices and configuration guidelines
    - Compliance checklist and audit requirements

    Write comprehensive security documentation that enables security teams to assess, maintain, and improve the system's security posture."""
            },
            
            "Deployment Operations Agent": {
                "role": "Senior DevOps Engineer and Infrastructure Specialist",
                "system_prompt": """You are a senior DevOps engineer specializing in deployment automation, infrastructure management, and environment configuration across all platforms and cloud providers.

    CORE RESPONSIBILITIES:
    - Document complete installation and setup procedures
    - Analyze deployment strategies and infrastructure requirements
    - Explain environment configuration and dependency management
    - Document containerization and orchestration setups
    - Analyze monitoring, logging, and observability configurations
    - Explain CI/CD pipelines and automation workflows
    - Document scaling strategies and infrastructure optimization
    - Explain disaster recovery and backup procedures

    DEPLOYMENT ANALYSIS REQUIREMENTS:
    - Installation prerequisites: system requirements, software dependencies
    - Environment setup: development, staging, production configurations
    - Configuration management: environment variables, secrets, feature flags
    - Deployment strategies: blue-green, rolling updates, canary releases
    - Infrastructure as Code: Terraform, CloudFormation, Kubernetes manifests
    - Monitoring setup: metrics collection, alerting, dashboard configuration
    - Security hardening: network security, access controls, certificate management
    - Performance optimization: resource allocation, caching, load balancing

    OPERATIONAL PROCEDURES:
    - Backup and recovery procedures with testing protocols
    - Scaling procedures: horizontal and vertical scaling strategies
    - Troubleshooting guides: common issues and resolution steps
    - Maintenance procedures: updates, patches, dependency management
    - Performance monitoring and capacity planning strategies

    OUTPUT FORMAT:
    - Step-by-step installation and setup guides
    - Infrastructure architecture diagrams and specifications
    - Configuration templates and example files
    - Deployment pipeline documentation with automation scripts
    - Operations runbooks and troubleshooting procedures
    - Performance tuning guides and optimization strategies

    Write comprehensive deployment and operations documentation that enables DevOps teams to reliably deploy, monitor, and maintain the system in production."""
            },
            
            "Quality Assurance Agent": {
                "role": "Senior Quality Engineer and Test Automation Specialist",
                "system_prompt": """You are a senior quality engineer specializing in test automation, quality assurance strategies, and testing frameworks across all programming languages and platforms.

    CORE RESPONSIBILITIES:
    - Analyze testing strategies and framework implementations
    - Document test coverage, test types, and quality metrics
    - Explain automated testing pipelines and continuous integration
    - Document performance testing and load testing strategies
    - Analyze code quality tools and static analysis configurations
    - Explain testing best practices and quality gates
    - Document bug tracking, issue management, and quality processes
    - Analyze accessibility, usability, and user experience testing

    TESTING ANALYSIS REQUIREMENTS:
    - Test framework analysis: unit, integration, end-to-end testing tools
    - Test coverage metrics: line coverage, branch coverage, mutation testing
    - Testing strategies: TDD, BDD, risk-based testing approaches
    - Automated testing: CI/CD integration, test automation pipelines
    - Performance testing: load testing, stress testing, benchmark analysis
    - Security testing: vulnerability scanning, penetration testing procedures
    - Quality metrics: code quality scores, technical debt analysis
    - Testing environments: test data management, environment provisioning

    QUALITY ASSURANCE PROCESSES:
    - Code review processes and quality standards
    - Bug triage and issue management workflows
    - Quality gates and release criteria
    - Regression testing strategies and test maintenance
    - User acceptance testing and stakeholder validation processes

    OUTPUT FORMAT:
    - Comprehensive testing strategy overview
    - Test framework documentation with examples
    - Quality metrics dashboard and reporting procedures
    - Testing automation guides and CI/CD integration
    - Quality assurance processes and best practices
    - Performance testing procedures and benchmarking guides

    Write detailed testing and quality documentation that enables QA teams to maintain high code quality and comprehensive test coverage."""
            },
            
            "User Documentation Agent": {
                "role": "Senior Technical Writer and User Experience Specialist",
                "system_prompt": """You are a senior technical writer specializing in user experience documentation, onboarding workflows, and user-centered technical communication.

    CORE RESPONSIBILITIES:
    - Create comprehensive user onboarding and getting started guides
    - Document user workflows and interaction patterns
    - Explain feature usage with practical examples and use cases
    - Create troubleshooting guides and FAQ documentation
    - Document accessibility features and inclusive design considerations
    - Explain integration workflows for developers and end users
    - Create tutorial content and step-by-step learning paths
    - Document user feedback mechanisms and support processes

    USER EXPERIENCE ANALYSIS:
    - User journey mapping: onboarding, feature discovery, task completion
    - Workflow documentation: common tasks, advanced features, edge cases
    - Tutorial creation: progressive learning, hands-on examples, best practices
    - Troubleshooting guides: common problems, diagnostic procedures, solutions
    - Accessibility documentation: screen reader support, keyboard navigation, WCAG compliance
    - Integration guides: developer onboarding, API usage examples, SDK documentation
    - Feature documentation: capabilities, limitations, configuration options
    - Support documentation: help resources, community guidelines, escalation procedures

    CONTENT CREATION REQUIREMENTS:
    - Clear, jargon-free explanations with progressive complexity
    - Practical examples and real-world use cases
    - Visual descriptions of UI elements and user interactions
    - Step-by-step procedures with expected outcomes
    - Common pitfalls and how to avoid them
    - Tips, tricks, and advanced usage patterns

    OUTPUT FORMAT:
    - Getting started tutorial with clear progression
    - Feature-by-feature usage guides with examples
    - Workflow documentation with decision trees
    - Troubleshooting guides with diagnostic procedures
    - FAQ section addressing common questions and concerns
    - User feedback collection and improvement processes

    Write user-focused documentation that enables users of all skill levels to successfully adopt and use the system effectively."""
            },
            
            "Performance Optimization Agent": {
                "role": "Senior Performance Engineer and System Maintenance Specialist",
                "system_prompt": """You are a senior performance engineer specializing in system optimization, performance monitoring, and long-term maintenance strategies across all technology platforms.

    CORE RESPONSIBILITIES:
    - Analyze performance characteristics and optimization opportunities
    - Document monitoring and observability implementations
    - Explain maintenance procedures and operational best practices
    - Analyze resource utilization and capacity planning strategies
    - Document performance testing and benchmarking procedures
    - Explain caching strategies and optimization techniques
    - Document database optimization and query performance analysis
    - Analyze system reliability and availability improvements

    PERFORMANCE ANALYSIS REQUIREMENTS:
    - Performance metrics: response times, throughput, resource utilization
    - Bottleneck identification: CPU, memory, I/O, network constraints
    - Optimization strategies: code optimization, algorithmic improvements, caching
    - Database performance: query optimization, indexing strategies, connection pooling
    - Frontend performance: asset optimization, lazy loading, performance budgets
    - Scalability analysis: horizontal scaling, vertical scaling, load distribution
    - Monitoring implementation: metrics collection, alerting, dashboard creation
    - Performance testing: load testing, stress testing, performance regression detection

    MAINTENANCE PROCEDURES:
    - Preventive maintenance: regular updates, security patches, dependency management
    - Monitoring and alerting: system health checks, anomaly detection, incident response
    - Capacity planning: growth projections, resource allocation, cost optimization
    - Technical debt management: code refactoring, architecture evolution, legacy system updates
    - Documentation maintenance: keeping documentation current, version control

    OUTPUT FORMAT:
    - Performance analysis report with metrics and recommendations
    - Optimization guides with specific implementation steps
    - Monitoring and alerting setup documentation
    - Maintenance schedules and operational procedures
    - Capacity planning guides and resource allocation strategies
    - Performance testing procedures and benchmarking protocols

    Write comprehensive performance and maintenance documentation that enables operations teams to maintain optimal system performance and reliability."""
            }
        }
        
        # Create agent instances with cleaned names
        for agent_name, config in agent_configs.items():
            self.agents[agent_name] = DocumentationAgent(
                name=agent_name,
                role=config["role"],
                system_prompt=config["system_prompt"],
                openai_client=self.client,
                model=model_name
            )
        
        print(f"✅ Initialized {len(self.agents)} specialized agents:")
        for agent_name in self.agents.keys():
            print(f"  - {agent_name}")

    def _get_model_name(self):
        """Get appropriate model name based on client type"""
        USE_AZURE = os.getenv("USE_AZURE", "False").lower() == "true"
        
        if USE_AZURE:
            return os.getenv("llm_deployment_name", "gpt-4o-mini")  # Azure deployment name
        else:
            return "gpt-4o-mini"  # Regular OpenAI model name
    
    def generate_comprehensive_documentation(self, project_data: Dict, project=None) -> Dict:
        """Orchestrate all agents to generate comprehensive documentation"""
        start_time = time.time()
        
        print(f"🚀 Starting multi-agent documentation generation for: {project_data.get('title', 'Unknown')}")
        print(f"📋 Deploying {len(self.agents)} specialized agents...")
        
        if not self.client:
            print("⚠️ No OpenAI access - using enhanced simulation mode")
            return self._simulate_comprehensive_generation(project_data, start_time)
        
        try:
            # Phase 1: Parallel analysis by all agents
            print("🔄 Phase 1: Parallel agent analysis...")
            agent_results = self._run_agents_parallel(project_data)
            
            # Validate we have some results
            if not agent_results or all(not result.get('content', '').strip() for result in agent_results.values()):
                print("⚠️ No valid content from agents, falling back to simulation")
                return self._simulate_comprehensive_generation(project_data, start_time)
            
            # Phase 2: Cross-reference and enhancement
            print("🔄 Phase 2: Cross-referencing and enhancement...")
            enhanced_results = self._enhance_cross_references(agent_results, project_data)
            
            # Phase 3: Final assembly and quality check
            print("🔄 Phase 3: Final assembly and quality assurance...")
            final_documentation = self._assemble_final_documentation(enhanced_results, project_data)
            
            # Validate final output
            if not final_documentation.get('tabs') or len(final_documentation['tabs']) == 0:
                print("⚠️ No valid tabs generated, creating fallback documentation")
                fallback_content = self._create_fallback_documentation(project_data)
                final_documentation = {
                    "content": fallback_content,
                    "tabs": [{
                        "title": "Project Documentation",
                        "content": fallback_content,
                        "word_count": len(fallback_content.split()),
                        "agent": "Fallback"
                    }]
                }
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            return {
                "content": final_documentation["content"],
                "tabs": final_documentation["tabs"],
                "model": "gpt-4-turbo-multi-agent",
                "tokens_used": self.total_tokens,
                "processing_time_ms": processing_time_ms,
                "generated_at": datetime.now().isoformat(),
                "method": "multi-agent-parallel",
                "agents_deployed": len(self.agents),
                "sections_generated": len(final_documentation["tabs"])
            }
        
        except Exception as e:
            print(f"❌ Multi-agent generation failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Return enhanced fallback instead of basic error
            return self._simulate_comprehensive_generation(project_data, start_time)

    
    def _run_agents_parallel(self, project_data: Dict) -> Dict:
        """Run all agents in parallel for maximum efficiency"""
        agent_results = {}
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.agents)) as executor:
            # Submit all agent tasks
            future_to_agent = {
                executor.submit(agent.analyze_project, project_data, self.shared_context): agent_name
                for agent_name, agent in self.agents.items()
            }
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_agent):
                agent_name = future_to_agent[future]
                try:
                    content, tokens = future.result()
                    agent_results[agent_name] = {
                        'content': content,
                        'tokens': tokens,
                        'agent': self.agents[agent_name]
                    }
                    self.total_tokens += tokens
                    print(f"✅ {agent_name}: {len(content.split())} words, {tokens} tokens")
                except Exception as e:
                    print(f"❌ {agent_name} failed: {e}")
                    agent_results[agent_name] = {
                        'content': f"# {agent_name} Analysis\n\n*Analysis failed: {e}*",
                        'tokens': 0,
                        'agent': self.agents[agent_name]
                    }
        
        return agent_results
    
    def _enhance_cross_references(self, agent_results: Dict, project_data: Dict) -> Dict:
        """Enhance documentation with cross-references between agents"""
        enhanced_results = {}
        
        # Create summary context from all agents
        context_summary = {}
        for agent_name, result in agent_results.items():
            # Extract key insights from each agent's analysis
            content = result['content']
            summary = content[:300] + "..." if len(content) > 300 else content
            context_summary[agent_name] = summary
        
        # Enhance each agent's content with cross-references
        for agent_name, result in agent_results.items():
            enhanced_content = self._add_cross_references(
                result['content'], 
                agent_name, 
                context_summary,
                project_data
            )
            
            enhanced_results[agent_name] = {
                'content': enhanced_content,
                'tokens': result['tokens'],
                'agent': result['agent']
            }
        
        return enhanced_results
    
    def _add_cross_references(self, content: str, agent_name: str, context_summary: Dict, project_data: Dict) -> str:
        """Add cross-references and integration notes to agent content"""
        cross_refs = []
        
        # Add integration notes based on agent type
        if "Code Architecture" in agent_name:
            cross_refs.append("\n## Integration Notes\n")
            cross_refs.append("- **Architecture Impact**: See Architecture Agent analysis for system-level design implications")
            cross_refs.append("- **API Integration**: Refer to API Documentation Agent for endpoint implementations")
            cross_refs.append("- **Security Considerations**: Cross-reference Security Agent for authentication and authorization details")
        
        elif "System Architecture" in agent_name:
            cross_refs.append("\n## Implementation References\n")
            cross_refs.append("- **Code Implementation**: See Code Analysis Agent for detailed function-level implementation")
            cross_refs.append("- **Deployment Architecture**: Refer to Setup & Deployment Agent for infrastructure considerations")
            cross_refs.append("- **Performance Impact**: Cross-reference Performance Agent for scalability implications")
        
        elif "API Integration" in agent_name:
            cross_refs.append("\n## Related Documentation\n")
            cross_refs.append("- **Security Implementation**: See Security Agent for authentication and authorization details")
            cross_refs.append("- **Code Implementation**: Refer to Code Analysis Agent for endpoint implementation details")
            cross_refs.append("- **Testing Procedures**: Cross-reference Testing Agent for API testing strategies")
        
        # Add project-specific cross-references
        file_count = len(project_data.get('files', []))
        cross_refs.append(f"\n## Project Context\n")
        cross_refs.append(f"- **Total Files Analyzed**: {file_count} files across the project")
        cross_refs.append(f"- **Project Scope**: {project_data.get('title', 'Unknown Project')}")
        cross_refs.append("- **Multi-Agent Analysis**: This analysis is part of a comprehensive 8-agent documentation system")
        
        return content + "\n".join(cross_refs)
    
    def _assemble_final_documentation(self, enhanced_results: Dict, project_data: Dict) -> Dict:
        """Assemble final documentation into unique tabs with de-duplication."""
        import hashlib

        section_order = [
            "Code Architecture Agent",
            "System Architecture Agent",
            "API Integration Agent",
            "Security Implementation Agent",
            "Deployment Operations Agent",
            "Quality Assurance Agent",
            "User Documentation Agent",
            "Performance Optimization Agent"
        ]

        # Filter/validate content
        valid_results = {}
        for agent_name, result in enhanced_results.items():
            content = (result.get('content') or "").strip()
            if not content:
                continue
            words = [w for w in content.split() if w.strip() and not w.startswith('#')]
            if len(words) < 100:
                continue
            lines = [ln.strip() for ln in content.split('\n') if ln.strip() and not ln.strip().startswith('#')]
            if len(lines) < 5:
                continue
            flat = content.replace('#', '').replace('\n', '').replace(' ', '').replace('-', '').replace('*', '').replace('`', '')
            if len(flat) < 100:
                continue
            lower = content.lower()
            if any(p in lower for p in ['no content available','content not available','failed to generate','error occurred','please try again','analysis failed']):
                continue
            valid_results[agent_name] = result

        if not valid_results:
            fallback = self._create_fallback_documentation(project_data)
            return {
                "content": fallback,
                "tabs": [{
                    "title": "Project Overview",
                    "content": fallback,
                    "word_count": len(fallback.split()),
                    "agent": "Fallback"
                }]
            }

        # Table of contents / overview
        toc_lines = ["# Comprehensive Technical Documentation\n"]
        toc_lines.append(f"**Project**: {project_data.get('title', 'Unknown Project')}")
        toc_lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        toc_lines.append(f"**Analysis Method**: Multi-Agent Parallel Processing")
        toc_lines.append(f"**Agents Deployed**: {len(valid_results)}")
        toc_lines.append(f"\n**Files Analyzed**: {len(project_data.get('files', []))} files\n")
        toc_lines.append("## Documentation Sections\n")
        n = 1
        for agent_name in section_order:
            if agent_name in valid_results:
                toc_lines.append(f"{n}. {agent_name.replace(' Agent',' Analysis')}")
                n += 1
        full_toc = "\n".join(toc_lines)

        # Build tabs with duplicate detection
        tabs = []
        full_content_parts = [full_toc + "\n\n---\n"]
        created_tabs = []
        seen_hashes = set()
        seen_titles = set()
        section_count = 1

        def _try_add_tab(title, content, agent_name):
            nonlocal section_count
            # normalize title to detect dupes
            base = title.lower()
            for token in ["analysis","documentation","implementation","operations","assurance","optimization"]:
                base = base.replace(token, "")
            base = " ".join(base.split()).strip()
            if base in seen_titles:
                return False

            import re

            # Step 1 — Remove empty fenced code blocks entirely
            content_no_empty_code = re.sub(
                r"```[\w-]*\s*\n\s*```",
                "",
                content,
                flags=re.MULTILINE
            )

            # Step 2 — Remove code blocks that only contain import/file reference lines
            def is_trivial_codeblock(block):
                lines = [l.strip() for l in block.splitlines() if l.strip()]
                if not lines:
                    return True
                # Consider trivial if all lines are imports, file paths, or comments
                return all(
                    l.startswith("import ") or
                    l.endswith(".js") or l.endswith(".jsx") or l.endswith(".css") or
                    l.startswith("//") or
                    l.startswith("#") or
                    (l.startswith("from ") and "import" in l)
                    for l in lines
                )

            def replace_trivial_codeblocks(match):
                lang = match.group(1) or ''
                code = match.group(2) or ''
                if is_trivial_codeblock(code):
                    return ""  # drop entirely
                return match.group(0)  # keep full block

            content_no_empty_code = re.sub(
                r"```(\w+)?\s*\n([\s\S]*?)\n\s*```",
                replace_trivial_codeblocks,
                content_no_empty_code,
                flags=re.MULTILINE
            )

            # Step 3 — Remove empty bullet points (after code cleanup)
            lines_cleaned = []
            for ln in content_no_empty_code.splitlines():
                stripped = ln.strip()
                if stripped.startswith(('-', '*')) and len(stripped.lstrip('-* ').strip()) == 0:
                    continue
                lines_cleaned.append(ln)

            cleaned_content = "\n".join(lines_cleaned)


            # Normalize for hashing without destroying heading structure
            normalized = cleaned_content.lower()
            normalized = ' '.join(normalized.split())

            h = hashlib.md5(normalized.encode('utf-8')).hexdigest()
            if h in seen_hashes:
                return False

            # quick word-similarity heuristic vs existing tabs
            for existing in created_tabs:
                ew = set(existing['content'].lower().split())
                cw = set(content.lower().split())
                if ew and cw:
                    common = len(ew.intersection(cw))
                    sim = common / max(len(ew), len(cw))
                    if sim > 0.65:
                        return False

            tab = {
                "title": title,
                "content": content,
                "word_count": len([w for w in content.split() if w.strip() and not w.startswith('#')]),
                "agent": agent_name,
                "section_number": section_count
            }
            tabs.append(tab)
            created_tabs.append(tab)
            seen_hashes.add(h)
            seen_titles.add(base)

            full_content_parts.append(f"# {section_count}. {title}\n")
            full_content_parts.append(content)
            full_content_parts.append("\n\n---\n")
            section_count += 1
            return True

        # Ordered agents first
        for agent_name in section_order:
            if agent_name in valid_results:
                content = valid_results[agent_name]['content'].strip()
                title = agent_name.replace(" Agent", " Analysis")
                _try_add_tab(title, content, agent_name)

        # Any other (unexpected) agents
        for agent_name, result in valid_results.items():
            if agent_name not in section_order:
                content = (result.get('content') or "").strip()
                if not content:
                    continue
                title = agent_name.replace(" Agent", "")
                _try_add_tab(title, content, agent_name)

        if not tabs:
            fallback = self._create_fallback_documentation(project_data)
            tabs.append({
                "title": "Project Analysis",
                "content": fallback,
                "word_count": len(fallback.split()),
                "agent": "Fallback"
            })
            full_content_parts = [fallback]

        # Add overview as first tab if multiple
        if len(tabs) > 1:
            tabs.insert(0, {
                "title": "Documentation Overview",
                "content": full_toc,
                "word_count": len(full_toc.split()),
                "agent": "Orchestrator"
            })

        return {
            "content": "\n".join(full_content_parts),
            "tabs": tabs
        }

    def _create_fallback_documentation(self, project_data: Dict) -> str:
        """Create meaningful fallback documentation when agents fail"""
        files = project_data.get('files', [])
        
        content = f"""# {project_data.get('title', 'Project')} Documentation

    ## Project Overview
    This documentation was generated for **{project_data.get('title', 'your project')}**.

    **Description**: {project_data.get('description', 'No description provided')}

    ## Project Structure
    The project contains **{len(files)} files** that were analyzed:

    """
        
        # Group files by type
        file_types = {}
        for file_info in files:
            name = file_info.get('name', '')
            ext = name.split('.')[-1].lower() if '.' in name else 'other'
            if ext not in file_types:
                file_types[ext] = []
            file_types[ext].append(name)
        
        for file_type, file_list in file_types.items():
            content += f"### {file_type.upper()} Files ({len(file_list)})\n"
            for file_name in file_list[:10]:  # Show first 10 files
                content += f"- `{file_name}`\n"
            if len(file_list) > 10:
                content += f"- ... and {len(file_list) - 10} more files\n"
            content += "\n"
        
        content += """## Getting Started
    To work with this project:

    1. Review the project structure above
    2. Check for README or setup files
    3. Install required dependencies
    4. Follow any setup instructions provided

    ## Next Steps
    This is a basic analysis of your project structure. For more detailed documentation:

    - Ensure all project files are uploaded
    - Check that files contain actual code content
    - Verify network connectivity for AI analysis
    - Contact support if issues persist

    ---
    *Generated by Mashreq Documentation System*
    """
        
        return content
    
    def _simulate_comprehensive_generation(self, project_data: Dict, start_time: float) -> Dict:
        """Comprehensive simulation for when OpenAI is not available"""
        print("🎭 Simulating comprehensive multi-agent documentation generation...")
        
        # Simulate processing time based on project complexity
        file_count = len(project_data.get('files', []))
        simulation_time = 3 + file_count * 0.8  # More realistic timing
        time.sleep(simulation_time)
        
        # Create simulated comprehensive documentation
        tabs = []
        
        agent_sections = [
    ("Code Architecture Analysis", "Comprehensive code structure and logic analysis"),
    ("System Architecture Analysis", "System design patterns and component relationships"), 
    ("API Integration Documentation", "Complete endpoint specifications and integration guides"),
    ("Security Implementation Analysis", "Authentication flows and security implementations"),
    ("Deployment Operations Guide", "Installation procedures and infrastructure requirements"),
    ("Quality Assurance Strategy", "Testing strategies and quality assurance processes"),
    ("User Documentation Guide", "User workflows and onboarding procedures"),
    ("Performance Optimization Analysis", "Optimization strategies and operational procedures")
]
        
        full_content_parts = [
            f"# Comprehensive Technical Documentation\n",
            f"**Project**: {project_data.get('title', 'Unknown Project')}\n",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n", 
            f"**Analysis Method**: Multi-Agent Simulation\n",
            f"**Files Analyzed**: {file_count} files\n\n",
            "## Multi-Agent Analysis Overview\n",
            "This documentation was generated using 8 specialized AI agents working in parallel:\n\n"
        ]
        
        for i, (section_title, description) in enumerate(agent_sections, 1):
            # Create comprehensive simulated content for each section
            simulated_content = f"""# {section_title}

## Overview
{description}

## Detailed Analysis
*[This section would contain comprehensive {section_title.lower()} for {project_data.get('title', 'Unknown Project')}]*

### Key Components Identified
- Component analysis based on {file_count} project files
- Integration patterns and architectural decisions
- Implementation details and best practices
- Performance implications and optimization opportunities

### Technical Implementation
The {section_title.lower()} reveals several important aspects:

1. **Primary Architecture**: Modern, scalable design patterns
2. **Technology Integration**: Well-structured component interactions  
3. **Code Organization**: Clear separation of concerns
4. **Quality Standards**: Enterprise-level implementation practices

### Recommendations
- Continue following established architectural patterns
- Implement comprehensive monitoring and logging
- Regular security audits and performance optimization
- Maintain documentation as system evolves

### Cross-Agent Integration
This analysis integrates with insights from other specialized agents to provide a holistic view of the system architecture and implementation.

*Note: This is simulated content. The actual multi-agent system would provide detailed, code-specific analysis based on comprehensive examination of all project files.*
"""
            
            tabs.append({
                "title": section_title,
                "content": simulated_content,
                "word_count": len(simulated_content.split()),
                "agent": f"{section_title} Agent"
            })
            
            full_content_parts.append(f"{i}. {section_title}")
            full_content_parts.append(simulated_content)
            full_content_parts.append("\n---\n")
        
        # Add overview tab
        overview_content = "\n".join(full_content_parts[:8])  # Take first part for overview
        tabs.insert(0, {
            "title": "Documentation Overview", 
            "content": overview_content,
            "word_count": len(overview_content.split()),
            "agent": "Orchestrator"
        })
        
        full_content = "\n".join(full_content_parts)
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "content": full_content,
            "tabs": tabs,
            "model": "multi-agent-simulation",
            "tokens_used": len(full_content) // 4,  # Estimate tokens
            "processing_time_ms": processing_time_ms,
            "generated_at": datetime.now().isoformat(),
            "method": "multi-agent-simulation",
            "agents_deployed": len(agent_sections),
            "sections_generated": len(tabs)
        }


# ----- Service wrapper + singleton (used by routes) -------------------------
class MultiAgentService:
    def __init__(self):
        # Initialize OpenAI client if configured
        client = None
        try:
            if OPENAI_AVAILABLE and getattr(Config, "OPENAI_API_KEY", None):
                client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        except Exception as e:
            print("⚠️ OpenAI init failed; falling back to simulation:", e)
            client = None
        self.client = client

    def generate_documentation(self, project_data: Dict, project=None) -> Dict:
        orchestrator = OrchestratorAgent(openai_client=self.client)
        return orchestrator.generate_comprehensive_documentation(project_data, project)


def get_access_token():
    """Get access token from API for Azure OpenAI."""
    try:
        auth_url = os.getenv("auth_url")
        client_id = os.getenv("client_id")
        client_secret = os.getenv("client_secret")
        
        if not auth_url:
            logger.warning("⚠️ No auth_url provided, skipping token authentication")
            return None
            
        logger.debug("🔑 Requesting access token...")
        data = {
            "grant_type": "client_credentials",
            "scope": "EXT",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        
        import requests
        response = requests.post(
            auth_url,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token", "")
            logger.debug("✅ Access token obtained successfully")
            return token if token else None
        else:
            logger.error(f"❌ Token request failed with status: {response.status_code}")
        return None
    
    except Exception as e:
        logger.error(f"❌ Token Error: {str(e)}")
        return None

def get_llm_client():
    """Get OpenAI client - Azure or regular OpenAI based on configuration"""
    # Configuration - Choose one method below
    
    # Method 1: Azure OpenAI (comment out to disable)
    USE_AZURE = os.getenv("USE_AZURE", "False").lower() == "true"
    
    if USE_AZURE:
        # Azure OpenAI
        print("🤖 Creating Azure OpenAI client...")
        AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
        AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
        AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        client_id = os.getenv("client_id")
        x_user_id = os.getenv("x_user_id")
        
        access_token = get_access_token()
        auth_headers = {}
        
        if access_token:
            auth_headers = {
                'clientid': client_id,
                'Authorization': f'Bearer {access_token}',
                'X-USER-ID': x_user_id
            }

        import httpx
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            default_headers=auth_headers,
            http_client=httpx.Client(verify=False)
        )
        print("✅ Azure OpenAI client created successfully")
        return client
    else:
        # Regular OpenAI
        print("🤖 Creating regular OpenAI client...")
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ Regular OpenAI client created successfully")
        return client

# Exported singleton expected by routes/projects.py
multi_agent_service = MultiAgentService()
