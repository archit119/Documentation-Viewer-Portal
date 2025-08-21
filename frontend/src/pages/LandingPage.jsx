import React, { useState, useEffect } from 'react';
import DocumentationViewer from '../components/features/DocumentationViewer';
import JSZip from 'jszip';

// Add this style block
const floatingStyles = `
  @keyframes float {
    0%, 100% { transform: translateY(0px) rotate(0deg); }
    33% { transform: translateY(-10px) rotate(1deg); }
    66% { transform: translateY(5px) rotate(-1deg); }
  }
  
  .floating-badge {
    animation: float 6s ease-in-out infinite;
  }
  
  .floating-badge-delayed {
    animation: float 6s ease-in-out infinite;
    animation-delay: 2s;
  }
`;

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style');
  styleSheet.textContent = floatingStyles;
  document.head.appendChild(styleSheet);
}



// NEW (memory-based)
// Backend-connected ProjectService
class ProjectService {
  constructor() {
    this.baseURL = 'http://localhost:5000/api';
    this.token = localStorage.getItem('auth_token');
    this.userRole = localStorage.getItem('user_role');
    this.documentationService = 'documentation_service'; // Reference to backend service
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  setUserRole(role) {
    this.userRole = role;
    if (role) {
      localStorage.setItem('user_role', role);
    } else {
      localStorage.removeItem('user_role');
    }
  }

  getUserRole() {
    return this.userRole;
  }

  isAdmin() {
    return this.userRole === 'admin';
  }

  getHeaders() {
    return {
      'Content-Type': 'application/json',
      ...(this.token && { 'Authorization': `Bearer ${this.token}` })
    };
  }

  async loadProjects() {
  try {
    console.log('🔍 Loading projects with headers:', this.getHeaders());
    const response = await fetch(`${this.baseURL}/projects`, {
      headers: this.getHeaders()
    });
    console.log('📡 Response status:', response.status);
    
    // If no token and we get 401, return empty array for guest mode
    if (response.status === 401 && !this.token) {
      console.log('👥 Guest mode: No projects available');
      return [];
    }
    
    const data = await response.json();
    console.log('📦 Response data:', data);
    
    if (data.success) {
      console.log('✅ Projects loaded successfully:', data.data);
      console.log('📊 Number of projects:', data.data.length);
      return data.data;
    } else {
      console.log('❌ API returned success: false');
      return [];
    }
  } catch (error) {
    console.error('💥 Failed to load projects:', error);
    return [];
  }
}

  async getAllProjects() {
    return await this.loadProjects();
  }

  async createProject(projectData) {
    try {
      const formData = new FormData();
      formData.append('title', projectData.title);
      formData.append('description', projectData.description || '');
      
      projectData.files.forEach(fileObj => {
        formData.append('files', fileObj.file);
      });

      const response = await fetch(`${this.baseURL}/projects`, {
        method: 'POST',
        headers: {
          ...(this.token && { 'Authorization': `Bearer ${this.token}` })
        },
        body: formData
      });

      const data = await response.json();
      if (data.success) {
        this.emitProjectUpdate(data.data.id, 'created');
        
        // Start polling for this specific project
        this.startProjectPolling(data.data.id);
        
        return data.data;
      } else {
        throw new Error(data.error || 'Failed to create project');
      }
    } catch (error) {
      console.error('Failed to create project:', error);
      throw error;
    }
  }

  startProjectPolling(projectId) {
    const pollProject = async () => {
      try {
        const response = await fetch(`${this.baseURL}/projects/${projectId}`, {
          headers: this.getHeaders()
        });
        const data = await response.json();
        
        if (data.success && data.data.status !== 'processing') {
          // Project completed or failed, emit update and stop polling
          this.emitProjectUpdate(projectId, 'updated');
          return;
        }
        
        // Continue polling if still processing
        setTimeout(pollProject, 2000);
        this.emitProjectUpdate(projectId, 'updated');
      } catch (error) {
        console.error('Failed to poll project:', error);
        // Retry after a longer delay on error
        setTimeout(pollProject, 5000);
      }
    };

    // Start polling after a short delay
    setTimeout(pollProject, 2000);
  }

  async deleteProject(projectId) {
  try {
    console.log('🗑️ Deleting project:', projectId);
    
    const response = await fetch(`${this.baseURL}/projects/${projectId}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success) {
        console.log('✅ Project deleted successfully');
        this.emitProjectUpdate(projectId, 'deleted');
        return true;
      } else {
        throw new Error(data.error || 'Failed to delete project');
      }
    } else {
      const errorText = await response.text();
      throw new Error(`Delete failed: ${response.status} - ${errorText}`);
    }
  } catch (error) {
    console.error('❌ Failed to delete project:', error);
    throw error;
  }
}

  async exportProject(projectId) {
    try {
      const response = await fetch(`${this.baseURL}/projects/${projectId}/export`, {
        headers: this.getHeaders()
      });
      
      const data = await response.json();
      if (data.success) {
        const blob = new Blob([JSON.stringify(data.data, null, 2)], {
          type: 'application/json'
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${data.data.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_documentation.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('Failed to export project:', error);
      throw error;
    }
  }

  emitProjectUpdate(projectId, type) {
    const event = new CustomEvent('projectUpdate', {
      detail: { projectId, type }
    });
    window.dispatchEvent(event);
  }
}

const projectService = new ProjectService();

// Add these two components to your existing LandingPage.jsx file

// Login Page Component
function LoginPage({ onLogin, onSwitchToRegister, isLoading }) {
  const [formData, setFormData] = useState({
    email: '',
    password: ''
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (!formData.email.trim() || !formData.password.trim()) {
      setError('Please fill in all fields');
      return;
    }

    try {
      await onLogin(formData);
    } catch (error) {
      setError(error.message || 'Login failed');
    }
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ 
        background: 'linear-gradient(135deg, #2C1810 0%, #3D2417 25%, #5D3A25 50%, #8B5A3C 75%, #F5F5F5 100%)'
      }}
    >
      {/* Background Elements */}
      <div className="absolute inset-0">
        <div className="absolute top-20 left-20 w-72 h-72 rounded-full bg-orange-500/15 blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-96 h-96 rounded-full bg-orange-400/10 blur-3xl"></div>
        <div className="absolute top-1/2 left-1/4 w-64 h-64 rounded-full bg-white/10 blur-2xl"></div>
        <div className="absolute bottom-1/3 right-1/3 w-80 h-80 rounded-full bg-orange-600/10 blur-3xl"></div>
      </div>
      <div className="relative z-10 w-full max-w-md mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-8">
          <img 
            src="/images/mashreq-logo.png" 
            alt="Mashreq Logo" 
            className="w-64 h-64 mx-auto mb-4 object-contain"
          />
          <h1 className="text-3xl font-bold text-white mb-2">Welcome Back</h1>
          <p className="text-white/70">Sign in to your Mashreq Docs account</p>
        </div>

        {/* Login Form */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl">
          <div className="space-y-6">
            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                  </svg>
                </div>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-xl hover:shadow-lg transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Signing In...
                </div>
              ) : (
                'Sign In'
              )}
            </button>

            {/* Admin Access Only */}
            <div className="text-center">
              <p className="text-white/70 text-sm">
                Admin access required for project management
              </p>
              <p className="text-white/60 text-xs mt-1">
                Contact administrator for credentials
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Register Page Component
function RegisterPage({ onRegister, onSwitchToLogin, isLoading }) {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    // Validation
    if (!formData.name.trim() || !formData.email.trim() || !formData.password.trim() || !formData.confirmPassword.trim()) {
      setError('Please fill in all fields');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters long');
      return;
    }

    try {
      await onRegister({
        name: formData.name,
        email: formData.email,
        password: formData.password
      });
    } catch (error) {
      setError(error.message || 'Registration failed');
    }
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center relative overflow-hidden"
      style={{ 
        background: 'linear-gradient(135deg, #0F1419 0%, #1A2332 25%, #2D4A6B 50%, #4A7C9D 75%, #E8F4F8 100%)'
      }}
    >
      {/* Background Elements */}
      <div className="absolute inset-0">
        <div className="absolute top-20 left-20 w-72 h-72 rounded-full bg-orange-500/10 blur-3xl"></div>
        <div className="absolute bottom-20 right-20 w-96 h-96 rounded-full bg-blue-500/10 blur-3xl"></div>
      </div>

      <div className="relative z-10 w-full max-w-md mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center" 
               style={{ backgroundColor: '#F58220', boxShadow: '0 4px 20px rgba(245,130,32,0.3)' }}>
            <div className="text-white font-bold text-2xl">M</div>
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Create Account</h1>
          <p className="text-white/70">Join Mashreq Docs and start documenting</p>
        </div>

        {/* Register Form */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-8 border border-white/20 shadow-2xl">
          <div className="space-y-6">
            {/* Name Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                </div>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="John Doe"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Email Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Email Address
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                  </svg>
                </div>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="you@example.com"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                  </svg>
                </div>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Confirm Password Field */}
            <div>
              <label className="block text-sm font-medium text-white/90 mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <input
                  type="password"
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/20 border border-red-500/30 rounded-xl p-4">
                <div className="flex items-center">
                  <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-red-200 text-sm">{error}</p>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <button
              onClick={handleSubmit}
              disabled={isLoading}
              className="w-full py-3 px-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-xl hover:shadow-lg transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {isLoading ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Creating Account...
                </div>
              ) : (
                'Create Account'
              )}
            </button>

            {/* Switch to Login */}
            <div className="text-center">
              <p className="text-white/70 text-sm">
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={onSwitchToLogin}
                  className="text-orange-400 hover:text-orange-300 font-medium transition-colors"
                  disabled={isLoading}
                >
                  Sign In
                </button>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Toggle Switch Component
function ToggleSwitch({ isOn, handleToggle }) {
  return (
    <div
      onClick={handleToggle}
      className={`w-14 h-7 flex items-center rounded-full p-1 cursor-pointer transition-all duration-300 shadow-inner ${
        isOn ? 'bg-white/20 border border-white/30' : 'bg-black/10 border border-black/20'
      }`}
    >
      <div
        className={`w-5 h-5 rounded-full shadow-lg transform duration-300 ease-in-out ${
          isOn ? 'translate-x-7' : ''
        }`}
        style={{ 
          backgroundColor: isOn ? '#F58220' : '#FFFFFF',
          boxShadow: isOn ? '0 4px 12px rgba(245,130,32,0.3)' : '0 2px 8px rgba(0,0,0,0.15)'
        }}
      />
    </div>
  );
}

// Project Creation Modal Component
function ProjectCreationModal({ isOpen, onClose, onCreateProject }) {
  const [projectData, setProjectData] = useState({
    title: '',
    description: '',
    files: []
  });
  const [dragActive, setDragActive] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isExtractingZip, setIsExtractingZip] = useState(false);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileInput = (e) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files));
    }
  };

  // ZIP file extraction function
const extractZipFile = async (zipFile) => {
  setIsExtractingZip(true);
  try {
    const zip = new JSZip();
    const zipContent = await zip.loadAsync(zipFile);
    const extractedFiles = [];
    
 const supportedExtensions = new Set([
  'js','jsx','ts','tsx','py','java','cpp','c','cs','php','rb',
  'go','rs','swift','kt','scala','html','css','scss','json',
  'xml','yaml','yml','md','txt','sql','sh','bat',
  // ✅ allow docs inside ZIPs
  'pdf','docx','ppt','pptx'
]);

    
    for (const [fileName, fileData] of Object.entries(zipContent.files)) {
      // Skip directories, hidden files, and system files
      if (fileData.dir || 
          fileName.startsWith('.') || 
          fileName.includes('__MACOSX') ||
          fileName.includes('node_modules') ||
          fileName.includes('.git/')) {
        continue;
      }
      
      const ext = fileName.toLowerCase().split('.').pop();
      if (!supportedExtensions.has(ext)) {
        continue;
      }
      
      // Skip files larger than 1MB
      if (fileData._data && fileData._data.uncompressedSize > 1024 * 1024) {
        console.warn(`Skipping large file: ${fileName}`);
        continue;
      }
      
      try {
        const content = await fileData.async('text');
        const extractedFile = new File([content], fileName, {
          type: 'text/plain',
          lastModified: Date.now()
        });
        
        extractedFiles.push({
          id: Date.now() + Math.random() + extractedFiles.length,
          file: extractedFile,
          name: fileName,
          size: content.length,
          type: 'text/plain'
        });
      } catch (fileError) {
        console.warn(`Failed to extract ${fileName}:`, fileError);
      }
    }
    
    if (extractedFiles.length === 0) {
      throw new Error('No supported code files found in ZIP archive');
    }
    
    return extractedFiles;
  } finally {
    setIsExtractingZip(false);
  }
};

  const handleFiles = async (newFiles) => {
  setErrorMessage('');
  
  const processedFiles = [];
  let hasZipFiles = false;
  
  for (const file of newFiles) {
    if (file.name.toLowerCase().endsWith('.zip')) {
      hasZipFiles = true;
      try {
        const extractedFiles = await extractZipFile(file);
        processedFiles.push(...extractedFiles);
      } catch (error) {
        setErrorMessage(`Failed to extract ${file.name}: ${error.message}`);
        return;
      }
    } else {
      // Handle regular files
      const ext = file.name.toLowerCase().split('.').pop();
      const supportedExtensions = [
  'js','jsx','ts','tsx','py','java','cpp','c','cs','php','rb','go','rs','swift','kt','scala',
  'html','css','scss','json','xml','yaml','yml','md','txt','sql','sh','bat',
  // ✅ allow direct upload of docs
  'pdf','docx','ppt','pptx'
];
      
      if (supportedExtensions.includes(ext)) {
        processedFiles.push({
          id: Date.now() + Math.random(),
          file,
          name: file.name,
          size: file.size,
          type: file.type
        });
      }
    }
  }
  
  if (processedFiles.length === 0) {
    setErrorMessage('No supported code files found. Please upload code files or ZIP archives containing code files.');
    return;
  }
  
  setProjectData(prev => ({
    ...prev,
    files: [...prev.files, ...processedFiles]
  }));
  
  if (hasZipFiles && processedFiles.length > 0) {
    setErrorMessage(`Successfully extracted ${processedFiles.length} files from ZIP archive(s).`);
    setTimeout(() => setErrorMessage(''), 3000);
  }
};

  const removeFile = (fileId) => {
    setProjectData(prev => ({
      ...prev,
      files: prev.files.filter(f => f.id !== fileId)
    }));
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!projectData.title.trim()) {
      setErrorMessage('Project title is required');
      return;
    }

    if (projectData.files.length === 0) {
      setErrorMessage('Please upload at least one file');
      return;
    }

    setIsProcessing(true);

    try {
      await onCreateProject(projectData);
      setProjectData({ title: '', description: '', files: [] });
      setIsProcessing(false);
      onClose();
    } catch (error) {
      setErrorMessage('Failed to create project: ' + error.message);
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 rounded-t-3xl">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-gray-900">Create New Project</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              disabled={isProcessing}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Project Details */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Project Title *
              </label>
              <input
                type="text"
                value={projectData.title}
                onChange={(e) => setProjectData(prev => ({ ...prev, title: e.target.value }))}
                placeholder="Enter project name..."
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors"
                disabled={isProcessing}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Project Description
              </label>
              <textarea
                value={projectData.description}
                onChange={(e) => setProjectData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Describe your project, its purpose, key features, and any important details..."
                rows={4}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-orange-500 focus:border-orange-500 transition-colors resize-none"
                disabled={isProcessing}
              />
            </div>
          </div>

          {/* File Upload */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Upload Code Files *
            </label>
            <div
              className={`relative border-2 border-dashed rounded-xl p-8 transition-all duration-300 ${
                dragActive 
                  ? 'border-orange-400 bg-orange-50' 
                  : 'border-gray-300 bg-gray-50 hover:bg-gray-100'
              } ${isProcessing ? 'opacity-50 pointer-events-none' : ''}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <input
                type="file"
                multiple
                onChange={handleFileInput}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept="
    .js,.jsx,.ts,.tsx,.py,.java,.cpp,.c,.cs,.php,.rb,.go,.rs,.swift,.kt,.scala,
    .html,.css,.scss,.json,.xml,.yaml,.yml,.md,.txt,.sql,.sh,.bat,
    .zip,
    .pdf,.docx,.ppt,.pptx
  "
                disabled={isProcessing}
              />
              
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-orange-100 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {dragActive ? 'Drop your files here' : 'Upload your code files'}
                </h3>
                <p className="text-gray-600 text-sm">
                  Drag and drop files or click to browse
                </p>
                  <p className="text-gray-500 text-xs mt-2">
                    Supported: Code files, PDFs, PowerPoint, Images (JPG, PNG, etc.), ZIP archives, and more
                  </p>
              </div>
            </div>
          </div>

          {/* Processing indicator for ZIP extraction */}
          {isExtractingZip && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center">
                <svg className="animate-spin w-5 h-5 text-blue-600 mr-2" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <p className="text-blue-700 text-sm">Extracting files from ZIP archive...</p>
              </div>
            </div>
          )}

          {/* Uploaded Files List */}
          {projectData.files.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-700 mb-3">
                Uploaded Files ({projectData.files.length})
              </h3>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {projectData.files.map(file => (
                  <div key={file.id} className="flex items-center justify-between bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                        <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{file.name}</p>
                        <p className="text-gray-500 text-xs">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => removeFile(file.id)}
                      className="text-red-400 hover:text-red-600 transition-colors"
                      disabled={isProcessing}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Error Message */}
          {errorMessage && (
  <div className={`border rounded-lg p-4 ${
    errorMessage.includes('Successfully') 
      ? 'bg-green-50 border-green-200' 
      : 'bg-red-50 border-red-200'
  }`}>
    <div className="flex items-center">
      <svg className={`w-5 h-5 mr-2 ${
        errorMessage.includes('Successfully') 
          ? 'text-green-400' 
          : 'text-red-400'
      }`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={
          errorMessage.includes('Successfully')
            ? "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            : "M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        } />
      </svg>
      <p className={`text-sm ${
        errorMessage.includes('Successfully') 
          ? 'text-green-700' 
          : 'text-red-700'
      }`}>{errorMessage}</p>
    </div>
  </div>
)}

          {/* Action Buttons */}
          <div className="flex items-center justify-end space-x-4 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              disabled={isProcessing}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isProcessing || !projectData.title.trim() || projectData.files.length === 0}
              className="px-8 py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium rounded-xl hover:shadow-lg transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
            >
              {isProcessing ? 'Creating Project...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Project View Modal Component
function ProjectViewModal({ project, isOpen, onClose, onDelete, onExport, isAdmin }) {
  const [activeTab, setActiveTab] = useState('documentation');
  const [isDeleting, setIsDeleting] = useState(false);
  const [currentProject, setCurrentProject] = useState(project);

  // Poll for updates if project is processing
  useEffect(() => {
    if (!isOpen || !project || project.status !== 'processing') return;

    const pollProject = async () => {
      try {
        const response = await fetch(`http://localhost:5000/api/projects/${project.id}`, {
          headers: {
            'Content-Type': 'application/json',
            ...(projectService.token && { 'Authorization': `Bearer ${projectService.token}` })
          }
        });
        const data = await response.json();
        
        if (data.success) {
          setCurrentProject(data.data);
          
          // Stop polling if project is no longer processing
          if (data.data.status !== 'processing') {
            return;
          }
        }
      } catch (error) {
        console.error('Failed to poll project:', error);
      }
    };

    const interval = setInterval(pollProject, 2000);
    return () => clearInterval(interval);
  }, [isOpen, project?.id, project?.status]);

  // Update current project when prop changes
  useEffect(() => {
    setCurrentProject(project);
  }, [project]);

  if (!isOpen || !currentProject) return null;

  // Use currentProject instead of project in the rest of the component

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete "${currentProject.title}"? This action cannot be undone.`)) {
      setIsDeleting(true);
      try {
        await onDelete(currentProject.id);
        onClose();
      } catch (error) {
        alert('Failed to delete project: ' + error.message);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const handleExport = () => {
    try {
      onExport(currentProject.id);
    } catch (error) {
      alert('Failed to export project: ' + error.message);
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      alert('Documentation copied to clipboard!');
    } catch (error) {
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      alert('Documentation copied to clipboard!');
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      completed: 'bg-green-100 text-green-800 border-green-200',
      processing: 'bg-orange-100 text-orange-800 border-orange-200',
      error: 'bg-red-100 text-red-800 border-red-200'
    };

    const labels = {
      completed: 'Completed',
      processing: 'Processing',
      error: 'Error'
    };

    return (
      <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium border ${styles[status] || 'bg-gray-100 text-gray-800 border-gray-200'}`}>
        {status === 'processing' && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        )}
        {labels[status] || 'Unknown'}
      </span>
    );
  };

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-orange-50">
          <div className="flex-1">
            <div className="flex items-center space-x-4 mb-2">
              <h2 className="text-2xl font-bold text-gray-900">{project.title}</h2>
              {getStatusBadge(project.status)}
            </div>
            <p className="text-gray-600">{project.description || 'No description provided'}</p>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
  <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
  <span>•</span>
  <span>Files: {project.files_count}</span>
</div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors ml-4"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Progress Bar (if processing) */}
        {project.status === 'processing' && (
          <div className="px-6 py-4 bg-orange-50 border-b border-orange-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-orange-800">
                {project.statusMessage || 'Processing project...'}
              </span>
              <span className="text-sm text-orange-600">{project.progress || 0}%</span>
            </div>
            <div className="w-full bg-orange-200 rounded-full h-2">
              <div 
                className="bg-orange-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${project.progress || 0}%` }}
              ></div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b border-gray-200 bg-gray-50">
          <button
            onClick={() => setActiveTab('documentation')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'documentation'
                ? 'text-orange-600 border-b-2 border-orange-600 bg-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Documentation
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'files'
                ? 'text-orange-600 border-b-2 border-orange-600 bg-white'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Files ({project.files_count})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {activeTab === 'documentation' && (
            <div className="p-6">
              {project.status === 'completed' && project.documentation ? (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Generated Documentation</h3>
                    <button
                      onClick={() => copyToClipboard(project.documentation)}
                      className="flex items-center space-x-2 px-4 py-2 bg-orange-100 text-orange-700 rounded-lg hover:bg-orange-200 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                      </svg>
                      <span>Copy</span>
                    </button>
                  </div>
                  <div className="bg-white rounded-lg border border-gray-200 p-6 prose prose-lg max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-gray-800">
                      {project.documentation}
                    </pre>
                  </div>
                </div>
              ) : project.status === 'error' ? (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Documentation Generation Failed</h3>
                  <p className="text-gray-600 mb-4">{project.error || 'An unknown error occurred'}</p>
                  <p className="text-sm text-gray-500">Please try creating the project again.</p>
                </div>
              ) : (
                <div className="text-center py-12">
                  <div className="w-16 h-16 mx-auto mb-4 bg-orange-100 rounded-full flex items-center justify-center">
                    <svg className="animate-spin w-8 h-8 text-orange-600" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">Generating Documentation</h3>
                  <p className="text-gray-600">AI is analyzing your code and generating comprehensive documentation...</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'files' && (
            <div className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Project Files</h3>
              <div className="space-y-2">
                {(project.file_names || []).map((fileName, index) => (
                  <div key={index} className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                      <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <span className="font-medium text-gray-900">{fileName}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex space-x-3">
            {/* Delete button - Admin only */}
            {isAdmin && (
              <button
                onClick={handleDelete}
                disabled={isDeleting}
                className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isDeleting ? (
                  <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                )}
                <span>{isDeleting ? 'Deleting...' : 'Delete'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Main Project Dashboard Component
function ProjectDashboard({ onBack, onNewProject, isAdmin, setShowDocumentation, setDocumentationProject }) {
  const [projects, setProjects] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grid');
  const [selectedProject, setSelectedProject] = useState(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         (project.description || '').toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || project.status === selectedFilter;
    return matchesSearch && matchesFilter;
  });

const handleViewProject = async (project) => {
  console.log('🔥 Opening project:', project?.id);
  
  if (!project || !project.id) {
    console.error('⚠️ Invalid project data:', project);
    alert('Invalid project data. Please try refreshing the page.');
    return;
  }
  
  try {
    // Fetch fresh project data to ensure we have the latest
    const response = await fetch(`http://localhost:5000/api/projects/${project.id}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(projectService?.token && { 'Authorization': `Bearer ${projectService.token}` })
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.success && data.data) {
        console.log('✅ Fresh project data loaded');
        console.log('🔍 Fresh project generation_metadata:', data.data.generation_metadata ? 'Present' : 'Missing');
        setDocumentationProject(data.data);
        setShowDocumentation(true);
      } else {
        throw new Error('Failed to load project data');
      }
    } else if (response.status === 404) {
      alert('This project no longer exists. It may have been deleted.');
      // Refresh the projects list
      window.location.reload();
    } else {
      throw new Error(`Server error: ${response.status}`);
    }
  } catch (error) {
    console.error('⚠️ Failed to load project:', error);
    alert('Failed to load project. Please try again or refresh the page.');
  }
};

  const handleDeleteProject = async (projectId) => {
    await projectService.deleteProject(projectId);
  };

  const handleExportProject = (projectId) => {
    projectService.exportProject(projectId);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'processing': return 'bg-orange-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'processing': return 'Processing';
      case 'error': return 'Error';
      default: return 'Unknown';
    }
  };

  useEffect(() => {
  // Load projects on mount
  const loadProjects = async () => {
    try {
      console.log('🎯 Dashboard: Loading projects...');
      const projectsData = await projectService.getAllProjects();
      console.log('🎯 Dashboard: Received', projectsData.length, 'projects');
      
      // Filter out any invalid projects
      const validProjects = projectsData.filter(project => 
        project && 
        project.id && 
        project.title &&
        typeof project.id === 'string'
      );
      
      if (validProjects.length !== projectsData.length) {
        console.warn('⚠️ Filtered out', projectsData.length - validProjects.length, 'invalid projects');
      }
      
      setProjects(validProjects);
      return validProjects;
    } catch (error) {
      console.error('💥 Dashboard: Failed to load projects:', error);
      setProjects([]);
      return [];
    }
  };

    // Set up smart polling for processing projects
    let pollInterval;
    
    const startPolling = () => {
      if (pollInterval) clearInterval(pollInterval);
      
      pollInterval = setInterval(async () => {
        try {
          const projectsData = await projectService.getAllProjects();
          const hasProcessingProjects = projectsData.some(p => p.status === 'processing');
          
          setProjects(projectsData);
          
          // Stop polling if no processing projects
          if (!hasProcessingProjects) {
            clearInterval(pollInterval);
            console.log('No processing projects, stopping poll');
          }
        } catch (error) {
          console.error('Failed to poll projects:', error);
        }
      }, 2000);
    };

    // Initialize projects and start polling if needed
    const initializeProjects = async () => {
      const initialProjectsData = await loadProjects();
      if (initialProjectsData.some(p => p.status === 'processing')) {
        startPolling();
      }
    };

    // Listen for project updates
    const handleProjectUpdate = async (event) => {
      try {
        const { type, projectId } = event.detail;
        
        if (type === 'deleted') {
          // Remove project from state immediately
          setProjects(prev => prev.filter(p => p.id !== projectId));
        } else {
          // Refresh all projects for other updates
          const projectsData = await projectService.getAllProjects();
          setProjects(projectsData);
          
          // Restart polling if a new project is processing
          if (type === 'created') {
            const hasProcessingProjects = projectsData.some(p => p.status === 'processing');
            if (hasProcessingProjects) {
              startPolling();
            }
          }
        }
      } catch (error) {
        console.error('Failed to refresh projects:', error);
      }
    };

    // Start initialization
    initializeProjects();

    window.addEventListener('projectUpdate', handleProjectUpdate);
    
    return () => {
      if (pollInterval) clearInterval(pollInterval);
      window.removeEventListener('projectUpdate', handleProjectUpdate);
    };
  }, []);

  return (
    <div 
      className="min-h-screen relative overflow-hidden"
      style={{ 
        background: 'linear-gradient(135deg, #2C1810 0%, #3D2417 25%, #5D3A25 50%, #8B5A3C 75%, #F5F5F5 100%)'
      }}
    >
      {/* Header */}
      <header className="relative z-10 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 md:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-4">
              <img 
                src="/images/mashreq-logo.png" 
                alt="Mashreq Logo" 
                className="w-16 h-16 object-contain"
              />
            </div>
              <div className="text-3xl font-bold text-white tracking-tight">
                
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="text-white/70 hover:text-white transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-8 py-8">
        {/* Dashboard Header */}
        <div className="mb-8">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
                AI Documentation Portal
              </h1>
              <p className="text-xl text-white/80 max-w-2xl">
  {projectService.token && isAdmin 
    ? 'Manage your documentation projects, track progress, and collaborate with your team.'
    : projectService.token && !isAdmin
    ? 'View and explore documentation projects created by your team.'
    : 'Browse available documentation projects. Login as admin to create and manage projects.'
  }
</p>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* User Role Badge */}
<div className="flex items-center space-x-2 px-4 py-2 bg-white/10 backdrop-blur-xl rounded-xl border border-white/20">
  <div className={`w-2 h-2 rounded-full ${
  projectService.token && projectService.getUserRole() === 'admin' ? 'bg-orange-500' : 
  projectService.token && projectService.getUserRole() === 'user' ? 'bg-green-500' : 
  'bg-blue-500'
}`}></div>
  <span className="text-white/90 text-sm font-medium">
  {projectService.token && projectService.getUserRole() === 'admin' ? 'Administrator' : 
   projectService.token && projectService.getUserRole() === 'user' ? 'User' : 
   'Guest Viewer'}
</span>
</div>

              {/* New Project Button - Admin Only */}
              {isAdmin && (
                <button
                  onClick={onNewProject}
                  className="group relative px-8 py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-2xl transition-all duration-300 hover:shadow-2xl hover:shadow-orange-500/25 transform hover:scale-105 hover:-translate-y-1"
                  style={{ boxShadow: '0 10px 30px rgba(245,130,32,0.3)' }}
                >
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <span className="relative z-10">New Project</span>
                  </div>
                </button>
              )}

              {/* Read-only notice for users */}
              {!isAdmin && (
                <div className="px-4 py-2 bg-orange-500/20 backdrop-blur-xl rounded-xl border border-orange-500/30">
                  <div className="flex items-center space-x-2">
                    <svg className="w-4 h-4 text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <span className="text-blue-200 text-sm">View Only Access</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 border border-white/20 mb-8">
          <div className="flex flex-col lg:flex-row gap-4 lg:items-center lg:justify-between">
            <div className="flex-1 max-w-md">
              <div className="relative">
                <svg className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 transition-all duration-300"
                />
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              <select 
                value={selectedFilter}
                onChange={(e) => setSelectedFilter(e.target.value)}
                className="px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-orange-500/50 appearance-none cursor-pointer"
              >
                <option value="all">All Projects</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="error">Error</option>
              </select>
              
              <div className="flex items-center bg-white/10 rounded-xl border border-white/20 p-1">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-2 rounded-lg transition-colors duration-300 ${
                    viewMode === 'grid' ? 'bg-orange-500 text-white' : 'text-white/60 hover:text-white'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
                  </svg>
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-2 rounded-lg transition-colors duration-300 ${
                    viewMode === 'list' ? 'bg-orange-500 text-white' : 'text-white/60 hover:text-white'
                  }`}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Projects Grid */}
        {filteredProjects.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-24 h-24 mx-auto mb-6 bg-white/10 rounded-full flex items-center justify-center">
              <svg className="w-12 h-12 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 className="text-2xl font-bold text-white mb-2">
              {searchQuery || selectedFilter !== 'all' ? 'No projects found' : 'No projects yet'}
            </h3>
            <p className="text-white/70 mb-6 max-w-md mx-auto">
              {searchQuery || selectedFilter !== 'all' 
                ? 'Try adjusting your search or filter criteria'
                : 'Get started by creating your first documentation project'
              }
            </p>
            {!searchQuery && selectedFilter === 'all' && isAdmin && (
              <button
                onClick={onNewProject}
                className="px-8 py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-2xl hover:shadow-xl transition-all duration-300 transform hover:scale-105"
              >
                Create Your First Project
              </button>
            )}
            {!searchQuery && selectedFilter === 'all' && !isAdmin && (
              <div className="text-center">
                <p className="text-white/70 text-sm">Contact administrator to create projects</p>
              </div>
            )}
          </div>
        ) : (
          // In your ProjectDashboard component, find this part:
<div className={`grid gap-6 ${viewMode === 'grid' ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3' : 'grid-cols-1'}`}>
  {filteredProjects.map(project => (
    <div
      key={project.id}
      onClick={() => handleViewProject(project)}
      className="group bg-white/10 backdrop-blur-xl rounded-3xl p-6 border border-white/20 hover:border-white/40 transition-all duration-300 hover:transform hover:scale-105 hover:shadow-2xl cursor-pointer"
      style={{ boxShadow: '0 10px 30px rgba(0,0,0,0.1)' }}
    >
      {/* Add admin controls at the top */}
      {isAdmin && (
        <div className="flex justify-end mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          <button
            onClick={(e) => {
              e.stopPropagation(); // Prevent card click
              if (window.confirm(`Are you sure you want to delete "${project.title}"? This action cannot be undone.`)) {
                handleDeleteProject(project.id);
              }
            }}
            className="p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
            title="Delete Project"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      )}
      
      {/* Rest of your existing card content */}
      <div 
        onClick={() => handleViewProject(project)}
        className="cursor-pointer"
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold bg-orange-600">
              {project.title.slice(0, 2).toUpperCase()}
            </div>
            <div>
              <h3 className="font-bold text-white text-lg group-hover:text-orange-300 transition-colors duration-300">
                {project.title}
              </h3>
              <div className="flex items-center space-x-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${getStatusColor(project.status)}`}></div>
                <span className="text-xs text-white/60">{getStatusText(project.status)}</span>
              </div>
            </div>
          </div>
          
          <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </div>
        
        <p className="text-white/70 text-sm mb-4 line-clamp-2">
          {project.description || 'No description provided'}
        </p>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between text-sm text-white/60">
            <span>{project.files_count} files</span>
            <span>{new Date(project.updated_at).toLocaleDateString()}</span>
          </div>
          
          {project.status === 'processing' && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-white/70">Progress</span>
                <span className="text-white font-medium">{project.progress || 0}%</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div 
                  className="h-2 rounded-full bg-gradient-to-r from-orange-500 to-orange-600 transition-all duration-500"
                  style={{ width: `${project.progress || 0}%` }}
                ></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  ))}
</div>
        )}

        {/* Quick Stats */}
{/* Quick Stats */}
{projects.length > 0 && (
  <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-12">
    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20 text-center">
      <div className="text-3xl font-bold text-white mb-2">{projects.length}</div>
      <div className="text-white/70 text-sm">Total Projects</div>
    </div>
    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20 text-center">
      <div className="text-3xl font-bold text-orange-400 mb-2">
        {projects.reduce((sum, p) => sum + (p.files_count || 0), 0)}
      </div>
      <div className="text-white/70 text-sm">Files Processed</div>
    </div>
    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20 text-center">
      <div className="text-3xl font-bold text-green-400 mb-2">
        {projects.filter(p => p.status === 'completed').length}
      </div>
      <div className="text-white/70 text-sm">Completed</div>
    </div>
    {/* ADD THIS NEW STAT */}
    <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20 text-center">
      <div className="text-3xl font-bold text-blue-400 mb-2">
        {projects.reduce((sum, p) => sum + (p.diagrams_count || 0), 0)}
      </div>
      <div className="text-white/70 text-sm">Diagrams Generated</div>
    </div>
  </div>
)}
      </div>
      
      {/*
      <ProjectViewModal
        project={selectedProject}
        isOpen={showProjectModal}
        onClose={() => {
          setShowProjectModal(false);
          setSelectedProject(null);
        }}
        onDelete={handleDeleteProject}
        onExport={handleExportProject}
        isAdmin={isAdmin}
      />
      */}
    </div>
  );
}

// Main Landing Page Component
export default function LandingPage() {
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentPage, setCurrentPage] = useState('landing');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthLoading, setIsAuthLoading] = useState(false);
  const [showDocumentation, setShowDocumentation] = useState(false); // ADD THIS
  const [documentationProject, setDocumentationProject] = useState(null);

useEffect(() => {
  if (process.env.NODE_ENV === 'development') {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    projectService.setToken(null);
    projectService.setUserRole(null);
    setIsAuthenticated(false);
    setIsAdmin(false);
    setCurrentPage('landing');
  }
}, []);


const handleLogin = async (formData) => {
  try {
    const response = await fetch('http://localhost:5000/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: formData.email,
        password: formData.password
      })
    });

    const data = await response.json();
    
    if (data.success) {
      projectService.setToken(data.token);
      projectService.setUserRole(data.user.role);
      setIsAdmin(data.user.role === 'admin');
      setIsAuthenticated(true);
      setCurrentPage('dashboard');
    } else {
      throw new Error(data.error || 'Login failed');
    }
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
};

  const handleRegister = async (formData) => {
  try {
    const response = await fetch('http://localhost:5000/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: formData.name,
        email: formData.email,
        password: formData.password
      })
    });

    const data = await response.json();
    
    if (data.success) {
      projectService.setToken(data.token);
      setIsAuthenticated(true);
      setCurrentPage('dashboard');
    } else {
      throw new Error(data.error || 'Registration failed');
    }
  } catch (error) {
    console.error('Registration failed:', error);
    throw error; // Re-throw so the RegisterPage can handle it
  }
};
  
  const handleAccessPortal = () => {
  if (isAuthenticated) {
    setCurrentPage('dashboard');
  } else {
    // If user mode is selected, go directly to dashboard as guest
    if (!isAdmin) {
      setIsAuthenticated(true);
      setCurrentPage('dashboard');
    } else {
      // Admin mode requires login
      setCurrentPage('login');
    }
  }
};
  
  const handleNewProject = () => {
    setShowCreateModal(true);
  };
  
  const handleBackToHome = () => {
    setCurrentPage('landing');
  };
  
  const handleCreateProject = async (projectData) => {
    await projectService.createProject(projectData);
  };

  if (showDocumentation && documentationProject) {
    return (
  <DocumentationViewer
    project={documentationProject}
    isAdmin={isAdmin}
    projectService={projectService}
    onClose={() => {
      setShowDocumentation(false);
      setDocumentationProject(null);
    }}
  />
);
  }
  
  if (currentPage === 'dashboard') {
  return (
    <>
      <ProjectDashboard 
  onBack={handleBackToHome} 
  onNewProject={handleNewProject}
  isAdmin={isAdmin}
  setShowDocumentation={setShowDocumentation}
  setDocumentationProject={setDocumentationProject}
/>
      <ProjectCreationModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreateProject={handleCreateProject}
      />
    </>
  );
}

if (currentPage === 'login') {
  return (
    <LoginPage
      onLogin={async (formData) => {
        setIsAuthLoading(true);
        try {
          await handleLogin(formData);
        } finally {
          setIsAuthLoading(false);
        }
      }}
      onSwitchToRegister={() => setCurrentPage('register')}
      isLoading={isAuthLoading}
    />
  );
}

// register page removed only for admin

  // Default Landing Page
  return (
    <div 
      className="min-h-screen relative overflow-hidden"
      style={{ 
        background: 'linear-gradient(135deg, #2C1810 0%, #3D2417 25%, #5D3A25 50%, #8B5A3C 75%, #F5F5F5 100%)'
      }}
    >
      {/* Enhanced header */}
      <header className="relative z-10 flex items-center justify-between p-6 md:p-8 backdrop-blur-sm">
        <div className="flex items-center space-x-4">
          <img 
            src="/images/mashreq-logo.png" 
            alt="Mashreq Logo" 
            className="w-40 h-40 md:w-24 md:h-24 object-contain"
          />
        </div>
        
        
        {/* Admin toggle */}
<div className="flex items-center space-x-3 md:space-x-4 bg-white/10 backdrop-blur-md rounded-2xl px-4 md:px-6 py-2 md:py-3 border border-white/20 shadow-2xl">
  <span className="text-xs md:text-sm font-medium text-white/90">User</span>
  <ToggleSwitch
  isOn={isAdmin}
  handleToggle={() => {
    // Reset authentication state when switching modes
    setIsAuthenticated(false);
    projectService.setToken(null);
    projectService.setUserRole(null);
    setIsAdmin(prev => !prev);
    
    // If we're not on the landing page, go back to it
    if (currentPage !== 'landing') {
      setCurrentPage('landing');
    }
  }}
/>
  <span className="text-xs md:text-sm font-medium text-white/90">Admin</span>
</div>
      </header>

      {/* Main content */}
      <div className="relative z-10 flex flex-col lg:flex-row items-center justify-center min-h-[calc(100vh-140px)] px-6 md:px-8 max-w-7xl mx-auto gap-8 lg:gap-12">
        {/* Left content */}
        <div className="flex-1 max-w-4xl text-center lg:text-left">
          <div className="space-y-6 md:space-y-8">
            {/* Premium badge */}
            <div className="inline-flex items-center px-3 md:px-4 py-2 rounded-full bg-gradient-to-r from-orange-500/20 to-blue-600/20 border border-white/20 backdrop-blur-sm">
              <span className="text-xs md:text-sm font-medium text-white/90">Enterprise Documentation Platform</span>
            </div>
            
            {/* Main heading */}
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight text-white">
              Technical Documentation,
              <br />
              <span style={{ 
                background: 'linear-gradient(135deg, #F58220 0%, #FF8C42 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text'
              }}>
                Reimagined
              </span>
            </h1>
            
            <p className="text-lg md:text-xl leading-relaxed text-white/80 max-w-2xl mx-auto lg:mx-0">
              Transform your project documentation with AI-powered organization, 
              real-time collaboration, and enterprise-grade security. Built for the modern workspace.
            </p>
            
            {/* CTA section */}
            <div className="pt-4">
              <button
  onClick={handleAccessPortal}
  className="group relative px-8 md:px-10 py-3 md:py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold rounded-2xl transition-all duration-300 hover:shadow-2xl hover:shadow-orange-500/25 transform hover:scale-105 hover:-translate-y-1 text-sm md:text-base"
  style={{ boxShadow: '0 10px 30px rgba(245,130,32,0.3)' }}
>
  <span className="relative z-10">
    {isAuthenticated 
      ? 'ACCESS PORTAL' 
      : isAdmin 
        ? 'LOGIN & ACCESS PORTAL' 
        : 'ACCESS PORTAL AS VIEWER'
    }
  </span>
  <div className="absolute inset-0 bg-gradient-to-r from-orange-400 to-orange-500 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
</button>
            </div>
          </div>
        </div>

        {/* Right content - Preview */}
        <div className="flex-1 flex justify-center items-center w-full max-w-lg lg:max-w-none">
          <div className="relative w-full max-w-md lg:max-w-lg">
            {/* Main preview card */}
            <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 md:p-8 border border-white/20 shadow-2xl transform rotate-2 hover:rotate-1 transition-all duration-500"
                 style={{ boxShadow: '0 25px 60px rgba(0,0,0,0.3)' }}>
              <div className="bg-white rounded-2xl p-6 md:p-8 shadow-xl">
                <div className="flex items-center justify-between mb-4 md:mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 md:w-10 md:h-10 rounded-xl flex items-center justify-center" 
                         style={{ backgroundColor: '#F58220' }}>
                      <svg className="w-4 h-4 md:w-6 md:h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-bold text-base md:text-lg" style={{ color: '#F58220' }}>Documentation</h3>
                      <p className="text-xs md:text-sm text-gray-500">Last updated 2 hours ago</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-orange-400 rounded-full"></div>
                    <span className="text-xs text-gray-600">Live</span>
                  </div>
                </div>
                
                <div className="space-y-3 md:space-y-4">
                  <div className="h-2 md:h-3 bg-gray-100 rounded-lg"></div>
                  <div className="h-2 md:h-3 bg-gray-100 rounded-lg w-4/5"></div>
                  <div className="h-2 md:h-3 rounded-lg w-3/5" style={{ backgroundColor: '#F58220', opacity: 0.3 }}></div>
                  <div className="h-2 md:h-3 bg-gray-100 rounded-lg w-2/3"></div>
                </div>
                
                <div className="flex items-center justify-between mt-4 md:mt-6 pt-3 md:pt-4 border-t border-gray-100">
                  <div className="flex items-center space-x-2">
                    <div className="w-5 h-5 md:w-6 md:h-6 bg-gray-200 rounded-full"></div>
                    <span className="text-xs md:text-sm text-gray-600">John Smith</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <svg className="w-3 h-3 md:w-4 md:h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    <span className="text-xs text-gray-500">247 views</span>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Floating badges */}
            <div className="absolute -top-4 md:-top-6 -left-4 md:-left-6 bg-gradient-to-r from-orange-500 to-orange-600 rounded-2xl p-3 md:p-4 shadow-2xl animate-pulse">
              <svg className="w-6 h-6 md:w-8 md:h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            
            <div className="absolute -bottom-6 md:-bottom-8 -right-6 md:-right-8 bg-white/20 backdrop-blur-xl rounded-2xl p-4 md:p-6 border border-white/30 shadow-2xl">
              <div className="flex items-center space-x-3">
                <div className="w-3 h-3 bg-green-400 rounded-full animate-ping"></div>
                <div className="text-white">
                  <div className="text-xs md:text-sm font-semibold">Real-time Sync</div>
                  <div className="text-xs opacity-80">3 active editors</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}