# services/openai_service.py - Enhanced Multi-Agent, Tabbed Output Version with Retries and Content Fix

import time
import json
from datetime import datetime
from config import Config

class Agent:
    """
    Represents a specialized documentation agent responsible for one subsection.
    """
    def __init__(self, name, system_prompt, model="gpt-3.5-turbo", temperature=0.3, max_tokens=1200, openai_client=None):
        self.name = name
        self.system_prompt = system_prompt.strip()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.openai = openai_client


    def run(self, user_prompt, max_retries=3):
        """Executes a chat completion for this agent with retry on transient errors.
        Returns a tuple (content, tokens)."""
        if not self.openai:
            raise RuntimeError(f"OpenAI client not initialized for agent {self.name}")
        attempt = 0
        wait = 1
        while attempt < max_retries:
            try:
                response = self.openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user",   "content": user_prompt}
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                content = response.choices[0].message.content.strip()
                tokens = getattr(response.usage, "total_tokens", 0)
                return content, tokens
            except Exception as e:
                attempt += 1
                if attempt < max_retries:
                    print(f"⚠️  Agent {self.name} attempt {attempt} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                    wait *= 2
                else:
                    # Final retry
                    print(f"⚠️  Agent {self.name} final retry after errors.")
                    response = self.openai.ChatCompletion.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user",   "content": user_prompt}
                        ],
                        temperature=self.temperature,
                        max_tokens=self.max_tokens
                    )
                    content = response.choices[0].message.content.strip()
                    tokens = getattr(response.usage, "total_tokens", 0)
                    return content, tokens

