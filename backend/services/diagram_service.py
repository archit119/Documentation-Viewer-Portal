# services/diagram_service.py
import os
import json
import time
import ast
import re
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from collections import Counter, defaultdict, deque
import networkx as nx

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    MATPLOTLIB_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Matplotlib not available: {e}")
    MATPLOTLIB_AVAILABLE = False

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    print("⚠️ NetworkX not available")
    NETWORKX_AVAILABLE = False

class CodeAnalyzer:
    """AI-powered code analysis engine"""
    
    def __init__(self):
        self.components = {}
        self.routes = {}
        self.data_flows = []
        self.user_journeys = []
        self.dependencies = {}
        
    def analyze_project_files(self, files):
        """Main analysis entry point"""
        print("🔍 Starting AI code analysis...")
        
        # Reset analysis data
        self.components = {}
        self.routes = {}
        self.data_flows = []
        self.user_journeys = []
        self.dependencies = {}
        
        for file_info in files:
            filename = file_info.get('name', '')
            content = file_info.get('content', '')
            
            if not content:
                continue
                
            try:
                if filename.endswith('.py'):
                    self._analyze_python_file(filename, content)
                elif filename.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    self._analyze_javascript_file(filename, content)
                elif filename.endswith('.json'):
                    self._analyze_json_file(filename, content)
            except Exception as e:
                print(f"⚠️ Error analyzing {filename}: {e}")
                continue
        
        # After analyzing all files, detect patterns
        self._detect_user_journeys()
        self._detect_data_flows()
        
        return {
            'components': self.components,
            'routes': self.routes,
            'data_flows': self.data_flows,
            'user_journeys': self.user_journeys,
            'dependencies': self.dependencies
        }
    
    def _analyze_python_file(self, filename, content):
        """Analyze Python files for backend patterns"""
        try:
            tree = ast.parse(content)
            
            # Extract routes (Flask/FastAPI)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for route decorators
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Call):
                            if hasattr(decorator.func, 'attr'):
                                if decorator.func.attr in ['route', 'get', 'post', 'put', 'delete']:
                                    route_path = self._extract_route_path(decorator)
                                    method = decorator.func.attr.upper() if decorator.func.attr != 'route' else 'GET'
                                    
                                    self.routes[f"{method} {route_path}"] = {
                                        'file': filename,
                                        'function': node.name,
                                        'method': method,
                                        'path': route_path,
                                        'type': 'api_endpoint'
                                    }
                
                # Extract class definitions (models, services)
                elif isinstance(node, ast.ClassDef):
                    self.components[node.name] = {
                        'file': filename,
                        'type': 'class',
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'category': self._classify_python_class(node.name, filename)
                    }
                    
        except SyntaxError:
            print(f"⚠️ Syntax error in {filename}, skipping AST analysis")
            # Fallback to regex analysis
            self._analyze_python_with_regex(filename, content)
    
    def _analyze_javascript_file(self, filename, content):
        """Analyze JS/JSX files for frontend patterns"""
        
        # Extract React components
        component_patterns = [
            r'function\s+([A-Z]\w+)\s*\(',
            r'const\s+([A-Z]\w+)\s*=\s*\(',
            r'class\s+([A-Z]\w+)\s+extends',
            r'export\s+default\s+function\s+([A-Z]\w+)'
        ]
        
        for pattern in component_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                component_name = match.group(1)
                self.components[component_name] = {
                    'file': filename,
                    'type': 'react_component',
                    'category': 'frontend'
                }
        
        # Extract API calls
        api_patterns = [
            r'fetch\([\'"`]([^\'"``]+)[\'"`]',
            r'axios\.([a-z]+)\([\'"`]([^\'"``]+)[\'"`]',
            r'\.([a-z]+)\([\'"`]/api([^\'"``]+)[\'"`]'
        ]
        
        for pattern in api_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                if 'fetch' in pattern:
                    endpoint = match.group(1)
                    method = 'GET'  # Default
                else:
                    method = match.group(1).upper()
                    endpoint = match.group(2)
                
                self.data_flows.append({
                    'from': filename,
                    'to': endpoint,
                    'type': 'api_call',
                    'method': method
                })
        
        # Extract user interactions
        interaction_patterns = [
            r'onClick\s*=',
            r'onSubmit\s*=',
            r'onChange\s*=',
            r'onInput\s*=',
            r'addEventListener\([\'"`]([^\'"``]+)[\'"`]'
        ]
        
        for pattern in interaction_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                interaction_type = match.group(1) if 'addEventListener' in pattern else pattern.split('=')[0]
                self.user_journeys.append({
                    'component': filename,
                    'interaction': interaction_type,
                    'type': 'user_action'
                })
    
    def _analyze_json_file(self, filename, content):
        """Analyze JSON files for configuration and dependencies"""
        try:
            data = json.loads(content)
            
            if 'package.json' in filename:
                dependencies = data.get('dependencies', {})
                dev_dependencies = data.get('devDependencies', {})
                
                self.dependencies['frontend'] = {
                    **dependencies,
                    **dev_dependencies
                }
            
            elif 'requirements' in filename or 'Pipfile' in filename:
                # Handle Python dependencies (if JSON format)
                self.dependencies['backend'] = data
                
        except json.JSONDecodeError:
            pass
    
    def _detect_user_journeys(self):
        """Detect complete user journeys from component interactions"""
        print("🎯 Detecting user journeys...")
        
        # Group interactions by component
        component_interactions = defaultdict(list)
        for journey in self.user_journeys:
            component_interactions[journey['component']].append(journey)
        
        # Create journey flows
        detected_journeys = []
        
        # Common user journey patterns
        for component, interactions in component_interactions.items():
            if any('onClick' in str(i) for i in interactions):
                if 'Login' in component or 'Auth' in component:
                    detected_journeys.append({
                        'name': 'Authentication Flow',
                        'steps': ['User visits login page', 'Enter credentials', 'Click login', 'Redirect to dashboard'],
                        'components': [component],
                        'type': 'authentication'
                    })
                elif 'Create' in component or 'Add' in component:
                    detected_journeys.append({
                        'name': 'Creation Flow',
                        'steps': ['User clicks create', 'Fill form', 'Submit data', 'Confirmation'],
                        'components': [component],
                        'type': 'creation'
                    })
        
        # Look for multi-component journeys
        if len(component_interactions) > 1:
            detected_journeys.append({
                'name': 'Main User Journey',
                'steps': ['Landing page', 'Navigation', 'Action', 'Result'],
                'components': list(component_interactions.keys()),
                'type': 'main_flow'
            })
        
        self.user_journeys = detected_journeys
    
    def _detect_data_flows(self):
        """Enhance data flow detection"""
        print("💫 Detecting data flows...")
        
        # Add backend-to-frontend flows
        for route_name, route_info in self.routes.items():
            # Find components that might call this route
            for component_name, component_info in self.components.items():
                if component_info['category'] == 'frontend':
                    self.data_flows.append({
                        'from': component_name,
                        'to': route_name,
                        'type': 'api_request',
                        'description': f"{component_name} calls {route_name}"
                    })
    
    def _extract_route_path(self, decorator):
        """Extract route path from decorator"""
        if hasattr(decorator, 'args') and decorator.args:
            if hasattr(decorator.args[0], 's'):
                return decorator.args[0].s
            elif hasattr(decorator.args[0], 'value'):
                return decorator.args[0].value
        return '/unknown'
    
    def _classify_python_class(self, class_name, filename):
        """Classify Python class based on name and file"""
        name_lower = class_name.lower()
        file_lower = filename.lower()
        
        if 'model' in name_lower or 'model' in file_lower:
            return 'data_model'
        elif 'service' in name_lower or 'service' in file_lower:
            return 'business_logic'
        elif 'controller' in name_lower or 'route' in file_lower:
            return 'api_controller'
        else:
            return 'utility'
    
    def _analyze_python_with_regex(self, filename, content):
        """Fallback regex analysis for Python files"""
        # Extract function definitions
        func_pattern = r'def\s+([a-zA-Z_]\w*)\s*\('
        functions = re.findall(func_pattern, content)
        
        # Extract class definitions
        class_pattern = r'class\s+([a-zA-Z_]\w*)\s*[\(:]'
        classes = re.findall(class_pattern, content)
        
        for func in functions:
            self.components[func] = {
                'file': filename,
                'type': 'function',
                'category': 'backend'
            }
        
        for cls in classes:
            self.components[cls] = {
                'file': filename,
                'type': 'class',
                'category': self._classify_python_class(cls, filename)
            }


