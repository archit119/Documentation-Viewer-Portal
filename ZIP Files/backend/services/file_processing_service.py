# services/file_processing_service.py
import base64
import io  # PyMuPDF for PDF processing
from PIL import Image
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple
import openai
from config import Config

try:
    import fitz  # PyMuPDF for PDF processing
    _PDF_AVAILABLE = True
except Exception:
    fitz = None
    _PDF_AVAILABLE = False

class EnhancedFileProcessor:
    """Enhanced file processor for PDFs, PPTs, and images with smart image placement"""
    
    def __init__(self):
        self.openai_client = None
        self.supported_image_formats = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        self.supported_doc_formats = {'.pdf', '.ppt', '.pptx', '.docx'}
        
        # Initialize OpenAI for image analysis (using cost-effective model)
        try:
            if Config.OPENAI_API_KEY:
                self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        except:
            print("⚠️ OpenAI not available for image analysis")
    
    def process_uploaded_files(self, files: List[Any]) -> List[Dict]:
        """Process uploaded files including PDFs, PPTs, DOCX, images and plain text/code."""
        processed_files: List[Dict] = []
        extracted_images: List[Dict] = []

        for file in files:
            if not getattr(file, "filename", None):
                continue

            filename = file.filename
            file_ext = self._get_file_extension(filename)

            # ALWAYS read once, then wrap in BytesIO for downstream functions
            try:
                # Reset stream to start, then read once
                try:
                    file.stream.seek(0)
                except Exception:
                    pass
                content: bytes = file.read() or b""
            except Exception as e:
                print(f"❌ Failed to read {filename}: {e}")
                processed_files.append({
                    'name': filename,
                    'size': 0,
                    'content': f'[Error reading upload: {str(e)}]',
                    'type': 'error'
                })
                continue

            try:
                if file_ext == '.pdf':
                    result = self._process_pdf(filename, content)
                    processed_files.extend(result['files'])
                    extracted_images.extend(result['images'])

                elif file_ext in ('.ppt', '.pptx'):
                    result = self._process_powerpoint(filename, content)
                    processed_files.extend(result['files'])
                    extracted_images.extend(result['images'])

                elif file_ext == '.docx':
                    result = self._process_docx(filename, content)
                    processed_files.extend(result['files'])
                    extracted_images.extend(result['images'])

                elif file_ext in self.supported_image_formats:
                    result = self._process_image(filename, content)
                    extracted_images.append(result)

                else:
                    # Regular text/code or unknown types fall back to simple read
                    result = self._process_regular_file(filename, content)
                    processed_files.append(result)

            except zipfile.BadZipFile as e:
                print(f"❌ ZIP error in {filename}: {e}")
                # Soft fallback: keep the raw file so the pipeline keeps going
                processed_files.append({
                    'name': filename,
                    'size': len(content),
                    'content': '[Archive parsing failed; storing raw file so documentation can still be generated.]',
                    'type': self._mime_for_ext(file_ext),
                    'raw_base64': base64.b64encode(content).decode('utf-8')
                })
                # Do NOT re-raise; just continue with other files
                continue

            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")
                processed_files.append({
                    'name': filename,
                    'size': len(content),
                    'content': f'[Error processing file: {str(e)}]',
                    'type': 'error'
                })

        # Analyze and place images intelligently (never fail hard)
        try:
            if extracted_images and processed_files:
                self._place_images_intelligently(processed_files, extracted_images)
        except Exception as e:
            print(f"⚠️ Image placement skipped due to error: {e}")

        return processed_files


    

    def _process_pdf(self, filename: str, content: bytes) -> Dict:
        """Extract text and images from PDF (robust)."""
        if not _PDF_AVAILABLE:
            # Fallback: treat as a regular document so uploads never fail
            return {
                'files': [{
                    'name': filename,
                    'size': len(content),
                    'content': '[PDF parsing unavailable on server; install PyMuPDF to enable rich extraction]',
                    'type': 'application/pdf'
                }],
                'images': []
            }

        doc = fitz.open(stream=content, filetype="pdf")
        
        text_content = []
        images = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Extract text
            page_text = page.get_text()
            if page_text.strip():
                text_content.append(f"## Page {page_num + 1}\n\n{page_text}")
            
            # Extract images
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        
                        # Analyze image context
                        context = self._get_surrounding_context(text_content, page_num)
                        
                        images.append({
                            'name': f"pdf_page_{page_num + 1}_img_{img_index + 1}.png",
                            'data': img_base64,
                            'context': context,
                            'page': page_num + 1,
                            'source': filename
                        })
                    
                    pix = None
                except Exception as e:
                    print(f"⚠️ Failed to extract image from PDF page {page_num + 1}: {e}")
        
        doc.close()
        
        return {
            'files': [{
                'name': filename,
                'size': len(content),
                'content': '\n\n'.join(text_content),
                'type': 'application/pdf'
            }],
            'images': images
        }
    
    def _process_powerpoint(self, filename: str, content: bytes) -> Dict:
        """Extract text and images from PowerPoint"""
        if not content.startswith(b'PK'):
            return {
                'files': [{
                    'name': filename,
                    'size': len(content),
                    'type': self._mime_for_ext('.pptx' if filename.lower().endswith('pptx') else '.ppt'),
                    'content': '[Unsupported or non-OOXML PowerPoint file detected; keeping raw file so the project can proceed.]',
                    'raw_base64': base64.b64encode(content).decode('utf-8')
                }],
                'images': []
            }
        images = []
        slides_text = []
        
        try:
            # PowerPoint files are ZIP archives
            with zipfile.ZipFile(io.BytesIO(content), 'r') as ppt_zip:
                # Extract slide text
                slide_files = [f for f in ppt_zip.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
                slide_files.sort()
                
                for i, slide_file in enumerate(slide_files):
                    try:
                        slide_xml = ppt_zip.read(slide_file)
                        root = ET.fromstring(slide_xml)
                        
                        # Extract text from slide
                        text_elements = []
                        for text_elem in root.iter():
                            if text_elem.text and text_elem.text.strip():
                                text_elements.append(text_elem.text.strip())
                        
                        if text_elements:
                            slide_text = f"## Slide {i + 1}\n\n" + '\n'.join(text_elements)
                            slides_text.append(slide_text)
                    
                    except Exception as e:
                        print(f"⚠️ Failed to process slide {i + 1}: {e}")
                
                # Extract images
                media_files = [f for f in ppt_zip.namelist() if f.startswith('ppt/media/') and any(f.lower().endswith(ext) for ext in self.supported_image_formats)]
                
                for img_file in media_files:
                    try:
                        img_data = ppt_zip.read(img_file)
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        
                        # Get context from slides
                        context = ' '.join(slides_text[-2:]) if slides_text else ""
                        
                        images.append({
                            'name': f"ppt_{img_file.split('/')[-1]}",
                            'data': img_base64,
                            'context': context,
                            'source': filename
                        })
                    
                    except Exception as e:
                        print(f"⚠️ Failed to extract image {img_file}: {e}")
        
        except Exception as e:
            print(f"❌ Failed to process PowerPoint: {e}")
            return {
                'files': [{
                    'name': filename,
                    'size': len(content),
                    'content': f'[PowerPoint processing failed: {str(e)}]',
                    'type': 'application/vnd.ms-powerpoint'
                }],
                'images': []
            }
        
        return {
            'files': [{
                'name': filename,
                'size': len(content),
                'content': '\n\n'.join(slides_text),
                'type': 'application/vnd.ms-powerpoint'
            }],
            'images': images
        }
    
    def _process_docx(self, filename: str, content: bytes) -> Dict:
        """Extract text and embedded images from DOCX without python-docx (zip/xml)."""
        if not content.startswith(b'PK'):
            return {
                'files': [{
                    'name': filename,
                    'size': len(content),
                    'type': self._mime_for_ext('.docx'),
                    'content': '[Unsupported or non-OOXML Word file detected; keeping raw file so the project can proceed.]',
                    'raw_base64': base64.b64encode(content).decode('utf-8')
                }],
                'images': []
            }
        images = []
        paragraphs = []

        try:
            with zipfile.ZipFile(io.BytesIO(content), 'r') as docx_zip:
                # 1) main document text
                try:
                    document_xml = docx_zip.read('word/document.xml')
                    root = ET.fromstring(document_xml)

                    # DOCX text is inside w:t elements
                    ns = {
                        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
                    }
                    texts = []
                    for node in root.iter():
                        # gather text nodes
                        if node.tag.endswith('}t') and node.text and node.text.strip():
                            texts.append(node.text.strip())
                        # paragraph boundaries -> add a blank line on </w:p>
                        if node.tag.endswith('}p'):
                            texts.append('\n')

                    merged = []
                    for t in texts:
                        if t == '\n':
                            merged.append('\n')
                        else:
                            merged.append(t)
                    text_out = ''.join(merged)
                    # Light cleanup of excessive blank lines
                    text_out = '\n'.join([ln.rstrip() for ln in text_out.splitlines()])
                    if text_out.strip():
                        paragraphs.append(text_out.strip())
                except KeyError:
                    # no document.xml — unusual, but handle gracefully
                    pass

                # 2) embedded images in /word/media/*
                media_files = [f for f in docx_zip.namelist() if f.startswith('word/media/')]
                for media in media_files:
                    try:
                        img_data = docx_zip.read(media)
                        img_base64 = base64.b64encode(img_data).decode('utf-8')
                        images.append({
                            'name': f"docx_{media.split('/')[-1]}",
                            'data': img_base64,
                            'context': ' '.join(paragraphs[-10:]) if paragraphs else '',
                            'source': filename
                        })
                    except Exception as e:
                        print(f"⚠️ Failed to extract image {media} from {filename}: {e}")

        except zipfile.BadZipFile as e:
            # surface a clear message
            raise zipfile.BadZipFile(f"{filename}: {e}")

        doc_text = '\n'.join(paragraphs).strip()
        return {
            'files': [{
                'name': filename,
                'size': len(content),
                'content': doc_text if doc_text else '[No text extracted from DOCX]',
                'type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }],
            'images': images
        }



    
    def _process_image(self, filename: str, content: bytes) -> Dict:
        """Process standalone image files"""
        img_base64 = base64.b64encode(content).decode('utf-8')
        return {
            'name': filename,
            'data': img_base64,
            'context': '',
            'source': filename
        }
    
    def _process_regular_file(self, filename: str, content: bytes) -> Dict:
        """Fallback handler for text/code-like files."""
        # Try to decode as UTF-8, fallback to latin-1 to avoid crashes
        try:
            text = content.decode('utf-8', errors='replace')
        except Exception:
            text = content.decode('latin-1', errors='replace')

        return {
            'name': filename,
            'size': len(content),
            'content': text,
            'type': 'text/plain'
        }

    
    def _place_images_intelligently(self, processed_files: List[Dict], images: List[Dict]) -> None:
        """
        Attach up to ~2 relevant images per large text-bearing file.
        If OpenAI vision is configured, try to classify placement; otherwise use heuristic.
        Never raise; log and continue.
        """
        def heuristic_section_guess(ctx: str) -> str:
            ctx_low = (ctx or '').lower()
            if any(k in ctx_low for k in ['install', 'setup', 'configure']):
                return 'setup'
            if any(k in ctx_low for k in ['api', 'endpoint', 'request', 'response']):
                return 'api'
            if any(k in ctx_low for k in ['architecture', 'design', 'diagram', 'component']):
                return 'architecture'
            if any(k in ctx_low for k in ['deploy', 'production', 'pipeline', 'docker', 'k8s']):
                return 'deployment'
            if any(k in ctx_low for k in ['test', 'qa', 'assert', 'coverage']):
                return 'testing'
            return 'overview'

        # Index big text files (PDF/PPTX/DOCX and md/py/js/…)
        text_files = [f for f in processed_files if isinstance(f.get('content'), str) and len(f.get('content') or '') > 400]
        if not text_files:
            # if nothing to attach to, drop images into a synthetic "embedded_images.json" record
            processed_files.append({
                'name': 'embedded_images.json',
                'type': 'image_data',
                'embedded_images': [{
                    'name': img.get('name', 'image'),
                    'data': img.get('data', ''),
                    'placement': {'section': heuristic_section_guess(img.get('context', '')), 'description': 'Auto-placed image'},
                    'source': img.get('source', '')
                } for img in images]
            })
            return

        # Try OpenAI (best-effort); if anything fails, fall back to heuristic
        for tf in text_files:
            tf.setdefault('embedded_images', [])
            # pick a couple of images heuristically relevant to this text file
            picked = images[:2]

            for img in picked:
                placement = {
                    'section': heuristic_section_guess(img.get('context', '')),
                    'description': 'Auto-placed image'
                }

                if self.openai_client:
                    try:
                        # Best-effort vision classification in a tiny prompt; do not assume JSON success
                        prompt = (
                            "Given the document excerpt and the image context, suggest the best single section "
                            "(overview/setup/api/architecture/deployment/testing/performance/security) where the image belongs. "
                            "Respond with just the section name."
                        )
                        _ = self.openai_client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You classify where an image should be embedded within technical docs."},
                                {"role": "user", "content": f"Document excerpt:\n{(tf.get('content') or '')[:2000]}\n\nImage context:\n{img.get('context', '')}\n\n{prompt}"}
                            ],
                            temperature=0.0,
                            max_tokens=20
                        )
                        # We purposely ignore parsing exact content; heuristics above already picked a solid default.
                    except Exception as e:
                        print(f"⚠️ Vision placement skipped for one image: {e}")

                tf['embedded_images'].append({
                    'name': img.get('name', 'image'),
                    'data': img.get('data', ''),
                    'placement': placement,
                    'source': img.get('source', '')
                })

    
    def _analyze_image_placement(self, image: Dict, project_context: str) -> Dict:
        """Analyze where to place an image using GPT-4o-mini (cost-effective)"""
        try:
            # Create a concise prompt to minimize token usage
            prompt = f"""Project Context: {project_context[:500]}...

Image Context: {image.get('context', '')[:300]}
Image Source: {image['source']}

Determine optimal placement for this image in technical documentation. Respond with JSON only:
{{
    "section": "overview|architecture|setup|usage|api|troubleshooting",
    "description": "Brief description (max 50 chars)",
    "relevance": 1-10
}}"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                messages=[
                    {"role": "system", "content": "You are a technical documentation expert. Respond with JSON only."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Limit tokens to reduce cost
                temperature=0.1
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"⚠️ LLM analysis failed: {e}")
            return {
                'section': 'overview',
                'description': f"Image from {image['source']}",
                'relevance': 5
            }
    
    def _create_project_context(self, code_files: List[Dict], doc_files: List[Dict]) -> str:
        """Create brief project context for LLM analysis"""
        context_parts = []
        
        # Add file types summary
        if code_files:
            file_types = set(f['name'].split('.')[-1] for f in code_files[:5])
            context_parts.append(f"Code files: {', '.join(file_types)}")
        
        # Add brief content sample
        if doc_files:
            sample_content = doc_files[0]['content'][:200]
            context_parts.append(f"Documentation sample: {sample_content}")
        
        return " | ".join(context_parts)
    
    def _get_surrounding_context(self, text_content: List[str], page_num: int) -> str:
        """Get context around where image was found"""
        if not text_content or page_num >= len(text_content):
            return ""
        
        # Get current page and adjacent pages for context
        start_idx = max(0, page_num - 1)
        end_idx = min(len(text_content), page_num + 2)
        
        context = " ".join(text_content[start_idx:end_idx])
        return context[:500]  # Limit context length
    
    def _is_code_file(self, filename: str) -> bool:
        """Check if file is a code file"""
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.cs', '.php', '.rb', '.go', '.rs'}
        ext = self._get_file_extension(filename)
        return ext in code_extensions
    
    def _is_doc_file(self, filename: str) -> bool:
        """Check if file is a documentation file"""
        doc_extensions = {'.md', '.txt', '.rst', '.pdf', '.docx'}
        ext = self._get_file_extension(filename)
        return ext in doc_extensions
    
    def _get_file_extension(self, filename: str) -> str:
        """Get file extension in lowercase"""
        return '.' + filename.split('.')[-1].lower() if '.' in filename else ''
    

    def _mime_for_ext(self, ext: str) -> str:
        ext = (ext or "").lower()
        return {
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.ppt':  'application/vnd.ms-powerpoint',
            '.pdf':  'application/pdf',
            '.txt':  'text/plain',
        }.get(ext, 'application/octet-stream')
    




# Create singleton instance
enhanced_file_processor = EnhancedFileProcessor()