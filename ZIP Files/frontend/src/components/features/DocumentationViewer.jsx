import React, { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
// import DiagramViewer from './DiagramViewer';

const parseMarkdownToSections = (markdown) => {
  if (!markdown) return [];
  // helpers to build unique, URL-safe ids
const slugify = (s) => s.toLowerCase()
  .replace(/[^a-z0-9\s-]/g, '')
  .replace(/\s+/g, '-')
  .replace(/-+/g, '-')
  .substring(0, 50);

const idCounts = new Map();
const uniqId = (raw) => {
  const base = slugify(raw);
  const count = (idCounts.get(base) || 0) + 1;
  idCounts.set(base, count);
  return count === 1 ? base : `${base}-${count}`;
};

  
  const lines = markdown.split('\n');
  const sections = [];
  let currentMainSection = null;
  let currentSubSection = null;
  let allContent = [];
  
  lines.forEach(line => {
    const headerMatch = line.match(/^(#{1,4})\s+(.+)$/);
    
    if (headerMatch) {
      const level = headerMatch[1].length;
      const title = headerMatch[2].trim();
      const id = uniqId(title);
      
      if (level === 1) {
        // Save previous main section
        if (currentMainSection) {
          currentMainSection.fullContent = allContent.join('\n').trim();
          sections.push(currentMainSection);
        }
        
        // Start new main section
        currentMainSection = {
          id,
          title,
          level,
          icon: getSectionIcon(title),
          subsections: [],
          content: '',
          fullContent: ''
        };
        currentSubSection = null;
        allContent = [line];
      } else if (level === 2 && currentMainSection) {
        // Add subsection to current main section
        if (currentSubSection) {
          currentMainSection.subsections.push(currentSubSection);
        }
        
        currentSubSection = {
          id,
          title,
          level,
          content: '',
          parentId: currentMainSection.id
        };
        allContent.push(line);
      } else {
        allContent.push(line);
      }
    } else {
      allContent.push(line);
    }
  });
  
  // Don't forget the last section
  if (currentSubSection && currentMainSection) {
  currentMainSection.subsections.push(currentSubSection);
}
if (currentMainSection) {
  currentMainSection.fullContent = allContent.join('\n').trim();
  sections.push(currentMainSection);
}

// Filter out sections with minimal content
// Filter out sections with minimal content
const filteredSections = sections.filter(section => {
  const content = section.fullContent || '';

  // If this section contains a WYSIWYG HTML marker anywhere, always keep it
  if (content.indexOf('<!--HTML_DOC-->') !== -1) {
    console.log(`✅ Keeping HTML section "${section.title}" (has WYSIWYG marker)`);
    return true;
  }

  // Count actual words (not headers or formatting)
  const words = content.split(/\s+/).filter(word => 
    word.trim() && 
    !word.startsWith('#') && 
    word.length > 2
  );

  // Count meaningful lines
  const lines = content.split('\n');
  const meaningfulLines = lines.filter(line => 
    line.trim() && 
    !line.trim().startsWith('#') && 
    line.trim().length > 10 &&
    !line.trim().match(/^[-=*`]{3,}$/)
  );

  const hasEnoughWords = words.length >= 30;
  const hasEnoughLines = meaningfulLines.length >= 3;
  const hasSubstantialContent = content.replace(/[#\-*\n\s`]/g, '').length > 50;

  // Check for empty content indicators
  const hasEmptyIndicators = content.toLowerCase().includes('no content') ||
                             content.toLowerCase().includes('analysis failed') ||
                             content.toLowerCase().includes('error occurred');

  const isValid = hasEnoughWords && hasEnoughLines && hasSubstantialContent && !hasEmptyIndicators;

  if (!isValid) {
    console.log(`🚫 Filtering out section "${section.title}":`, {
      words: words.length,
      meaningfulLines: meaningfulLines.length,
      contentLength: content.length,
      hasEmptyIndicators,
      hasHTMLMarker: content.indexOf('<!--HTML_DOC-->') !== -1
    });
  }

  return isValid;
});


console.log(`📊 Filtered sections: ${sections.length} → ${filteredSections.length}`);
return filteredSections;
};

const getSectionIcon = (title) => {
  const titleLower = title.toLowerCase();
  
  if (titleLower.includes('overview') || titleLower.includes('introduction')) {
    return '📋';
  } else if (titleLower.includes('installation') || titleLower.includes('setup')) {
    return '⚙️';
  } else if (titleLower.includes('usage') || titleLower.includes('guide')) {
    return '📖';
  } else if (titleLower.includes('api') || titleLower.includes('endpoint')) {
    return '🔌';
  } else if (titleLower.includes('architecture') || titleLower.includes('design')) {
    return '🏗️';
  } else if (titleLower.includes('configuration') || titleLower.includes('config')) {
    return '⚙️';
  } else if (titleLower.includes('deployment') || titleLower.includes('deploy')) {
    return '🚀';
  } else if (titleLower.includes('troubleshooting') || titleLower.includes('faq')) {
    return '🔧';
  } else if (titleLower.includes('security') || titleLower.includes('auth')) {
    return '🔒';
  } else if (titleLower.includes('development') || titleLower.includes('dev')) {
    return '💻';
  } else if (titleLower.includes('testing') || titleLower.includes('test')) {
    return '🧪';
  } else if (titleLower.includes('maintenance') || titleLower.includes('update')) {
    return '🔄';
  } else {
    return '📄';
  }
};

// Enhanced markdown renderer with proper white text
// Enhanced markdown renderer with FIXED formatting
const MarkdownRenderer = ({ content, onFileClick }) => {
  const rootRef = useRef(null);

  useEffect(() => {
    if (!onFileClick || !rootRef.current) return;
    const handler = (e) => {
      const btn = e.target.closest('.view-file-btn');
      if (btn && btn.dataset.file) {
        e.preventDefault();
        onFileClick(btn.dataset.file);
      }
    };
    rootRef.current.addEventListener('click', handler);
    return () => rootRef.current?.removeEventListener('click', handler);
  }, [onFileClick]);

  const renderMarkdown = (raw) => {
    if (!raw) return '';
    // If content was saved by the WYSIWYG editor, render the HTML directly
    // If any WYSIWYG HTML marker exists, render that HTML directly (ignore markdown parsing)
const markerIndex = raw.indexOf('<!--HTML_DOC-->');
if (markerIndex !== -1) {
  // render only the HTML portion; avoids re-parsing and duplicating "View file" chips
  return raw.slice(markerIndex).replace('<!--HTML_DOC-->', '');
}

    // 1) normalize, then process markdown
    let text = raw.replace(/\r\n?/g, '\n');
    text = text.replace(/!\[([^\]]*)\]\(data:image\/[^;]+;base64,([^)]+)\)/g, (match, alt, base64Data) => {
      // Ensure base64 data is clean
    const cleanBase64 = base64Data.replace(/\s/g, '');
    return `<div class="my-6 text-center">
        <img src="data:image/png;base64,${cleanBase64}" 
             alt="${alt || 'Embedded image'}" 
             class="max-w-full h-auto rounded-lg shadow-lg border border-white/20 bg-white/5 p-2"
             style="max-height: 400px; object-fit: contain;" />
        ${alt ? `<p class="text-sm text-white/70 mt-2 italic">${alt}</p>` : ''}
      </div>`;
    });
    
    // Handle regular images
    text = text.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, url) => {
      return `<div class="my-6 text-center">
        <img src="${url}" 
             alt="${alt || 'Image'}" 
             class="max-w-full h-auto rounded-lg shadow-lg border border-white/20"
             style="max-height: 400px; object-fit: contain;" />
        ${alt ? `<p class="text-sm text-white/70 mt-2 italic">${alt}</p>` : ''}
      </div>`;
    });
    

    // Headers (longest first)
    text = text.replace(/^#### (.*$)/gim, (m, title) => {
      const id = title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').substring(0, 50);
      return `<h4 class="text-lg font-semibold text-white mt-6 mb-3 border-b border-white/20 pb-2" id="${id}">${title}</h4>`;
    });
    text = text.replace(/^### (.*$)/gim, (m, title) => {
      const id = title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').substring(0, 50);
      return `<h3 class="text-xl font-bold text-white mt-8 mb-4 border-b border-white/20 pb-2" id="${id}">${title}</h3>`;
    });
    text = text.replace(/^## (.*$)/gim, (m, title) => {
      const id = title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').substring(0, 50);
      return `<h2 class="text-2xl font-bold text-white mt-10 mb-5 border-b border-orange-500/30 pb-3" id="${id}">${title}</h2>`;
    });
    text = text.replace(/^# (.*$)/gim, (m, title) => {
      const id = title.toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-').substring(0, 50);
      return `<h1 class="text-3xl font-bold text-white mt-12 mb-6 border-b border-orange-500/50 pb-4" id="${id}">${title}</h1>`;
    });