class OpenAIService:
    def __init__(self):
        """Initialize OpenAI service with proper error handling."""
        self.api_key = None
        self.openai = None
        self.model = "gpt-3.5-turbo"
        # ← ADD THIS BLOCK:
        self.min_words_per_section = 150
        self.max_tabs = 10
        self.default_sections = [
    "Project Overview",
    "Key Features & Functionality", 
    "Technology Stack Analysis",
    "Architecture & Design Patterns",
    "Directory Structure Breakdown",
    "Core Components & Modules",
    "Data Flow & System Interactions",
    "API Endpoints & Routes",
    "Installation Prerequisites",
    "Environment Setup & Configuration", 
    "Getting Started Tutorial",
    "Usage Examples & Workflows",
    "Code Walkthrough & Logic",
    "Security & Authentication",
    "Testing Strategy & Examples",
    "Deployment & Production Setup",
    "Configuration Options",
    "Troubleshooting & FAQ",
    "Performance Considerations",
    "Maintenance & Updates"
]
        try:
            import openai
            from config import Config
            api_key = Config.OPENAI_API_KEY
            if api_key and api_key.startswith('sk-'):
                openai.api_key = api_key
                self.api_key = api_key
                self.openai = openai
                print("✅ OpenAI service initialized with API key")
            else:
                print("⚠️  No valid OpenAI API key found — falling back to simulation mode")
        except ImportError:
            print("⚠️  openai package not installed — falling back to simulation mode")
        except Exception as e:
            print(f"⚠️  OpenAI initialization failed: {e} — falling back to simulation mode")

        self.agents = self._create_agents()


    def _call_agent(self, section, project_data):
        """
        Look up the Agent for `section`, build its user prompt
        (including title, description and file list), and run it.
        """
        agent = self.agents.get(section)
        if not agent:
            # no agent defined for this section
            return f"*No agent defined for '{section}'*", 0

        # build a consistent user prompt
        files_md = self._format_file_list(project_data.get("files", []))
        prompt = (
            f"Project: **{project_data.get('title','Untitled')}**\n"
            f"Description: {project_data.get('description','No description')}\n\n"
            f"Files:\n{files_md}\n\n"
            f"Please write the **{section}** section in detailed, professional Markdown."
        )
        return agent.run(prompt)


    def generate_documentation(self, project_data):
        """Enhanced documentation generation with intelligent content splitting"""
        start_time = time.time()
        
        print(f"🚀 Starting documentation generation for: {project_data.get('title', 'Unknown')}")
        
        # Check if we have OpenAI access
        if not self.openai or not self.api_key:
            print("⚠️  No OpenAI access - using simulation")
            return self._simulate_generation(project_data, start_time)

        # Generate initial sections
        initial_sections = project_data.get("sections", self.default_sections)
        all_content = []
        total_tokens = 0

        # Generate content for each section (SINGLE LOOP ONLY)
        for section in initial_sections:
            try:
                print(f"🤖 Generating content for section: {section}")
                content, tokens = self._call_agent(section, project_data)
                
                # Clean up content
                for sec in initial_sections:
                    if content.rstrip().endswith(sec):
                        content = content.rstrip()[:-len(sec)].rstrip()

                word_count = len(content.split())
                
                # Skip very short sections
                if word_count < 100:
                    print(f"⚠️ Skipping '{section}' ({word_count} words too short)")
                    continue

                all_content.append({
                    'title': section,
                    'content': content,
                    'word_count': word_count
                })
                total_tokens += tokens
                print(f"✅ Generated '{section}': {word_count} words, {tokens} tokens")
                
            except Exception as e:
                print(f"❌ Error generating section '{section}': {e}")
                continue

        print(f"📊 Total sections generated: {len(all_content)}")

        # Intelligent content splitting
        print(f"🔧 Starting intelligent content splitting...")
        final_tabs = self._intelligent_content_split(all_content)
        print(f"✅ Content splitting complete: {len(final_tabs)} final sections")
        
        # Fallback if not enough content
        if len(final_tabs) < 3:
            print("⚠️  Too few sections generated, using simulation fallback")
            return self._simulate_generation(project_data, start_time)

        # Assemble final documentation
        full_content = "\n\n".join(f"## {t['title']}\n\n{t['content']}" for t in final_tabs)
        processing_time_ms = int((time.time() - start_time) * 1000)

        return {
            "content": full_content,
            "tabs": final_tabs,
            "diagrams": {},  # Will be populated by diagram service
            "diagram_count": 0,
            "model": self.model,
            "tokens_used": total_tokens,
            "processing_time_ms": processing_time_ms,
            "generated_at": datetime.now().isoformat(),
            "method": "openai_intelligent_split"
        }
    


    def _intelligent_content_split(self, content_sections):
        """Intelligently split content into well-sized tabs"""
        final_tabs = []
        target_words_per_tab = 300  # Reduced target for better distribution
        max_words_per_tab = 600     # Reduced max for more sections
        min_words_per_tab = 150     # Reduced minimum
        
        print(f"🔧 Processing {len(content_sections)} initial sections for intelligent splitting")
        
        for section in content_sections:
            title = section['title']
            content = section['content']
            word_count = section['word_count']
            
            print(f"📝 Processing section '{title}' with {word_count} words")
            
            if word_count <= max_words_per_tab:
                # Section is acceptable size, keep as-is
                final_tabs.append({
                    'title': title,
                    'content': content,
                    'word_count': word_count
                })
                print(f"✅ Kept section '{title}' as-is ({word_count} words)")
            else:
                # Section is too long, needs intelligent splitting
                print(f"✂️ Splitting long section '{title}' ({word_count} words)")
                split_sections = self._split_long_section(title, content, target_words_per_tab)
                final_tabs.extend(split_sections)
                print(f"✅ Split into {len(split_sections)} parts")
        
        print(f"📊 Before merging: {len(final_tabs)} sections")
        
        # Don't merge small sections - keep them separate for better distribution
        # final_tabs = self._merge_small_sections(final_tabs, min_words_per_tab)
        
        # Sort by logical order if needed
        final_tabs = self._reorder_sections(final_tabs)
        
        # Limit total tabs but allow more sections
        max_final_tabs = 15  # Increased from 10
        if len(final_tabs) > max_final_tabs:
            print(f"⚠️ Limiting to {max_final_tabs} tabs (had {len(final_tabs)})")
            final_tabs = final_tabs[:max_final_tabs]
        
        print(f"🎯 Final result: {len(final_tabs)} sections for sidebar")
        for tab in final_tabs:
            print(f"   - {tab['title']} ({tab['word_count']} words)")
        
        return final_tabs

    def _split_long_section(self, title, content, target_words):
        """Split a long section into smaller logical parts with better logic"""
        # First try to split by clear markdown headers
        header_splits = self._split_by_headers(title, content, target_words)
        if len(header_splits) > 1:
            return header_splits
        
        # Fallback to paragraph splitting
        #paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        paragraphs = self._split_into_blocks(content)
        if len(paragraphs) <= 1:
            # Single paragraph, split by sentences
            return self._split_by_sentences(title, content, target_words)
        
        sections = []
        current_section = []
        current_words = 0
        part_num = 1
        
        for paragraph in paragraphs:
            para_words = len(paragraph.split())
            
            # If adding this paragraph exceeds target and we have content, create new section
            if current_words + para_words > target_words and current_section:
                sections.append({
                    'title': f"{title} - Part {part_num}",
                    'content': '\n\n'.join(current_section),
                    'word_count': current_words
                })
                current_section = [paragraph]
                current_words = para_words
                part_num += 1
            else:
                current_section.append(paragraph)
                current_words += para_words
        
        # Add remaining content
        if current_section:
            final_title = f"{title} - Part {part_num}" if part_num > 1 else title
            sections.append({
                'title': final_title,
                'content': '\n\n'.join(current_section),
                'word_count': current_words
            })
        
        return sections if sections else [{
            'title': title,
            'content': content,
            'word_count': len(content.split())
        }]
    
    def _split_into_blocks(self, content):
        """
        Split content into “blocks” on blank lines, but do NOT break apart
        anything that lives inside a fenced code block.
        """
        blocks = []
        current = []
        in_fence = False

        for line in content.split('\n'):
            stripped = line.strip()
            # Toggle fence state if we see a fence delimiter
            if stripped.startswith('```'):
                current.append(line)
                in_fence = not in_fence
            elif not in_fence and stripped == '':
                # blank line outside of fence ends a block
                if current:
                    blocks.append('\n'.join(current).strip())
                    current = []
            else:
                current.append(line)

        # catch any trailing block
        if current:
            blocks.append('\n'.join(current).strip())

        return [b for b in blocks if b]


    def _split_by_headers(self, title, content, target_words):
        """Split content by markdown headers"""
        sections = []
        lines = content.split('\n')
        current_section = []
        current_title = title
        current_words = 0
        
        for line in lines:
            if line.startswith('##') and current_section:
                # Found a header, save previous section
                sections.append({
                    'title': current_title,
                    'content': '\n'.join(current_section),
                    'word_count': current_words
                })
                
                # Start new section
                header_text = line.replace('##', '').strip()
                current_title = f"{title} - {header_text}"
                current_section = []
                current_words = 0
            else:
                current_section.append(line)
                current_words += len(line.split())
        
        # Add final section
        if current_section:
            sections.append({
                'title': current_title,
                'content': '\n'.join(current_section),
                'word_count': current_words
            })
        
        return sections

    def _split_by_sentences(self, title, content, target_words):
        """Split content by sentences when paragraphs aren't available"""
        sentences = [s.strip() + '.' for s in content.replace('\n', ' ').split('.') if s.strip()]
        
        sections = []
        current_section = []
        current_words = 0
        part_num = 1
        
        for sentence in sentences:
            sentence_words = len(sentence.split())
            
            if current_words + sentence_words > target_words and current_section:
                sections.append({
                    'title': f"{title} - Part {part_num}",
                    'content': ' '.join(current_section),
                    'word_count': current_words
                })
                current_section = [sentence]
                current_words = sentence_words
                part_num += 1
            else:
                current_section.append(sentence)
                current_words += sentence_words
        
        if current_section:
            final_title = f"{title} - Part {part_num}" if part_num > 1 else title
            sections.append({
                'title': final_title,
                'content': ' '.join(current_section),
                'word_count': current_words
            })
        
        return sections

    def _merge_small_sections(self, sections, min_words):
        """Merge sections that are too small"""
        if len(sections) <= 1:
            return sections
        
        merged = []
        i = 0
        
        while i < len(sections):
            current = sections[i]
            
            # If current section is too small and we can merge with next
            if (current['word_count'] < min_words and 
                i + 1 < len(sections) and 
                current['word_count'] + sections[i + 1]['word_count'] < 1000):
                
                next_section = sections[i + 1]
                merged_content = current['content'] + '\n\n' + next_section['content']
                merged_title = f"{current['title']} & {next_section['title']}"
                
                merged.append({
                    'title': merged_title,
                    'content': merged_content,
                    'word_count': current['word_count'] + next_section['word_count']
                })
                i += 2  # Skip next section since we merged it
            else:
                merged.append(current)
                i += 1
        
        return merged
    
    def _reorder_sections(self, sections):
        """Reorder sections in logical sequence"""
        # Define preferred order
        order_priority = {
            'project overview': 1,
            'key features': 2, 
            'technology stack': 3,
            'architecture': 4,
            'directory structure': 5,
            'components': 6,
            'modules': 6,
            'data flow': 7,
            'api': 8,
            'installation': 9,
            'setup': 10,
            'configuration': 11,
            'getting started': 12,
            'tutorial': 13,
            'usage': 14,
            'examples': 15,
            'code walkthrough': 16,
            'security': 17,
            'testing': 18,
            'deployment': 19,
            'troubleshooting': 20,
            'performance': 21,
            'maintenance': 22
        }
        
        def get_order_score(section_title):
            title_lower = section_title.lower()
            for keyword, score in order_priority.items():
                if keyword in title_lower:
                    return score
            return 999  # Put unknown sections at the end
        
        # Sort sections by logical order
        sections.sort(key=lambda x: get_order_score(x['title']))
        return sections


    def _create_agents(self):
        """Defines a comprehensive set of agents for each documentation subsection."""
        section_prompts = {
    "Project Overview": (
        "You are a technical writer. Write a comprehensive project overview explaining the purpose, "
        "scope, and main objectives. Include what problem this project solves and who the target users are. "
        "Write 200-400 words with clear headings and bullet points where appropriate."
    ),
    "Key Features & Functionality": (
        "You are a product analyst. List and explain each key feature in detail. For each feature, "
        "explain what it does, why it's important, and how users interact with it. "
        "Write 250-450 words with subheadings for each major feature."
    ),
    "Technology Stack Analysis": (
        "You are a solution architect. Analyze the technology stack in detail. For each technology "
        "(frameworks, libraries, tools), explain: 1) Its role in the project, 2) Why it was chosen, "
        "3) How it integrates with other components, 4) Version and configuration details. "
        "Write 300-500 words with clear sections for frontend, backend, database, and tools."
    ),
    "Architecture & Design Patterns": (
        "You are a senior architect. Explain the overall system architecture and design patterns used. "
        "Cover: 1) High-level architecture, 2) Design patterns implemented, 3) Architectural decisions "
        "and rationale, 4) System boundaries and interfaces. Write 250-400 words with diagrams descriptions."
    ),
    "Directory Structure Breakdown": (
    "You are a code organization expert providing an in-depth analysis of the project's directory structure. "
    "Create a comprehensive guide that explains each directory and important file in detail. "
    "For each major directory and important file, provide: "
    "\n\n**1. Detailed Purpose & Responsibility** - Explain exactly what this directory/file does and why it exists in the project"
    "\n**2. Key Contents & Components** - List and describe the important files/subdirectories within, with specific examples"
    "\n**3. Implementation Details** - Technical specifics about what's implemented, including main functions, classes, or configurations"
    "\n**4. Relationships & Dependencies** - How it connects to and interacts with other parts of the system"
    "\n**5. Architecture Role** - How this fits into the overall system architecture and workflow"
    "\n\nFor configuration files (package.json, vite.config.js, etc.), explain their key settings and impact on the project. "
    "For code files, describe their main functions, classes, and purpose. "
    "For directories, explain the organization pattern and rationale. "
    "Structure your response with clear markdown headings (## for major directories, ### for subdirectories, #### for important files). "
    "Write 600-1000 words with detailed explanations. This should be a comprehensive guide that helps developers understand the entire codebase organization."
),
    "Core Components & Modules": (
        "You are an engineering lead. Detail each major component/module in the system. "
        "For each component: 1) Purpose and functionality, 2) Key classes/functions, "
        "3) Dependencies and interactions, 4) Usage examples. Write 300-500 words with clear component sections."
    ),
    "Data Flow & System Interactions": (
        "You are a systems engineer. Map out how data flows through the system and how components interact. "
        "Cover: 1) Request/response flow, 2) Data transformation points, 3) Inter-component communication, "
        "4) External system integrations. Write 250-400 words with step-by-step flow descriptions."
    ),
    "API Endpoints & Routes": (
        "You are an API documentation specialist. Document all API endpoints and routes. "
        "For each endpoint: 1) HTTP method and path, 2) Parameters and request format, "
        "3) Response format and examples, 4) Authentication requirements. Write 300-500 words with endpoint tables."
    ),
    "Installation Prerequisites": (
        "You are an installation specialist. Detail all prerequisites and system requirements. "
        "Cover: 1) Software dependencies and versions, 2) System requirements, "
        "3) Required accounts/credentials, 4) Pre-installation checklist. Write 200-350 words with clear requirements lists."
    ),
    "Environment Setup & Configuration": (
        "You are a DevOps engineer. Provide step-by-step environment setup instructions. "
        "Include: 1) Environment variables, 2) Configuration files, 3) Database setup, "
        "4) Service configurations. Write 250-400 words with numbered steps and code examples."
    ),
    "Getting Started Tutorial": (
        "You are a user educator. Create a comprehensive getting started guide. "
        "Include: 1) First-time setup walkthrough, 2) Basic usage examples, "
        "3) Common first tasks, 4) Verification steps. Write 300-450 words with step-by-step instructions."
    ),
    "Usage Examples & Workflows": (
        "You are a product specialist. Showcase real-world usage scenarios and workflows. "
        "Cover: 1) Common use cases, 2) Step-by-step workflows, 3) Best practices, "
        "4) Tips and tricks. Write 250-400 words with practical examples and code snippets."
    ),
    "Code Walkthrough & Logic": (
        "You are a code analyst. Provide a detailed walkthrough of the core application logic. "
        "Explain: 1) Main execution flow, 2) Key algorithms and functions, 3) Business logic implementation, "
        "4) Critical code sections with explanations. Write 300-500 words with inline code references."
    ),
    "Security & Authentication": (
        "You are a security engineer. Document the security measures and authentication mechanisms. "
        "Cover: 1) Authentication methods, 2) Authorization and permissions, 3) Security best practices, "
        "4) Data protection measures. Write 250-400 words with security implementation details."
    ),
    "Testing Strategy & Examples": (
        "You are a QA engineer. Explain the testing approach and provide examples. "
        "Include: 1) Test types and frameworks, 2) Test structure and organization, "
        "3) Running tests, 4) Example test cases. Write 250-400 words with test command examples."
    ),
    "Deployment & Production Setup": (
        "You are a deployment engineer. Detail the deployment process and production setup. "
        "Cover: 1) Deployment methods, 2) Production environment setup, 3) Monitoring and logging, "
        "4) Scaling considerations. Write 300-450 words with deployment commands and configurations."
    ),
    "Configuration Options": (
        "You are a configuration specialist. Document all configuration options and customization. "
        "Include: 1) Configuration files and formats, 2) Available options and defaults, "
        "3) Environment-specific configurations, 4) Advanced customization. Write 200-350 words with config examples."
    ),
    "Troubleshooting & FAQ": (
        "You are a support engineer. Provide troubleshooting guidance and answers to common questions. "
        "Include: 1) Common issues and solutions, 2) Debugging techniques, 3) FAQ with answers, "
        "4) Where to get help. Write 250-400 words with problem-solution pairs."
    ),
    "Performance Considerations": (
        "You are a performance engineer. Discuss performance aspects and optimization. "
        "Cover: 1) Performance benchmarks, 2) Optimization strategies, 3) Scaling considerations, "
        "4) Monitoring and profiling. Write 200-350 words with performance tips and metrics."
    ),
    "Maintenance & Updates": (
        "You are a maintenance specialist. Explain ongoing maintenance and update procedures. "
        "Include: 1) Regular maintenance tasks, 2) Update and upgrade procedures, "
        "3) Backup and recovery, 4) Version management. Write 250-400 words with maintenance schedules and procedures."
    )
}

        return {
            section: Agent(
                name=section.replace(" ", "_")[:32],
                system_prompt=prompt,
                openai_client=self.openai
            )
            for section, prompt in section_prompts.items()
        }

    def _format_file_list(self, files):
        """Formats the file list as Markdown for prompts."""
        if not files:
            return "- No files provided"
        lines = []
        for f in files:
            name = f.get('name', 'Unknown')
            size = f.get('size', 0)
            type_ = self._get_file_type(name)
            lines.append(f"- **{name}** ({type_}, {size:,} bytes)")
        return "\n".join(lines)

    def _get_file_type(self, filename):
        """Determine file type from filename extension."""
        if '.' not in filename:
            return 'Unknown'
        ext = filename.lower().split('.')[-1]
        type_map = {
            'py': 'Python', 'js': 'JavaScript', 'jsx': 'React JSX',
            'ts': 'TypeScript', 'tsx': 'React TS', 'java': 'Java',
            'cpp': 'C++', 'c': 'C', 'cs': 'C#', 'php': 'PHP',
            'rb': 'Ruby', 'go': 'Go', 'rs': 'Rust', 'swift': 'Swift',
            'kt': 'Kotlin', 'scala': 'Scala', 'html': 'HTML',
            'css': 'CSS', 'json': 'JSON', 'md': 'Markdown',
            'yaml': 'YAML', 'yml': 'YAML', 'sql': 'SQL', 'sh': 'Shell'
        }
        return type_map.get(ext, ext.upper())

    def _simulate_generation(self, project_data, start_time):
        """Fallback: simulate documentation generation for the whole project."""
        print("🎭 Simulating documentation generation...")
        time.sleep(2 + len(project_data.get("files", [])) * 0.5)
        # Simple single-tab fallback
        doc = "# " + project_data.get("title", "Project Documentation") + "\n\n" + \
              project_data.get("description", "") + "\n\n" + \
              "*(Simulated comprehensive documentation)*"
        processing_time_ms = int((time.time() - start_time) * 1000)
        return {
            "content": doc,
            "tabs": [{"title": "Full Documentation", "content": doc}],
            "model": "ai-simulation",
            "tokens_used": len(doc) // 4,
            "processing_time_ms": processing_time_ms,
            "generated_at": datetime.now().isoformat(),
            "method": "simulation"
        }

# Singleton instance
openai_service = OpenAIService()
