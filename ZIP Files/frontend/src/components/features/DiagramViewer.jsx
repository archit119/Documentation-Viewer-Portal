// components/features/DiagramViewer.jsx
import React, { useState, useEffect } from 'react';

const DiagramViewer = ({ diagrams, project, isAdmin, projectService }) => {
  const [selectedDiagram, setSelectedDiagram] = useState(null);
  const [diagramCategories, setDiagramCategories] = useState({});
  const [activeCategory, setActiveCategory] = useState('all');
  const [viewMode, setViewMode] = useState('grid');
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showFullScreen, setShowFullScreen] = useState(false);

  useEffect(() => {
    if (diagrams && diagrams.diagrams) {
      organizeDiagrams();
    }
  }, [diagrams]);

  const organizeDiagrams = () => {
    console.log('🎨 Organizing diagrams:', diagrams);
    
    const categories = {
      'all': [],
      'architecture': [],
      'journey': [],
      'flow': [],
      'analysis': []
    };

    // Process generated diagrams
    const generatedDiagrams = diagrams.diagrams || {};
    Object.entries(generatedDiagrams).forEach(([key, diagram]) => {
      const categoryKey = getCategoryFromType(key);
      const diagramWithId = { ...diagram, id: key, source: 'generated' };
      categories[categoryKey].push(diagramWithId);
      categories['all'].push(diagramWithId);
    });

    setDiagramCategories(categories);
    
    // Set first diagram as selected if available
    if (categories['all'].length > 0) {
      setSelectedDiagram(categories['all'][0]);
    }
  };

  const getCategoryFromType = (type) => {
    if (type.includes('architecture')) {
      return 'architecture';
    } else if (type.includes('user_journey')) {
      return 'journey';
    } else if (type.includes('data_flow')) {
      return 'flow';
    } else {
      return 'analysis';
    }
  };

  const getDiagramIcon = (type) => {
    const iconMap = {
      'architecture': '🏗️',
      'user_journey': '👤',
      'data_flow': '🌊',
      'file_structure': '📂',
      'tech_stack': '⚙️',
      'complexity': '📊'
    };
    return iconMap[type] || '📈';
  };

  const getCategoryDisplayName = (category) => {
    const nameMap = {
      'all': 'All Diagrams',
      'architecture': 'Architecture',
      'journey': 'User Journeys',
      'flow': 'Data Flows',
      'analysis': 'Analysis'
    };
    return nameMap[category] || category;
  };

  const handleGenerateDiagrams = async () => {
    if (!isAdmin) {
      alert('Only admins can generate diagrams');
      return;
    }
    
    setIsGenerating(true);
    try {
      console.log('🎨 Generating diagrams for project:', project.id);
      
      const response = await fetch(`http://localhost:5000/api/diagrams/project/${project.id}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${projectService?.token || localStorage.getItem('auth_token')}`
        }
      });

      const data = await response.json();
      console.log('📊 Diagram generation response:', data);
      
      if (data.success) {
        alert('Diagrams generated successfully! Refreshing...');
        window.location.reload(); // Simple refresh to show new diagrams
      } else {
        alert(`Failed to generate diagrams: ${data.error}`);
      }
    } catch (error) {
      console.error('❌ Failed to generate diagrams:', error);
      alert(`Failed to generate diagrams: ${error.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleViewDiagram = (diagram) => {
    setSelectedDiagram(diagram);
    setShowFullScreen(true);
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading diagrams...</p>
        </div>
      </div>
    );
  }

  // No diagrams state
  if (!diagrams || !diagrams.diagrams || Object.keys(diagrams.diagrams).length === 0) {
    return (
      <div className="text-center py-12">
        <div className="mb-6">
          <div className="w-24 h-24 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <span className="text-4xl">📊</span>
          </div>
          <h3 className="text-xl font-semibold text-gray-700 mb-2">No Diagrams Available</h3>
          <p className="text-gray-500 mb-6">Generate AI-powered diagrams to visualize your project architecture, user journeys, and data flows.</p>
        </div>
        
        {isAdmin && (
          <button
            onClick={handleGenerateDiagrams}
            disabled={isGenerating}
            className={`inline-flex items-center px-6 py-3 rounded-lg font-medium transition-all ${
              isGenerating 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-lg hover:shadow-xl transform hover:scale-105'
            } text-white`}
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                Generating AI Diagrams...
              </>
            ) : (
              <>
                <span className="mr-2">🤖</span>
                Generate AI Diagrams
              </>
            )}
          </button>
        )}
      </div>
    );
  }

  const currentDiagrams = diagramCategories[activeCategory] || [];

  return (
    <div className="space-y-6">
      {/* Header with controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Project Diagrams</h2>
          <p className="text-gray-600">
            AI-generated visualizations • {Object.keys(diagrams.diagrams).length} diagrams available
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          {isAdmin && (
            <button
              onClick={handleGenerateDiagrams}
              disabled={isGenerating}
              className={`inline-flex items-center px-4 py-2 rounded-lg font-medium text-sm transition-all ${
                isGenerating 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'bg-orange-500 hover:bg-orange-600 shadow-md hover:shadow-lg'
              } text-white`}
            >
              {isGenerating ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Regenerating...
                </>
              ) : (
                <>
                  <span className="mr-2">🔄</span>
                  Regenerate
                </>
              )}
            </button>
          )}
          
          <div className="flex bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${
                viewMode === 'grid' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-3 py-1 rounded-md text-sm font-medium transition-all ${
                viewMode === 'list' ? 'bg-white shadow-sm text-blue-600' : 'text-gray-600 hover:text-gray-800'
              }`}
            >
              List
            </button>
          </div>
        </div>
      </div>

      {/* Category filters */}
      <div className="flex flex-wrap gap-2 pb-4 border-b border-gray-200">
        {Object.entries(diagramCategories).map(([category, diagrams]) => (
          <button
            key={category}
            onClick={() => setActiveCategory(category)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              activeCategory === category
                ? 'bg-blue-600 text-white shadow-md'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {getCategoryDisplayName(category)} ({diagrams.length})
          </button>
        ))}
      </div>

      {/* Diagrams grid/list */}
      {currentDiagrams.length > 0 ? (
        <div className={`grid gap-6 ${
          viewMode === 'grid' 
            ? 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3' 
            : 'grid-cols-1'
        }`}>
          {currentDiagrams.map((diagram) => (
            <DiagramCard
              key={diagram.id}
              diagram={diagram}
              viewMode={viewMode}
              onView={() => handleViewDiagram(diagram)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-8">
          <p className="text-gray-500">No diagrams in this category</p>
        </div>
      )}

      {/* Full screen modal */}
      {showFullScreen && selectedDiagram && (
        <FullScreenModal
          diagram={selectedDiagram}
          onClose={() => setShowFullScreen(false)}
        />
      )}
    </div>
  );
};

// Diagram card component
const DiagramCard = ({ diagram, viewMode, onView }) => {
  const getImageUrl = (diagram) => {
    if (diagram.filename) {
      return `http://localhost:5000/static/diagrams/${diagram.filename}`;
    }
    return null;
  };

  const imageUrl = getImageUrl(diagram);

  if (viewMode === 'list') {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{getDiagramIcon(diagram.type)}</span>
              <h3 className="text-lg font-semibold text-gray-800">{diagram.title}</h3>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full">
                {diagram.type}
              </span>
            </div>
            <p className="text-gray-600 text-sm mb-3">{diagram.description}</p>
            
            {diagram.metrics && (
              <div className="flex flex-wrap gap-4 text-xs text-gray-500 mb-4">
                {Object.entries(diagram.metrics).map(([key, value]) => (
                  <span key={key} className="bg-gray-50 px-2 py-1 rounded">
                    {key}: {value}
                  </span>
                ))}
              </div>
            )}
          </div>
          
          <div className="ml-4">
            {imageUrl && (
              <img 
                src={imageUrl} 
                alt={diagram.title}
                className="w-24 h-16 object-cover rounded-lg border border-gray-200"
                onError={(e) => {
                  e.target.style.display = 'none';
                }}
              />
            )}
          </div>
        </div>
        
        <div className="flex justify-end">
          <button
            onClick={onView}
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <span className="mr-2">👁️</span>
            View Full Size
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-lg transition-all duration-300 transform hover:scale-105">
      <div className="aspect-video bg-gray-50 flex items-center justify-center relative">
        {imageUrl ? (
          <img 
            src={imageUrl} 
            alt={diagram.title}
            className="w-full h-full object-contain"
            onError={(e) => {
              e.target.style.display = 'none';
              e.target.nextSibling.style.display = 'flex';
            }}
          />
        ) : null}
        <div className="absolute inset-0 flex items-center justify-center bg-gray-100" style={{display: imageUrl ? 'none' : 'flex'}}>
          <div className="text-center">
            <span className="text-4xl mb-2 block">{getDiagramIcon(diagram.type)}</span>
            <p className="text-gray-500 text-sm">Diagram Preview</p>
          </div>
        </div>
      </div>
      
      <div className="p-4">
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-lg font-semibold text-gray-800 truncate">{diagram.title}</h3>
          <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full shrink-0">
            {diagram.type}
          </span>
        </div>
        
        <p className="text-gray-600 text-sm mb-3 line-clamp-2">{diagram.description}</p>
        
        {diagram.metrics && (
          <div className="flex flex-wrap gap-2 mb-4">
            {Object.entries(diagram.metrics).slice(0, 2).map(([key, value]) => (
              <span key={key} className="bg-gray-50 text-gray-600 text-xs px-2 py-1 rounded">
                {key}: {value}
              </span>
            ))}
          </div>
        )}
        
        <button
          onClick={onView}
          className="w-full inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
        >
          <span className="mr-2">👁️</span>
          View Full Size
        </button>
      </div>
    </div>
  );
};

// Full screen modal component
const FullScreenModal = ({ diagram, onClose }) => {
  const getImageUrl = (diagram) => {
    if (diagram.filename) {
      return `http://localhost:5000/static/diagrams/${diagram.filename}`;
    }
    return null;
  };

  const imageUrl = getImageUrl(diagram);

  return (
    <div className="fixed inset-0 z-50 bg-black bg-opacity-75 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl max-w-6xl max-h-full w-full overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div>
            <h3 className="text-xl font-bold text-gray-800">{diagram.title}</h3>
            <p className="text-gray-600 text-sm">{diagram.description}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <span className="text-2xl">✕</span>
          </button>
        </div>
        
        {/* Image */}
        <div className="p-6">
          {imageUrl ? (
            <div className="text-center">
              <img 
                src={imageUrl} 
                alt={diagram.title}
                className="max-w-full h-auto rounded-lg shadow-lg mx-auto"
                style={{ maxHeight: 'calc(100vh - 300px)' }}
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'block';
                }}
              />
              <div style={{ display: 'none' }} className="text-center py-12">
                <span className="text-6xl mb-4 block">{getDiagramIcon(diagram.type)}</span>
                <p className="text-gray-500">Image failed to load</p>
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <span className="text-6xl mb-4 block">{getDiagramIcon(diagram.type)}</span>
              <p className="text-gray-500">No image available</p>
            </div>
          )}
          
          {/* Metrics */}
          {diagram.metrics && (
            <div className="mt-6 bg-gray-50 rounded-lg p-4">
              <h4 className="font-semibold text-gray-800 mb-3">Diagram Metrics</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {Object.entries(diagram.metrics).map(([key, value]) => (
                  <div key={key} className="text-center">
                    <div className="text-lg font-bold text-blue-600">{value}</div>
                    <div className="text-sm text-gray-600 capitalize">{key.replace('_', ' ')}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Helper function for icons (moved outside component to avoid recreation)
const getDiagramIcon = (type) => {
  const iconMap = {
    'architecture': '🏗️',
    'user_journey': '👤',
    'data_flow': '🌊',
    'file_structure': '📂',
    'tech_stack': '⚙️',
    'complexity': '📊'
  };
  return iconMap[type] || '📈';
};

export default DiagramViewer;