// Code fences → placeholders, skip trivial file-reference or empty blocks
const codePlaceholders = [];
text = text.replace(/```(\w+)?\s*\n([\s\S]*?)\n\s*```/gm, (match, lang, code) => {
  const clean = (code || '').trim();
  if (!clean) return ''; // drop empty

  // Skip if block is only imports, file paths, or comments
  const lines = clean.split("\n").map(l => l.trim()).filter(Boolean);
  const isTrivial = lines.length > 0 && lines.every(l =>
    l.startsWith("import ") ||
    l.endsWith(".js") || l.endsWith(".jsx") || l.endsWith(".css") ||
    l.startsWith("//") || l.startsWith("#") ||
    (l.startsWith("from ") && l.includes("import"))
  );
  if (isTrivial) return ''; // no placeholder, just remove

  // Keep meaningful code block
  const langLabel = lang ? `<span class="text-xs text-orange-300 mb-2 block font-semibold">${lang.toUpperCase()}</span>` : '';
  const html = `<div class="my-6"><pre class="bg-gray-900/80 backdrop-blur-xl rounded-xl p-4 overflow-x-auto border border-white/10">${langLabel}<code class="text-sm font-mono text-green-300 leading-relaxed whitespace-pre">${clean}</code></pre></div>`;
  codePlaceholders.push(html);
  return '';
});


    // Single-backtick code blocks occupying the whole line
    text = text.replace(/^`([^`\n]*(?:\n(?!`)[^\n]*)*)`$/gm, (match, content) => {
      if (content.includes('from ') || content.includes('import ') || content.includes('def ') || content.includes('@') || content.includes('app.') || content.length > 100) {
        return `<div class="my-6"><pre class="bg-gray-900/80 backdrop-blur-xl rounded-xl p-4 overflow-x-auto border border-white/10"><code class="text-sm font-mono text-green-300 leading-relaxed whitespace-pre">${content.trim()}</code></pre></div>`;
      }
      return `<code class="bg-gray-800/60 px-2 py-1 rounded text-sm font-mono text-green-300 border border-gray-700/50">${content}</code>`;
    });

    // Inline code (short)
    text = text.replace(/(?<!`)`([^`\n]+)`(?!`)/g, '<code class="bg-gray-800/60 px-2 py-1 rounded text-sm font-mono text-green-300 border border-gray-700/50">$1</code>');

    // 📄 Filename pass (run AFTER code/headers, BEFORE lists/links/paragraphs)
    const FILE_EXTS = '(py|js|jsx|ts|tsx|json|yml|yaml|ini|toml|md|html|css|scss|sql|sh|rb|go|rs|java|kt|swift|php|c|cpp)';
    const fileRegex = new RegExp(`\\b([\\w./-]+?\\.(${FILE_EXTS}))\\b`, 'g');
    text = text.replace(fileRegex, (m) => {
      const safe = m.replace(/"/g, '&quot;');
      return `
  <span class="file-chip inline-flex items-center gap-2" contenteditable="false" tabindex="0" data-file-chip="${safe}">
    <code class="bg-gray-800/60 px-2 py-1 rounded text-xs font-mono text-green-300 border border-gray-700/50">${safe}</code>
    <button class="view-file-btn text-xs px-2 py-1 rounded bg-orange-500/20 text-orange-300 border border-orange-500/30 hover:bg-orange-500/30" data-file="${safe}">
      View file
    </button>
  </span>
`;
    });

    // Bold / Italic
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-orange-300">$1</strong>');
    text = text.replace(/\*(.*?)\*/g, '<em class="italic text-white/90">$1</em>');

    // Numbered lists
    text = text.replace(/((?:^\d+\.\s+.*(?:\n|$))+)/gm, (match) => {
      const items = match.trim().split('\n').map(line => {
        const m = line.match(/^\d+\.\s+(.*)$/);
        if (!m) return '';
        let item = m[1].replace(/`([^`]+)`/g, '<code class="bg-gray-800/60 px-1.5 py-0.5 rounded text-xs font-mono text-green-300 border border-gray-700/50">$1</code>');
        return `<li class="text-white/90 mb-3 leading-relaxed pl-2">${item}</li>`;
      }).filter(Boolean).join('');
      return `<ol class="list-decimal list-inside space-y-2 my-6 pl-4 text-white/90 bg-white/5 rounded-lg p-4 border border-white/10">${items}</ol>`;
    });

    // Bullet lists
    // Bullet lists (skip empty/placeholder-only items)
text = text.replace(/((?:^[-*+]\s+.*(?:\n|$))+)/gm, (match) => {
  const items = match.trim().split('\n').map(line => {
    const m = line.match(/^[-*+]\s+(.*)$/);
    if (!m) return '';
    const raw = (m[1] || '').trim();
    if (!raw) return '';                        // drop empty bullets
    if (/^__CODE_BLOCK_\d+__$/.test(raw)) return ''; // drop bullets that were only code
    let item = raw.replace(/`([^`]+)`/g, '<code class="bg-gray-800/60 px-1.5 py-0.5 rounded text-xs font-mono text-green-300 border border-gray-700/50">$1</code>');
    return `<li class="text-white/90 mb-3 leading-relaxed pl-2">${item}</li>`;
  }).filter(Boolean).join('');
  if (!items) return ''; // don't render an empty <ul>
  return `<ul class="list-disc list-inside space-y-2 my-6 pl-4 text-white/90 bg-white/5 rounded-lg p-4 border border-white/10">${items}</ul>`;
});


    // Links
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-orange-400 hover:text-orange-300 underline decoration-orange-400/50 hover:decoration-orange-300 font-medium">$1</a>');

    // Paragraphs
    const paragraphs = text.split('\n\n').filter(p => p.trim());
    text = paragraphs.map(p => `<p class="mb-6 text-white/90 leading-relaxed">${p.trim()}</p>`).join('');

    return text;
  };

  if (!content) return <div className="text-white/70">No content available</div>;

  return (
    <div
      ref={rootRef}
      className="prose prose-lg max-w-none"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
    />
  );
};


// Right sidebar for subsection navigation
// Right sidebar for subsection navigation
// Right sidebar for subsection navigation
// Right sidebar for subsection navigation - FIXED VERSION
// Right sidebar for subsection navigation - FIXED VERSION
// Right sidebar for subsection navigation - COMPLETELY FIXED VERSION
// Right sidebar for subsection navigation - COMPLETELY FIXED VERSION
const SubsectionSidebar = ({ subsections, activeSubsectionId, onSubsectionSelect }) => {
  if (!subsections || subsections.length === 0) return null;
  
  const scrollToSubsection = (subsection) => {
    const elementId = subsection.id;
    const element = document.getElementById(elementId);
    
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start', inline: 'nearest' });
      onSubsectionSelect(subsection.id);
    } else {
      console.warn(`Element with ID '${elementId}' not found`);
    }
  };
  
  return (
    <div className="w-64 bg-white/5 backdrop-blur-xl border-l border-white/20 flex-shrink-0 relative">
      {/* FIXED: Proper sticky positioning with fixed height container */}
      <div className="sticky top-6 h-[calc(100vh-6rem)]">
        <div className="bg-white/5 rounded-xl m-4 border border-white/10 h-full flex flex-col">
          <div className="p-4 border-b border-white/10 flex-shrink-0">
            <h3 className="text-white font-semibold text-sm">In this section:</h3>
          </div>
          <nav className="flex-1 overflow-y-auto p-2 scrollbar-thin scrollbar-track-white/5 scrollbar-thumb-white/20">
            {subsections.map(subsection => (
              <button
                key={subsection.id}
                onClick={() => scrollToSubsection(subsection)}
                className={`w-full text-left p-3 rounded-lg mb-2 transition-all duration-200 text-sm group ${
                  activeSubsectionId === subsection.id 
                    ? 'bg-orange-500/20 text-orange-300 border-l-4 border-orange-500'
                    : 'text-white/70 hover:text-white hover:bg-white/10 hover:border-l-4 hover:border-white/30'
                }`}
              >
                <div className="font-medium">{subsection.title}</div>
                {subsection.description && (
                  <div className="text-xs text-white/50 mt-1 group-hover:text-white/70 line-clamp-2">
                    {subsection.description}
                  </div>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>
    </div>
  );
};

// Main Documentation Viewer Component
export default function DocumentationViewer({ project: initialProject, onClose, isAdmin, projectService }) { 
  const [project, setProject] = useState(initialProject);
  const [sections, setSections] = useState([]);
  const [activeSectionId, setActiveSectionId] = useState('');
  const [activeSubsectionId, setActiveSubsectionId] = useState('');
  const [activeTab, setActiveTab] = useState('documentation'); 
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');
  const [fileModalOpen, setFileModalOpen] = useState(false);
  const [fileModalName, setFileModalName] = useState('');
  const [fileModalLoading, setFileModalLoading] = useState(false);
  const [fileModalContent, setFileModalContent] = useState('');
  const contentViewRef = useRef(null);     // holds rendered (view) HTML
  const editorRef = useRef(null);          // contenteditable target
  const [editorHtml, setEditorHtml] = useState('');  // WYSIWYG buffer
  const editorInitDone = useRef(false);

  function placeCaretAtEnd(el) {
  try {
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  } catch {}
}

function applyInlineStyle(styleObj = {}) {
  const sel = window.getSelection();
  if (!sel || sel.rangeCount === 0) return;
  
  // Focus the editor first
  if (editorRef.current) {
    editorRef.current.focus();
  }
  
  const range = sel.getRangeAt(0);

  if (range.collapsed) {
    // No selection - apply style for future typing
    const span = document.createElement('span');
    Object.entries(styleObj).forEach(([k, v]) => { 
      span.style[k] = v; 
    });
    span.appendChild(document.createTextNode('\u200b')); // zero-width space
    
    try {
      range.insertNode(span);
      // Position cursor after the span
      const newRange = document.createRange();
      newRange.setStartAfter(span);
      newRange.collapse(true);
      sel.removeAllRanges();
      sel.addRange(newRange);
    } catch (e) {
      console.warn('Failed to apply style:', e);
    }
  } else {
    // Has selection - wrap it
    try {
      const span = document.createElement('span');
      Object.entries(styleObj).forEach(([k, v]) => { 
        span.style[k] = v; 
      });
      
      const contents = range.extractContents();
      span.appendChild(contents);
      range.insertNode(span);
      
      // Select the newly styled content
      const newRange = document.createRange();
      newRange.selectNodeContents(span);
      sel.removeAllRanges();
      sel.addRange(newRange);
    } catch (e) {
      console.warn('Failed to apply style to selection:', e);
    }
  }
  
  // Trigger input event to update state
  if (editorRef.current) {
    const event = new Event('input', { bubbles: true });
    editorRef.current.dispatchEvent(event);
  }
}


  // Initialize editor content once when entering edit mode
  useEffect(() => {
    if (isEditing && editorRef.current) {
      const html = editorHtml || (contentViewRef.current ? contentViewRef.current.innerHTML : '');
      // Seed content only once per edit session
      if (!editorInitDone.current) {
        editorRef.current.innerHTML = html || '';
        editorRef.current.setAttribute('dir', 'ltr');
editorRef.current.style.direction = 'ltr';
editorRef.current.style.unicodeBidi = 'embed';
editorInitDone.current = true;

// Ensure lists render properly inside the editor
if (!document.getElementById('editor-inline-style')) {
  const style = document.createElement('style');
  style.id = 'editor-inline-style';
  style.textContent = `
    .wysiwyg-editor ul { 
      list-style-type: disc !important; 
      margin: 1rem 0 !important; 
      padding-left: 2rem !important; 
      display: block !important;
    }
    .wysiwyg-editor ol { 
      list-style-type: decimal !important; 
      margin: 1rem 0 !important; 
      padding-left: 2rem !important; 
      display: block !important;
    }
    .wysiwyg-editor li { 
      display: list-item !important;
      margin: 0.25rem 0 !important; 
      padding-left: 0.5rem !important;
      list-style-position: outside !important;
    }
    .wysiwyg-editor ul ul { margin: 0.5rem 0 0.5rem 1rem !important; }
    .wysiwyg-editor ol ol { margin: 0.5rem 0 0.5rem 1rem !important; }
    .wysiwyg-editor p { margin: 0.5rem 0 !important; }
    
    /* Force list styling even in contenteditable */
    [contenteditable] ul { list-style-type: disc !important; }
    [contenteditable] ol { list-style-type: decimal !important; }
    [contenteditable] li { display: list-item !important; }
  `;
  document.head.appendChild(style);
}

// Add keyboard shortcuts for lists and Enter behavior
editorRef.current.addEventListener('keydown', (e) => {
  if (e.ctrlKey || e.metaKey) {
    switch(e.key) {
      case 'b':
      case 'B':
        e.preventDefault();
        document.execCommand('bold');
        break;
      case 'i':
      case 'I':
        e.preventDefault();
        document.execCommand('italic');
        break;
      case 'z':
      case 'Z':
        if (e.shiftKey) {
          e.preventDefault();
          document.execCommand('redo');
        } else {
          e.preventDefault();
          document.execCommand('undo');
        }
        break;
    }
  }
  
  // Handle Enter key in lists (Word-like behavior)
  if (e.key === 'Enter') {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      let currentNode = range.startContainer;
      
      // Find if we're in a list item
      while (currentNode && currentNode.nodeName !== 'LI' && currentNode.parentNode) {
        currentNode = currentNode.parentNode;
      }
      
      if (currentNode && currentNode.nodeName === 'LI') {
        const listItem = currentNode;
        const list = listItem.parentNode;
        
        // Check if current list item is empty or only has whitespace
        const itemText = listItem.textContent.trim();
        
        if (itemText === '' || itemText === 'New item') {
          // Empty list item - exit the list
          e.preventDefault();
          
          // Create a new paragraph after the list
          const newParagraph = document.createElement('p');
          newParagraph.innerHTML = '<br>'; // Ensure it's visible
          newParagraph.style.margin = '0.5rem 0';
          
          // Remove the empty list item
          listItem.remove();
          
          // If list is now empty, remove it entirely
          if (list.children.length === 0) {
            list.parentNode.insertBefore(newParagraph, list);
            list.remove();
          } else {
            // Insert paragraph after the list
            list.parentNode.insertBefore(newParagraph, list.nextSibling);
          }
          
          // Position cursor in the new paragraph
          const newRange = document.createRange();
          newRange.setStart(newParagraph, 0);
          newRange.collapse(true);
          selection.removeAllRanges();
          selection.addRange(newRange);
          
          // Update editor content
          setEditorHtml(editorRef.current.innerHTML);
          return;
        }
      }
    }
  }
});

        // place caret at end after mount
        // place caret at end after mount
setTimeout(() => {
  editorRef.current && editorRef.current.focus();
  editorRef.current && placeCaretAtEnd(editorRef.current);
}, 0);

// Make file chips atomic and deletable (not editable)
const chips = editorRef.current.querySelectorAll('.file-chip');
chips.forEach(chip => {
  chip.setAttribute('contenteditable', 'false');
  chip.setAttribute('tabindex', '0');

  // Delete with Backspace/Delete when focused
  chip.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' || e.key === 'Delete') {
      e.preventDefault();
      const parent = chip.parentElement;
      chip.remove();
      setEditorHtml(editorRef.current.innerHTML);
      // restore caret
      editorRef.current.focus();
      placeCaretAtEnd(parent || editorRef.current);
    }
  });

  // Double-click to delete (fallback)
  chip.addEventListener('dblclick', (e) => {
    e.preventDefault();
    const parent = chip.parentElement;
    chip.remove();
    setEditorHtml(editorRef.current.innerHTML);
    editorRef.current.focus();
    placeCaretAtEnd(parent || editorRef.current);
  });
});

      }
    } else {
      editorInitDone.current = false;
    }
  }, [isEditing]);  // run only when toggling edit mode

  const openFileViewer = async (fileName) => {
  console.log('[View file click]', fileName);
  try {
    setFileModalName(fileName);
    setFileModalContent('');
    setFileModalLoading(true);
    setFileModalOpen(true);

    const resp = await fetch(`http://localhost:5000/api/projects/${project.id}/files/${encodeURIComponent(fileName)}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(projectService?.token && { 'Authorization': `Bearer ${projectService.token}` })
      }
    });

  const data = await resp.json();
    if (data.success) {
      setFileModalContent(data.content ?? '');
    } else {
      setFileModalContent(`Failed to load file: ${data.error || 'Unknown error'}`);
    }
  } catch (err) {
    setFileModalContent(`Failed to load file: ${err.message}`);
  } finally {
    setFileModalLoading(false);
  }
  };
  const [isSaving, setIsSaving] = useState(false);
  const activeSection = sections.find(s => s.id === activeSectionId);
  const handleSectionSelect = (sectionId) => {
  setActiveSectionId(sectionId);
  setActiveSubsectionId('');
};

  // Update project state when prop changes
  useEffect(() => {
    setProject(initialProject);
  }, [initialProject]);
  // Auto-refresh project data when status is processing
  // FIXED: Auto-refresh project data when status is processing
// Disable polling entirely — AI won't touch project after creation
useEffect(() => {
  // Just parse documentation once if it's available
  if (project?.id && project?.documentation) {
    console.log('📋 Initial documentation parsing...');
    setIsLoading(true);
    const parsedSections = parseMarkdownToSections(project.documentation);
    console.log('📑 Initial parsed sections:', parsedSections.length);
    setSections(parsedSections);
    
    if (parsedSections.length > 0) {
      setActiveSectionId(parsedSections[0].id);
      setActiveSubsectionId('');
      console.log('🎯 Initial active section:', parsedSections[0].id);
    }
    setIsLoading(false);
  }
}, [project?.id, project?.documentation]);


// Add a ref to track if we're currently saving
const isSavingRef = useRef(false);

useEffect(() => {
  if (project?.documentation && sections.length === 0) {
    console.log('🔄 Initial documentation parsing...');
    setIsLoading(true);
    
    // Parse the original documentation
    let parsedSections = parseMarkdownToSections(project.documentation);
    
    // Apply any saved section updates from metadata
    try {
      const metadata = JSON.parse(project.generation_metadata || '{}');
      const sectionUpdates = metadata.section_updates || {};
      
      parsedSections = parsedSections.map(section => {
        if (sectionUpdates[section.id]) {
          console.log(`🔄 Applying saved edit to section: ${section.title}`);
          return {
            ...section,
            fullContent: sectionUpdates[section.id].content
          };
        }
        return section;
      });
    } catch (e) {
      console.warn('Failed to parse section updates:', e);
    }
    
    console.log('📄 Final parsed sections:', parsedSections.length);
    setSections(parsedSections);
    
    if (parsedSections.length > 0) {
      setActiveSectionId(parsedSections[0].id);
      setActiveSubsectionId('');
      console.log('🎯 Initial active section:', parsedSections[0].id);
    }
    setIsLoading(false);
  }
}, [project?.documentation, project?.generation_metadata]);


const handleSaveDocumentation = async (newSectionContent) => {
  setIsSaving(true);
  
  try {
    // Save only the section, not the full documentation
    const response = await fetch(`http://localhost:5000/api/projects/${project.id}/documentation/section`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${projectService.token}`
      },
      body: JSON.stringify({ 
        section_id: activeSectionId,
        section_content: newSectionContent 
      })
    });

    const data = await response.json();

    if (data.success) {
      // Update ONLY the local sections state, don't touch project.documentation
      const updatedSections = sections.map(section => {
        if (section.id === activeSectionId) {
          return {
            ...section,
            fullContent: newSectionContent
          };
        }
        return section;
      });
      
      setSections(updatedSections);
      setIsEditing(false);
      alert('Documentation updated successfully!');
    } else {
      throw new Error(data.error || 'Failed to save documentation');
    }
  } catch (error) {
    console.error('Failed to save documentation:', error);
    alert('Failed to save documentation: ' + error.message);
  } finally {
    setIsSaving(false);
  }
};

// Add this useEffect to your DocumentationViewer component
// Add this AFTER your existing useEffects, around line 300

// Auto-refresh project data when status is processing
  
  // Filter sections for search
  const filteredSections = sections.filter(section =>
    section.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    section.fullContent.toLowerCase().includes(searchQuery.toLowerCase())
  );
  
  if (!project || !project.id) {
  return (
    <div 
      className="min-h-screen flex items-center justify-center"
      style={{ 
        background: 'linear-gradient(135deg, #2C1810 0%, #3D2417 25%, #5D3A25 50%, #8B5A3C 75%, #F0F0F0 100%)'
      }}
    >
      <div className="text-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-white/10 rounded-full flex items-center justify-center">
          <svg className="w-8 h-8 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-white mb-2">
          {!project ? 'No Project Selected' : 'Project Not Found'}
        </h3>
        <p className="text-white/70 mb-4">
          {!project 
            ? 'Please select a project to view its documentation.' 
            : 'The requested project may have been deleted or is no longer available.'
          }
        </p>
        <button
          onClick={onClose}
          className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors"
        >
          Back to Dashboard
        </button>
      </div>
    </div>
  );
}
  
  return (
    <div 
      className="min-h-screen flex"
      style={{ 
        background: 'linear-gradient(135deg, #2C1810 0%, #3D2417 25%, #5D3A25 50%, #8B5A3C 75%, #F0F0F0 100%)'
      }}
    >
      {/* Left Sidebar - Only Main Sections */}
      <div className={`bg-white/10 backdrop-blur-xl border-r border-white/20 transition-all duration-300 ${sidebarCollapsed ? 'w-16' : 'w-80'} flex-shrink-0`}>
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/20">
          <div className={`flex items-center space-x-3 ${sidebarCollapsed ? 'justify-center' : ''}`}>
            <img 
              src="/images/mashreq-logo.png" 
              alt="Mashreq Logo" 
              className="w-8 h-8 object-contain"
            />
            {!sidebarCollapsed && (
              <div>
                <h2 className="font-semibold text-white text-sm truncate max-w-48">{project.title}</h2>
                <p className="text-xs text-white/60">Technical Documentation</p>
              </div>
            )}
          </div>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1 hover:bg-white/10 rounded transition-colors"
          >
            <svg className={`w-4 h-4 text-white/60 transition-transform ${sidebarCollapsed ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        </div>
        
        {/* Search */}
        {!sidebarCollapsed && (
          <div className="p-4 border-b border-white/20">
            <div className="relative">
              <svg className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                type="text"
                placeholder="Search sections..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/60 focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 text-sm backdrop-blur-sm"
              />
            </div>
          </div>
        )}
        
        {/* Navigation - Only Main Sections */}
        <div className="flex-1 overflow-y-auto">
          {isLoading ? (
            <div className="p-4 text-center">
              <div className="animate-spin w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full mx-auto mb-2"></div>
              <p className="text-sm text-white/70">Parsing documentation...</p>
            </div>
          ) : filteredSections.length > 0 ? (
            <nav className="p-2">
              {filteredSections.map((section, index) => (
                <button
                  key={`${section.id}-${index}`}
                  onClick={() => handleSectionSelect(section.id)}
                  className={`w-full text-left p-3 rounded-xl mb-1 transition-all duration-300 ${
                    activeSectionId === section.id
                      ? 'bg-orange-500/20 text-orange-300 border-l-4 border-orange-500 backdrop-blur-sm'
                      : 'hover:bg-white/10 text-white/70 hover:text-white'
                  } ${sidebarCollapsed ? 'justify-center' : ''}`}
                  title={sidebarCollapsed ? section.title : ''}
                >
                  <div className={`flex items-center ${sidebarCollapsed ? 'justify-center' : 'space-x-3'}`}>
                    <span className="text-lg flex-shrink-0">{section.icon}</span>
                    {!sidebarCollapsed && (
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">
                          {`${index + 1}. ${section.title}`}
                        </div>
                        {section.subsections && section.subsections.length > 0 && (
                          <div className="text-xs text-white/50 mt-1">
                            {section.subsections.length} subsection{section.subsections.length !== 1 ? 's' : ''}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </button>
              ))}
            </nav>
          ) : (
            <div className="p-4 text-center text-white/60 text-sm">
              {searchQuery ? 'No matching sections found' : 'No sections found in documentation'}
            </div>
          )}
        </div>
        
        {/* Sidebar Footer */}
        <div className="p-4 border-t border-white/20">
          <button
            onClick={onClose}
            className={`w-full flex items-center space-x-2 px-3 py-2 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors text-sm ${
              sidebarCollapsed ? 'justify-center' : ''
            }`}
            title={sidebarCollapsed ? 'Back to Dashboard' : ''}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            {!sidebarCollapsed && <span>Back to Dashboard</span>}
          </button>
        </div>
</div>



      
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Top Bar */}
        <div className="bg-white/10 backdrop-blur-xl border-b border-white/20 p-4">
  {/* Add Tab Navigation */}
  <div className="flex items-center space-x-6 mb-4 border-b border-white/10 pb-4">
    <button
      onClick={() => setActiveTab('documentation')}
      className={`px-4 py-2 rounded-lg transition-colors ${
        activeTab === 'documentation'
          ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30'
          : 'text-white/70 hover:text-white hover:bg-white/10'
      }`}
    >
      📋 Documentation
    </button>
  </div>

  <div className="flex items-center justify-between">
    <div>
      <h1 className="text-2xl font-bold text-white">
        {activeTab === 'documentation' 
          ? (activeSection ? `${sections.findIndex(s => s.id === activeSectionId) + 1}. ${activeSection.title}` : 'Documentation')
          : 'Project Diagrams'
        }
      </h1>
      <p className="text-sm text-white/70 mt-1">
        {activeTab === 'documentation' 
          ? (project.description || `Technical documentation for ${project.title}`)
          : 'Visual representations and architectural diagrams'
        }
      </p>
    </div>
            <div className="flex items-center space-x-3">
            {/* Edit Button - Admin Only */}
            {isAdmin && (
              isEditing ? (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={async () => {
  // 1) Collect edited section as HTML
  const html = editorRef.current ? editorRef.current.innerHTML : editorHtml;
  const sectionReplacement = `<!--HTML_DOC-->${html}`;

  // 2) Preserve scroll position
  const y = window.scrollY;
  
  // 3) Save the updated section content
  await handleSaveDocumentation(sectionReplacement);
  
  // 4) Restore scroll position
  requestAnimationFrame(() => window.scrollTo({ top: y, left: 0, behavior: 'instant' }));
}}

                    className="px-4 py-2 bg-green-600/20 text-green-300 rounded-lg hover:bg-green-600/30 transition-colors text-sm border border-green-600/40"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => {
                      setIsEditing(false);
                      setEditorHtml('');
                    }}
                    className="px-4 py-2 bg-white/10 text-white/80 rounded-lg hover:bg-white/20 transition-colors text-sm border border-white/20"
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
  // Keep a copy in state for Save, but let the effect seed the DOM once
  const html = contentViewRef.current ? contentViewRef.current.innerHTML : '';
  setEditorHtml(html);
  setIsEditing(true);
}}

                  className="flex items-center space-x-2 px-4 py-2 bg-orange-500/20 text-orange-300 rounded-lg hover:bg-orange-500/30 transition-colors text-sm backdrop-blur-sm border border-orange-500/30"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  <span>Edit</span>
                </button>
              )
            )}
              {/* Export Button */}
              <button
                onClick={() => {
                  const blob = new Blob([project.documentation], { type: 'text/markdown' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `${project.title.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_documentation.md`;
                  document.body.appendChild(a);
                  a.click();
                  document.body.removeChild(a);
                  URL.revokeObjectURL(url);
                }}
                className="flex items-center space-x-2 px-4 py-2 bg-white/10 text-white/90 rounded-lg hover:bg-white/20 transition-colors text-sm backdrop-blur-sm border border-white/20"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-4-4m4 4l4-4m3 8H5a2 2 0 01-2-2V8a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Export</span>
              </button>
              
              {/* Copy Button */}
              <button
                onClick={async () => {
                  try {
                    const contentToCopy = activeSection?.fullContent || project.documentation;
                    await navigator.clipboard.writeText(contentToCopy);
                    alert('Section copied to clipboard!');
                  } catch (error) {
                    console.error('Failed to copy:', error);
                  }
                }}
                className="flex items-center space-x-2 px-4 py-2 bg-orange-500/20 text-orange-300 rounded-lg hover:bg-orange-500/30 transition-colors text-sm backdrop-blur-sm border border-orange-500/30"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <span>Copy</span>
              </button>
            </div>
          </div>
        </div>
        
        {/* Content and Right Sidebar Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content */}
<div className="flex-1 overflow-hidden">
  {activeTab === 'documentation' ? (
    <div className="flex-1 h-full">
      <div className="flex h-full">
        {/* Documentation Content */}
        <div className="flex-1 overflow-y-auto p-8">
          {project.status === 'processing' ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-orange-500/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                <svg className="animate-spin w-8 h-8 text-orange-400" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Generating Documentation</h3>
              <p className="text-white/70 mb-4">AI is analyzing your code and generating comprehensive documentation...</p>
              <div className="w-64 mx-auto bg-white/20 rounded-full h-2">
                <div 
                  className="h-2 rounded-full bg-gradient-to-r from-orange-500 to-orange-600 transition-all duration-500"
                  style={{ width: `${project.progress || 0}%` }}
                ></div>
              </div>
              <p className="text-sm text-white/60 mt-2">{project.progress || 0}% complete</p>
            </div>
          ) : project.status === 'error' ? (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-red-500/20 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">Documentation Generation Failed</h3>
              <p className="text-white/70 mb-4">{project.error || 'An unknown error occurred'}</p>
              <p className="text-sm text-white/60">Please try regenerating the documentation.</p>
            </div>
          ) : activeSection ? (
            isEditing ? (
    // EDIT MODE: WYSIWYG (contenteditable)
    <div className="max-w-4xl">
      <div className="scroll-mt-8">
        {/* small sticky toolbar at the top of the content area */}
<div className="sticky top-2 z-30 inline-flex items-center gap-1 bg-white/10 border border-white/20 rounded-md px-2 py-1 backdrop-blur-sm">
  {/* Font size */}
  <select
    onChange={(e)=>{
      const px = `${e.target.value}px`;
      applyInlineStyle({ fontSize: px, lineHeight: '1.5' });
      e.target.blur();
    }}
    defaultValue="16"
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
    title="Font size"
  >
    {[12,14,16,18,20,24,28,32].map(size => (
      <option key={size} value={size}>{size}</option>
    ))}
  </select>

  {/* Text color */}
{/* Text color */}
<input
  type="color"
  onChange={(e) => {
    const color = e.target.value;
    document.execCommand('foreColor', false, color);
    editorRef.current?.focus();
  }}
  onInput={(e) => {
    const color = e.target.value;
    document.execCommand('foreColor', false, color);
    editorRef.current?.focus();
  }}
  className="w-8 h-8 p-0 border-none rounded bg-transparent cursor-pointer"
  title="Text color"
/>

  {/* Bold */}
  <button
    onClick={() => document.execCommand('bold')}
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90 font-bold"
    title="Bold"
  >
    B
  </button>

  {/* Italic */}
  <button
    onClick={() => document.execCommand('italic')}
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90 italic"
    title="Italic"
  >
    I
  </button>

{/* WORKING Bullet list */}
<button
  onClick={() => {
    if (!editorRef.current) return;
    
    editorRef.current.focus();
    const selection = window.getSelection();
    
    if (selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    let selectedText = range.toString().trim();
    
    // If no text selected, get the current line
    if (!selectedText) {
      // Expand selection to current line
      const startContainer = range.startContainer;
      const textNode = startContainer.nodeType === 3 ? startContainer : startContainer.firstChild;
      if (textNode && textNode.textContent) {
        selectedText = textNode.textContent.trim() || 'New item';
      } else {
        selectedText = 'New item';
      }
    }
    
    // Create the list HTML
    const listHTML = `
      <ul style="list-style-type: disc; margin: 1rem 0; padding-left: 2rem;">
        <li style="display: list-item; margin: 0.25rem 0;">${selectedText}</li>
      </ul>
    `;
    
    // Insert the list
    try {
      // Clear the selection
      range.deleteContents();
      
      // Create a temporary div to hold our HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = listHTML;
      
      // Insert the list
      const listElement = tempDiv.firstElementChild;
      range.insertNode(listElement);
      
      // Position cursor at end of list item for continued editing
      const listItem = listElement.querySelector('li');
      const newRange = document.createRange();
      newRange.selectNodeContents(listItem);
      newRange.collapse(false);
      selection.removeAllRanges();
      selection.addRange(newRange);
      
    } catch (error) {
      console.error('List creation failed:', error);
      // Fallback: just insert basic list text
      range.insertNode(document.createTextNode(`• ${selectedText}\n`));
    }
    
    // Trigger the input event to update state
    setEditorHtml(editorRef.current.innerHTML);
  }}
  className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
  title="Bullet List"
>
  • List
</button>

{/* WORKING Numbered list */}
<button
  onClick={() => {
    if (!editorRef.current) return;
    
    editorRef.current.focus();
    const selection = window.getSelection();
    
    if (selection.rangeCount === 0) return;
    
    const range = selection.getRangeAt(0);
    let selectedText = range.toString().trim();
    
    // If no text selected, get the current line
    if (!selectedText) {
      const startContainer = range.startContainer;
      const textNode = startContainer.nodeType === 3 ? startContainer : startContainer.firstChild;
      if (textNode && textNode.textContent) {
        selectedText = textNode.textContent.trim() || 'New item';
      } else {
        selectedText = 'New item';
      }
    }
    
    // Create the list HTML
    const listHTML = `
      <ol style="list-style-type: decimal; margin: 1rem 0; padding-left: 2rem;">
        <li style="display: list-item; margin: 0.25rem 0;">${selectedText}</li>
      </ol>
    `;
    
    // Insert the list
    try {
      // Clear the selection
      range.deleteContents();
      
      // Create a temporary div to hold our HTML
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = listHTML;
      
      // Insert the list
      const listElement = tempDiv.firstElementChild;
      range.insertNode(listElement);
      
      // Position cursor at end of list item for continued editing
      const listItem = listElement.querySelector('li');
      const newRange = document.createRange();
      newRange.selectNodeContents(listItem);
      newRange.collapse(false);
      selection.removeAllRanges();
      selection.addRange(newRange);
      
    } catch (error) {
      console.error('List creation failed:', error);
      // Fallback: just insert basic list text
      range.insertNode(document.createTextNode(`1. ${selectedText}\n`));
    }
    
    // Trigger the input event to update state
    setEditorHtml(editorRef.current.innerHTML);
  }}
  className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
  title="Numbered List"
>
  1. List
</button>

  {/* Clear formatting */}
  <button 
    onClick={() => {
      document.execCommand('removeFormat');
      editorRef.current?.focus();
    }} 
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
    title="Clear Formatting"
  >
    Clear
  </button>

  {/* Undo */}
  <button 
    onClick={() => {
      document.execCommand('undo');
      editorRef.current?.focus();
    }} 
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
    title="Undo"
  >
    Undo
  </button>

  {/* Redo */}
  <button 
    onClick={() => {
      document.execCommand('redo');
      editorRef.current?.focus();
    }} 
    className="px-2 py-1 text-xs bg-white/10 rounded text-white/90"
    title="Redo"
  >
    Redo
  </button>
</div>

        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          dir="ltr"
          className="prose prose-lg max-w-none text-white/90 bg-white/5 border border-white/20 rounded-xl p-4 focus:outline-none text-left"
          style={{ direction: 'ltr', unicodeBidi: 'embed' }}
          onInput={(e) => setEditorHtml(e.currentTarget.innerHTML)}  // update state, but DON'T re-inject HTML
        />

        <p className="text-xs text-white/50 mt-2">Editing inline. Use the toolbar above. “Save” will store this section as rich HTML.</p>
      </div>
    </div>
  ) : (

    // VIEW MODE
    <div className="max-w-4xl">
      <div id={`section-${activeSection.id}`} className="scroll-mt-8">
        <div ref={contentViewRef} className="prose prose-lg max-w-none text-white/90">
          <MarkdownRenderer content={activeSection.fullContent} onFileClick={openFileViewer} />
        </div>
      </div>
    </div>
  )
          ) : (
            <div className="text-center py-16">
              <div className="w-16 h-16 mx-auto mb-4 bg-white/10 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-white mb-2">No Content Available</h3>
              <p className="text-white/70">Documentation content is not available for this project.</p>
            </div>
          )}
        </div>
        
        {/* Right Sidebar - Subsection Navigation - Only show for documentation tab */}
        {activeSection && activeSection.subsections && activeSection.subsections.length > 0 && (
          <SubsectionSidebar
            subsections={activeSection.subsections}
            activeSubsectionId={activeSubsectionId}
            onSubsectionSelect={(subsectionId) => setActiveSubsectionId(subsectionId)}
          />
        )}
      </div>
    </div>
  ) : (
    /* Diagrams Tab */
    <div className="h-full">
      <DiagramViewer 
        diagrams={diagrams}
        project={project}
        isAdmin={isAdmin}
        isLoading={diagramsLoading}
      />
    </div>
  )}
</div>
        </div>
      </div>
            {/* Edit Modal */}

      <FileViewerModal
  open={fileModalOpen}
  fileName={fileModalName}
  loading={fileModalLoading}
  content={fileModalContent}
  onClose={() => setFileModalOpen(false)}
/>
    </div>
  );
}

// --- File Viewer Modal ---
function FileViewerModal({ open, fileName, loading, content, onClose }) {
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[9999] bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-5xl max-h-[90vh] bg-[#0f1620] border border-white/15 rounded-2xl overflow-hidden flex flex-col shadow-2xl">
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="px-2 py-1 text-xs rounded bg-white/10 text-white/70 border border-white/10">FILE</div>
            <h3 className="text-white font-semibold">{fileName}</h3>
          </div>
          <button className="text-white/70 hover:text-white" onClick={onClose} aria-label="Close">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full" />
            </div>
          ) : (
            <pre className="bg-black/40 border border-white/10 text-green-300 text-sm rounded-xl p-4 whitespace-pre-wrap leading-relaxed overflow-auto">
              {content || 'No content available'}
            </pre>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
}