class DiagramService:
    def __init__(self):
        self.output_dir = os.path.join('static', 'diagrams')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Set matplotlib backend for server environments
        if MATPLOTLIB_AVAILABLE:
            plt.switch_backend('Agg')
        
        # Color scheme matching your app
        self.colors = {
            'primary': '#0055A4',
            'secondary': '#F58220', 
            'accent': '#2D4A6B',
            'light': '#E8F4F8',
            'dark': '#0F1419',
            'success': '#10B981',
            'warning': '#F59E0B',
            'error': '#EF4444'
        }
        
        self.analyzer = CodeAnalyzer()

    def generate_project_diagrams(self, project_data):
        """Generate AI-powered diagrams for a project"""
        project_id = project_data.get('id', 'unknown')
        start_time = time.time()
        
        print(f"🎨 Generating AI-powered diagrams for project: {project_data.get('title', 'Unknown')}")
        
        if not MATPLOTLIB_AVAILABLE:
            return {
                'success': False,
                'error': 'Matplotlib not available',
                'diagrams': {},
                'count': 0
            }
        
        diagrams = {}
        
        try:
            # Analyze project files with AI
            files = project_data.get('files', [])
            analysis_result = self.analyzer.analyze_project_files(files)
            
            # Generate diagrams based on AI analysis
            diagrams['architecture'] = self._create_ai_architecture_diagram(project_data, analysis_result)
            diagrams['user_journey'] = self._create_user_journey_diagram(project_data, analysis_result)
            diagrams['data_flow'] = self._create_data_flow_diagram(project_data, analysis_result)
            
            # Keep existing diagrams for compatibility
            diagrams['file_structure'] = self._create_file_structure_diagram(project_data)
            diagrams['tech_stack'] = self._create_tech_stack_diagram(project_data, analysis_result)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'diagrams': diagrams,
                'count': len(diagrams),
                'processing_time_ms': processing_time,
                'generated_at': datetime.now().isoformat(),
                'analysis_summary': {
                    'components_found': len(analysis_result['components']),
                    'routes_found': len(analysis_result['routes']),
                    'user_journeys_detected': len(analysis_result['user_journeys']),
                    'data_flows_detected': len(analysis_result['data_flows'])
                }
            }
            
        except Exception as e:
            print(f"❌ Error generating diagrams: {e}")
            return {
                'success': False,
                'error': str(e),
                'diagrams': {},
                'count': 0
            }
    
    def _create_ai_architecture_diagram(self, project_data, analysis):
        """Create AI-powered architecture flowchart"""
        fig, ax = plt.subplots(figsize=(14, 10))
        fig.patch.set_facecolor('white')
        
        components = analysis['components']
        routes = analysis['routes']
        
        if not components:
            return self._create_simple_architecture_diagram(project_data)
        
        # Categorize components
        categories = {
            'frontend': [],
            'backend': [],
            'data': [],
            'api': []
        }
        
        for name, info in components.items():
            category = info.get('category', 'backend')
            if category == 'frontend' or info.get('type') == 'react_component':
                categories['frontend'].append(name)
            elif category in ['data_model', 'data']:
                categories['data'].append(name)
            elif category in ['api_controller', 'api'] or info.get('type') == 'api_endpoint':
                categories['api'].append(name)
            else:
                categories['backend'].append(name)
        
        # Add routes to API category
        for route_name in routes.keys():
            categories['api'].append(route_name.split(' ')[-1])  # Extract path
        
        # Create network graph
        if NETWORKX_AVAILABLE:
            G = nx.DiGraph()
            
            # Add nodes for each category
            pos = {}
            colors = []
            labels = {}
            
            # Frontend layer (top)
            y_frontend = 0.8
            for i, comp in enumerate(categories['frontend'][:5]):  # Limit to 5 for clarity
                node_id = f"fe_{i}"
                G.add_node(node_id)
                pos[node_id] = (0.2 + i * 0.15, y_frontend)
                colors.append(self.colors['secondary'])
                labels[node_id] = comp[:10]  # Truncate long names
            
            # API layer (middle-top)
            y_api = 0.6
            for i, comp in enumerate(categories['api'][:4]):
                node_id = f"api_{i}"
                G.add_node(node_id)
                pos[node_id] = (0.25 + i * 0.17, y_api)
                colors.append(self.colors['accent'])
                labels[node_id] = comp[:10]
            
            # Backend layer (middle-bottom)
            y_backend = 0.4
            for i, comp in enumerate(categories['backend'][:4]):
                node_id = f"be_{i}"
                G.add_node(node_id)
                pos[node_id] = (0.25 + i * 0.17, y_backend)
                colors.append(self.colors['primary'])
                labels[node_id] = comp[:10]
            
            # Data layer (bottom)
            y_data = 0.2
            for i, comp in enumerate(categories['data'][:3]):
                node_id = f"data_{i}"
                G.add_node(node_id)
                pos[node_id] = (0.3 + i * 0.2, y_data)
                colors.append(self.colors['success'])
                labels[node_id] = comp[:10]
            
            # Add edges to show flow
            nodes = list(G.nodes())
            for i in range(len(nodes) - 1):
                if nodes[i].startswith('fe_') and nodes[i+1].startswith('api_'):
                    G.add_edge(nodes[i], nodes[i+1])
                elif nodes[i].startswith('api_') and nodes[i+1].startswith('be_'):
                    G.add_edge(nodes[i], nodes[i+1])
                elif nodes[i].startswith('be_') and nodes[i+1].startswith('data_'):
                    G.add_edge(nodes[i], nodes[i+1])
            
            # Draw the graph
            nx.draw(G, pos, ax=ax, with_labels=True, labels=labels,
                   node_color=colors, node_size=2000, font_size=8, font_weight='bold',
                   arrows=True, arrowsize=20, edge_color='gray', width=2)
            
            # Add layer labels
            ax.text(0.05, 0.8, 'Frontend Layer', fontsize=12, fontweight='bold', 
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=self.colors['secondary'], alpha=0.7))
            ax.text(0.05, 0.6, 'API Layer', fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=self.colors['accent'], alpha=0.7))
            ax.text(0.05, 0.4, 'Backend Layer', fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=self.colors['primary'], alpha=0.7))
            ax.text(0.05, 0.2, 'Data Layer', fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=self.colors['success'], alpha=0.7))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"AI-Generated Architecture Flowchart - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        # Save diagram
        filename = f"ai_architecture_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'AI Architecture Flowchart',
            'description': f'AI-analyzed system architecture with {len(components)} components detected',
            'type': 'architecture',
            'filename': filename,
            'path': filepath,
            'metrics': {
                'components': len(components),
                'routes': len(routes),
                'layers': len([cat for cat in categories.values() if cat])
            }
        }
    
    def _create_user_journey_diagram(self, project_data, analysis):
        """Create AI-powered user journey flowchart"""
        fig, ax = plt.subplots(figsize=(16, 10))
        fig.patch.set_facecolor('white')
        
        user_journeys = analysis['user_journeys']
        
        if not user_journeys:
            # Create a default user journey based on components
            components = analysis['components']
            frontend_components = [name for name, info in components.items() 
                                 if info.get('category') == 'frontend' or info.get('type') == 'react_component']
            
            if frontend_components:
                user_journeys = [{
                    'name': 'Main User Flow',
                    'steps': ['User Entry', 'Navigation', 'Interaction', 'Result'],
                    'components': frontend_components[:3],
                    'type': 'detected'
                }]
        
        if not user_journeys:
            return self._create_simple_user_journey_diagram(project_data)
        
        # Create flowchart for each journey
        y_start = 0.9
        journey_height = 0.8 / len(user_journeys)
        
        for idx, journey in enumerate(user_journeys):
            y_pos = y_start - (idx * journey_height)
            
            # Journey title
            ax.text(0.05, y_pos - 0.05, journey['name'], fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor=self.colors['secondary'], alpha=0.8))
            
            steps = journey.get('steps', [])
            if steps:
                step_width = 0.8 / len(steps)
                
                for step_idx, step in enumerate(steps):
                    x_pos = 0.1 + (step_idx * step_width)
                    
                    # Create step box
                    box = patches.FancyBboxPatch(
                        (x_pos, y_pos - 0.15), step_width - 0.02, 0.08,
                        boxstyle="round,pad=0.01",
                        facecolor=self.colors['light'],
                        edgecolor=self.colors['primary'],
                        linewidth=2
                    )
                    ax.add_patch(box)
                    
                    # Add step text
                    ax.text(x_pos + (step_width - 0.02) / 2, y_pos - 0.11, step, 
                           ha='center', va='center', fontsize=9, fontweight='bold',
                           wrap=True)
                    
                    # Add arrow to next step
                    if step_idx < len(steps) - 1:
                        ax.annotate('', 
                                  xy=(x_pos + step_width, y_pos - 0.11),
                                  xytext=(x_pos + step_width - 0.02, y_pos - 0.11),
                                  arrowprops=dict(arrowstyle='->', lw=2, color=self.colors['primary']))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"AI-Detected User Journey Flowcharts - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        # Save diagram
        filename = f"user_journey_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'AI User Journey Flowcharts',
            'description': f'AI-detected user journeys with {len(user_journeys)} flows identified',
            'type': 'user_journey',
            'filename': filename,
            'path': filepath,
            'metrics': {
                'journeys_detected': len(user_journeys),
                'total_steps': sum(len(j.get('steps', [])) for j in user_journeys)
            }
        }
    
    def _create_data_flow_diagram(self, project_data, analysis):
        """Create AI-powered data flow diagram"""
        fig, ax = plt.subplots(figsize=(14, 12))
        fig.patch.set_facecolor('white')
        
        data_flows = analysis['data_flows']
        components = analysis['components']
        
        if not data_flows and not components:
            return self._create_simple_data_flow_diagram(project_data)
        
        if NETWORKX_AVAILABLE and data_flows:
            # Create directed graph for data flows
            G = nx.DiGraph()
            
            # Add nodes for components
            node_colors = []
            node_sizes = []
            labels = {}
            
            for flow in data_flows:
                from_node = flow.get('from', 'Unknown')
                to_node = flow.get('to', 'Unknown')
                
                # Add nodes if they don't exist
                if not G.has_node(from_node):
                    G.add_node(from_node)
                    labels[from_node] = from_node.split('/')[-1][:10]  # Short label
                
                if not G.has_node(to_node):
                    G.add_node(to_node)
                    labels[to_node] = to_node.split('/')[-1][:10]  # Short label
                
                # Add edge with flow type
                G.add_edge(from_node, to_node, 
                          type=flow.get('type', 'data_flow'),
                          method=flow.get('method', ''))
            
            # Set node colors based on type
            for node in G.nodes():
                if any(node in comp for comp in components.values()):
                    comp_info = next((info for name, info in components.items() if node in name), {})
                    if comp_info.get('category') == 'frontend':
                        node_colors.append(self.colors['secondary'])
                        node_sizes.append(3000)
                    elif comp_info.get('category') == 'data_model':
                        node_colors.append(self.colors['success'])
                        node_sizes.append(2500)
                    else:
                        node_colors.append(self.colors['primary'])
                        node_sizes.append(2000)
                elif '/api' in node or 'api' in node.lower():
                    node_colors.append(self.colors['accent'])
                    node_sizes.append(2500)
                else:
                    node_colors.append(self.colors['warning'])
                    node_sizes.append(1500)
            
            # Use spring layout for better visualization
            pos = nx.spring_layout(G, k=2, iterations=50)
            
            # Draw the graph
            nx.draw(G, pos, ax=ax, with_labels=True, labels=labels,
                   node_color=node_colors, node_size=node_sizes, 
                   font_size=8, font_weight='bold',
                   arrows=True, arrowsize=20, edge_color='gray', width=1.5)
            
            # Add legend
            legend_elements = [
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['secondary'], 
                          markersize=10, label='Frontend Components'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['accent'], 
                          markersize=10, label='API Endpoints'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['primary'], 
                          markersize=10, label='Backend Services'),
                plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=self.colors['success'], 
                          markersize=10, label='Data Models')
            ]
            ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1, 1))
            
        else:
            # Fallback: Create simple data flow representation
            ax.text(0.5, 0.7, "Data Flow Overview", ha='center', va='center', 
                   fontsize=18, fontweight='bold')
            
            flow_text = f"""
            Components Analyzed: {len(components)}
            Data Flows Detected: {len(data_flows)}
            
            Flow Types:
            • API Calls: {len([f for f in data_flows if f.get('type') == 'api_call'])}
            • Internal Flows: {len([f for f in data_flows if f.get('type') != 'api_call'])}
            """
            
            ax.text(0.5, 0.4, flow_text, ha='center', va='center', 
                   fontsize=12, bbox=dict(boxstyle="round,pad=0.5", facecolor=self.colors['light']))
        
        ax.set_xlim(-0.1, 1.1)
        ax.set_ylim(-0.1, 1.1)
        ax.set_title(f"AI-Generated Data Flow Diagram - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        # Save diagram
        filename = f"data_flow_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'AI Data Flow Diagram',
            'description': f'AI-analyzed data flows with {len(data_flows)} connections mapped',
            'type': 'data_flow',
            'filename': filename,
            'path': filepath,
            'metrics': {
                'data_flows': len(data_flows),
                'components_involved': len(set([f.get('from') for f in data_flows] + [f.get('to') for f in data_flows]))
            }
        }
    
    # Fallback methods for when AI analysis doesn't detect patterns
    
    def _create_simple_architecture_diagram(self, project_data):
        """Fallback simple architecture diagram"""
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        # Create basic 3-tier architecture
        layers = [
            {'name': 'Frontend Layer', 'color': self.colors['secondary'], 'y': 0.8},
            {'name': 'API/Service Layer', 'color': self.colors['accent'], 'y': 0.5},
            {'name': 'Data Layer', 'color': self.colors['primary'], 'y': 0.2}
        ]
        
        for layer in layers:
            # Create layer box
            box = patches.FancyBboxPatch(
                (0.2, layer['y'] - 0.1), 0.6, 0.15,
                boxstyle="round,pad=0.02",
                facecolor=layer['color'],
                alpha=0.7,
                edgecolor='black',
                linewidth=2
            )
            ax.add_patch(box)
            
            # Add layer label
            ax.text(0.5, layer['y'], layer['name'], 
                   ha='center', va='center', fontsize=14, fontweight='bold', color='white')
        
        # Add arrows between layers
        for i in range(len(layers) - 1):
            ax.annotate('', 
                      xy=(0.5, layers[i+1]['y'] + 0.05),
                      xytext=(0.5, layers[i]['y'] - 0.05),
                      arrowprops=dict(arrowstyle='<->', lw=3, color='black'))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"Basic Architecture - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        filename = f"simple_architecture_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'Basic Architecture',
            'description': 'Simple 3-tier architecture diagram',
            'type': 'architecture',
            'filename': filename,
            'path': filepath,
            'metrics': {'layers': 3}
        }
    
    def _create_simple_user_journey_diagram(self, project_data):
        """Fallback simple user journey diagram"""
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.patch.set_facecolor('white')
        
        # Generic user journey steps
        steps = [
            'User Entry',
            'Authentication',
            'Navigation',
            'Action/Input',
            'Processing',
            'Result/Feedback'
        ]
        
        step_width = 0.8 / len(steps)
        
        for idx, step in enumerate(steps):
            x_pos = 0.1 + (idx * step_width)
            
            # Create step circle
            circle = patches.Circle((x_pos + step_width/2, 0.5), 0.05, 
                                  facecolor=self.colors['secondary'], 
                                  edgecolor=self.colors['primary'], 
                                  linewidth=2)
            ax.add_patch(circle)
            
            # Add step label
            ax.text(x_pos + step_width/2, 0.35, step, 
                   ha='center', va='center', fontsize=9, fontweight='bold')
            
            # Add arrow to next step
            if idx < len(steps) - 1:
                ax.annotate('', 
                          xy=(x_pos + step_width + step_width/2 - 0.05, 0.5),
                          xytext=(x_pos + step_width/2 + 0.05, 0.5),
                          arrowprops=dict(arrowstyle='->', lw=2, color=self.colors['primary']))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"Generic User Journey - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        filename = f"simple_user_journey_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'Generic User Journey',
            'description': 'Standard user interaction flow',
            'type': 'user_journey',
            'filename': filename,
            'path': filepath,
            'metrics': {'steps': len(steps)}
        }
    
    def _create_simple_data_flow_diagram(self, project_data):
        """Fallback simple data flow diagram"""
        fig, ax = plt.subplots(figsize=(10, 8))
        fig.patch.set_facecolor('white')
        
        # Create basic data flow
        components = [
            {'name': 'User Input', 'pos': (0.2, 0.8), 'color': self.colors['secondary']},
            {'name': 'Frontend', 'pos': (0.5, 0.8), 'color': self.colors['secondary']},
            {'name': 'API Gateway', 'pos': (0.5, 0.6), 'color': self.colors['accent']},
            {'name': 'Business Logic', 'pos': (0.3, 0.4), 'color': self.colors['primary']},
            {'name': 'Database', 'pos': (0.7, 0.4), 'color': self.colors['success']},
            {'name': 'Response', 'pos': (0.5, 0.2), 'color': self.colors['warning']}
        ]
        
        # Draw components
        for comp in components:
            circle = patches.Circle(comp['pos'], 0.08, 
                                  facecolor=comp['color'], 
                                  alpha=0.7,
                                  edgecolor='black', 
                                  linewidth=2)
            ax.add_patch(circle)
            ax.text(comp['pos'][0], comp['pos'][1], comp['name'], 
                   ha='center', va='center', fontsize=9, fontweight='bold')
        
        # Draw data flow arrows
        flows = [
            (0, 1), (1, 2), (2, 3), (2, 4), (3, 5), (4, 5), (5, 1)
        ]
        
        for start_idx, end_idx in flows:
            start_pos = components[start_idx]['pos']
            end_pos = components[end_idx]['pos']
            
            ax.annotate('', 
                      xy=end_pos,
                      xytext=start_pos,
                      arrowprops=dict(arrowstyle='->', lw=2, color='gray'))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"Basic Data Flow - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        filename = f"simple_data_flow_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'Basic Data Flow',
            'description': 'Standard application data flow',
            'type': 'data_flow',
            'filename': filename,
            'path': filepath,
            'metrics': {'components': len(components)}
        }
    
    def _create_tech_stack_diagram(self, project_data, analysis):
        """Enhanced technology stack visualization"""
        fig, ax = plt.subplots(figsize=(12, 8))
        fig.patch.set_facecolor('white')
        
        dependencies = analysis.get('dependencies', {})
        files = project_data.get('files', [])
        
        # Detect technologies from file extensions and dependencies
        tech_stack = {
            'Frontend': set(),
            'Backend': set(),
            'Database': set(),
            'Tools': set()
        }
        
        # From file extensions
        for file_info in files:
            name = file_info.get('name', '')
            if name.endswith(('.js', '.jsx', '.ts', '.tsx')):
                tech_stack['Frontend'].add('JavaScript/React')
            elif name.endswith('.py'):
                tech_stack['Backend'].add('Python')
            elif name.endswith(('.sql', '.db')):
                tech_stack['Database'].add('SQL Database')
            elif name.endswith('.json'):
                tech_stack['Tools'].add('JSON Config')
        
        # From dependencies
        frontend_deps = dependencies.get('frontend', {})
        for dep in frontend_deps.keys():
            if 'react' in dep.lower():
                tech_stack['Frontend'].add('React')
            elif 'vue' in dep.lower():
                tech_stack['Frontend'].add('Vue.js')
            elif 'angular' in dep.lower():
                tech_stack['Frontend'].add('Angular')
            elif dep in ['axios', 'fetch']:
                tech_stack['Frontend'].add('HTTP Client')
        
        backend_deps = dependencies.get('backend', {})
        for dep in backend_deps.keys():
            if 'flask' in dep.lower():
                tech_stack['Backend'].add('Flask')
            elif 'django' in dep.lower():
                tech_stack['Backend'].add('Django')
            elif 'fastapi' in dep.lower():
                tech_stack['Backend'].add('FastAPI')
        
        # Create visualization
        y_positions = [0.8, 0.6, 0.4, 0.2]
        colors = [self.colors['secondary'], self.colors['primary'], self.colors['success'], self.colors['accent']]
        
        for idx, (category, techs) in enumerate(tech_stack.items()):
            if not techs:
                continue
                
            y_pos = y_positions[idx]
            color = colors[idx]
            
            # Category label
            ax.text(0.05, y_pos, category, fontsize=14, fontweight='bold',
                   bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.7))
            
            # Technology items
            x_start = 0.2
            for tech_idx, tech in enumerate(techs):
                x_pos = x_start + (tech_idx * 0.15)
                if x_pos > 0.9:  # Wrap to next line if too long
                    break
                    
                ax.text(x_pos, y_pos, tech, fontsize=10, 
                       bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.3))
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"Technology Stack Analysis - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        ax.axis('off')
        
        filename = f"tech_stack_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'Technology Stack',
            'description': f'Detected technologies across {len([cat for cat in tech_stack.values() if cat])} categories',
            'type': 'tech_stack',
            'filename': filename,
            'path': filepath,
            'metrics': {
                'categories': len([cat for cat in tech_stack.values() if cat]),
                'total_technologies': sum(len(techs) for techs in tech_stack.values())
            }
        }
    
    def _create_file_structure_diagram(self, project_data):
        """Keep existing file structure diagram (enhanced)"""
        fig, ax = plt.subplots(figsize=(10, 12))
        fig.patch.set_facecolor('white')
        
        files = project_data.get('files', [])
        
        if not files:
            ax.text(0.5, 0.5, "No files to analyze", ha='center', va='center', fontsize=16)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
        else:
            # Group files by directory structure
            file_tree = self._build_file_tree(files)
            self._draw_file_tree(ax, file_tree, 0.1, 0.9, 0)
        
        ax.set_title(f"File Structure - {project_data.get('title', 'Project')}", 
                    fontsize=16, fontweight='bold', pad=20)
        
        filename = f"file_structure_{int(time.time())}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.tight_layout()
        plt.savefig(filepath, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return {
            'title': 'File Structure',
            'description': f'Project structure with {len(files)} files',
            'type': 'file_structure',
            'filename': filename,
            'path': filepath,
            'metrics': {'total_files': len(files)}
        }
    
    def _build_file_tree(self, files):
        """Build a tree structure from file paths"""
        tree = {}
        for file_info in files:
            path_parts = file_info.get('name', '').split('/')
            current = tree
            for part in path_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        return tree
    
    def _draw_file_tree(self, ax, tree, x, y, level):
        """Recursively draw file tree"""
        indent = level * 0.05
        line_height = 0.03
        
        for idx, (name, subtree) in enumerate(tree.items()):
            current_y = y - (idx * line_height)
            
            # Draw file/folder icon and name
            icon = '📁' if subtree else '📄'
            ax.text(x + indent, current_y, f"{icon} {name}", 
                   fontsize=8, va='center')
            
            # Recursively draw subtree
            if subtree:
                self._draw_file_tree(ax, subtree, x, current_y - line_height, level + 1)
        
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')


# Singleton instance
diagram_service = DiagramService()