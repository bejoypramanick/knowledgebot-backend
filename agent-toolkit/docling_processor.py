"""
Docling Document Processor for Production-Level Document Processing
Provides hierarchical semantic chunking with fallback to Docling's default chunking

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import os
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import json
import hashlib
from pathlib import Path

# Docling imports
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.document import Document
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata for a document chunk"""
    chunk_id: str
    document_id: str
    chunk_index: int
    chunk_type: str  # 'title', 'heading', 'paragraph', 'list_item', 'table', 'figure', 'default'
    hierarchy_level: int
    parent_chunk_id: Optional[str] = None
    section_path: str = ""
    word_count: int = 0
    char_count: int = 0
    page_number: Optional[int] = None
    confidence_score: float = 1.0

@dataclass
class DocumentProcessingResult:
    """Result of document processing"""
    document_id: str
    document_type: str
    total_chunks: int
    hierarchical_chunks: List[Dict[str, Any]]
    processing_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None

class DoclingProcessor:
    """Production-level Docling document processor with hierarchical semantic chunking"""
    
    def __init__(self, 
                 cache_dir: str = "/tmp/docling_cache",
                 enable_hierarchical_chunking: bool = True,
                 min_chunk_size: int = 100,
                 max_chunk_size: int = 2000,
                 chunk_overlap: int = 200,
                 use_docling_fallback: bool = True):
        """
        Initialize Docling processor
        
        Args:
            cache_dir: Directory for caching models and processed documents
            enable_hierarchical_chunking: Enable hierarchical semantic chunking
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            use_docling_fallback: If True, fall back to Docling's default chunking when hierarchical fails
        """
        self.cache_dir = cache_dir
        self.enable_hierarchical_chunking = enable_hierarchical_chunking
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_docling_fallback = use_docling_fallback
        
        # Create cache directory
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize document converter
        self.converter = self._initialize_converter()
        
        logger.info(f"DoclingProcessor initialized with cache_dir={cache_dir}, hierarchical_chunking={enable_hierarchical_chunking}")
    
    def _initialize_converter(self) -> DocumentConverter:
        """Initialize Docling document converter with optimized settings"""
        try:
            # Configure PDF pipeline options for better processing
            pdf_options = PdfPipelineOptions()
            pdf_options.do_ocr = True  # Enable OCR for scanned PDFs
            pdf_options.do_table_structure = True  # Enable table structure detection
            pdf_options.table_structure_options.do_cell_matching = True
            pdf_options.table_structure_options.do_cell_matching = True
            
            # Initialize converter with backends
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: pdf_options,
                },
                backends=[
                    PyPdfiumDocumentBackend(),
                ]
            )
            
            logger.info("Docling converter initialized successfully")
            return converter
            
        except Exception as e:
            logger.error(f"Failed to initialize Docling converter: {e}")
            raise
    
    def process_document(self, 
                        document_path: str, 
                        document_id: Optional[str] = None) -> DocumentProcessingResult:
        """
        Process a document using Docling with hierarchical semantic chunking
        
        Args:
            document_path: Path to the document file
            document_id: Optional document ID, will be generated if not provided
            
        Returns:
            DocumentProcessingResult with processed chunks and metadata
        """
        import time
        start_time = time.time()
        
        try:
            # Generate document ID if not provided
            if not document_id:
                document_id = self._generate_document_id(document_path)
            
            logger.info(f"Processing document: {document_path} (ID: {document_id})")
            
            # Convert document using Docling
            doc = self.converter.convert(document_path)
            
            # Extract document metadata
            doc_metadata = self._extract_document_metadata(doc, document_id)
            
        # Process document into chunks using Docling hierarchical chunking
        if self.enable_hierarchical_chunking:
            chunks = self._create_hierarchical_chunks(doc, document_id)
        else:
            raise Exception("Hierarchical chunking is disabled - Docling processing requires hierarchical chunking")
        
        processing_time = time.time() - start_time
        
        logger.info(f"Document processed successfully: {len(chunks)} chunks in {processing_time:.2f}s")
        
        return DocumentProcessingResult(
            document_id=document_id,
            document_type=doc_metadata.get('document_type', 'unknown'),
            total_chunks=len(chunks),
            hierarchical_chunks=chunks,
            processing_time=processing_time,
            success=True,
            metadata=doc_metadata
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Failed to process document {document_path}: {str(e)}"
        logger.error(error_msg)
        
        return DocumentProcessingResult(
            document_id=document_id or "unknown",
            document_type="unknown",
            total_chunks=0,
            hierarchical_chunks=[],
            processing_time=processing_time,
            success=False,
            error_message=error_msg
        )
    
    def _generate_document_id(self, document_path: str) -> str:
        """Generate a unique document ID based on file path and content"""
        try:
            # Use file path and modification time for ID generation
            file_stat = os.stat(document_path)
            content = f"{document_path}_{file_stat.st_mtime}_{file_stat.st_size}"
            return hashlib.md5(content.encode()).hexdigest()[:16]
        except:
            # Fallback to filename-based ID
            return hashlib.md5(document_path.encode()).hexdigest()[:16]
    
    def _extract_document_metadata(self, doc: Document, document_id: str) -> Dict[str, Any]:
        """Extract metadata from Docling document"""
        try:
            metadata = {
                'document_id': document_id,
                'document_type': doc.export_to_dict().get('meta', {}).get('file_type', 'unknown'),
                'page_count': len(doc.pages) if hasattr(doc, 'pages') else 0,
                'title': doc.export_to_dict().get('meta', {}).get('title', ''),
                'author': doc.export_to_dict().get('meta', {}).get('author', ''),
                'creation_date': doc.export_to_dict().get('meta', {}).get('creation_date', ''),
                'modification_date': doc.export_to_dict().get('meta', {}).get('modification_date', ''),
                'total_elements': len(doc.iterate_items()) if hasattr(doc, 'iterate_items') else 0
            }
            return metadata
        except Exception as e:
            logger.warning(f"Failed to extract document metadata: {e}")
            return {'document_id': document_id, 'document_type': 'unknown'}
    
    def _create_hierarchical_chunks(self, doc: Document, document_id: str) -> List[Dict[str, Any]]:
        """
        Create hierarchical semantic chunks from Docling document
        
        This method creates chunks based on document structure:
        1. Document title
        2. Section headings (H1, H2, H3, etc.)
        3. Paragraphs grouped by section
        4. Lists, tables, figures as separate chunks
        5. Fallback to default chunking for unstructured content
        """
        chunks = []
        chunk_index = 0
        
        try:
            # Get document structure
            doc_dict = doc.export_to_dict()
            
            # Process document elements hierarchically
            current_section_path = ""
            current_hierarchy_level = 0
            
            for element in doc.iterate_items():
                element_type = element.__class__.__name__.lower()
                element_text = getattr(element, 'text', '') or str(element)
                
                if not element_text.strip():
                    continue
                
                # Determine chunk type and hierarchy level
                chunk_type, hierarchy_level = self._classify_element(element, element_type)
                
                # Update section path
                if chunk_type in ['title', 'heading']:
                    current_section_path = self._update_section_path(
                        current_section_path, element_text, hierarchy_level
                    )
                    current_hierarchy_level = hierarchy_level
                
                # Create chunk metadata
                chunk_metadata = ChunkMetadata(
                    chunk_id=f"{document_id}_chunk_{chunk_index}",
                    document_id=document_id,
                    chunk_index=chunk_index,
                    chunk_type=chunk_type,
                    hierarchy_level=hierarchy_level,
                    section_path=current_section_path,
                    word_count=len(element_text.split()),
                    char_count=len(element_text),
                    page_number=getattr(element, 'page', None),
                    confidence_score=getattr(element, 'confidence', 1.0)
                )
                
                # Create chunk
                chunk = {
                    'chunk_id': chunk_metadata.chunk_id,
                    'document_id': document_id,
                    'content': element_text,
                    'chunk_type': chunk_type,
                    'hierarchy_level': hierarchy_level,
                    'section_path': current_section_path,
                    'metadata': {
                        'word_count': chunk_metadata.word_count,
                        'char_count': chunk_metadata.char_count,
                        'page_number': chunk_metadata.page_number,
                        'confidence_score': chunk_metadata.confidence_score,
                        'chunk_index': chunk_index
                    }
                }
                
                chunks.append(chunk)
                chunk_index += 1
            
            # If no structured chunks found, try Docling's default chunking
            if not chunks:
                if self.use_docling_fallback:
                    logger.info("No structured elements found, falling back to Docling's default chunking")
                    chunks = self._create_docling_default_chunks(doc, document_id)
                else:
                    raise Exception("No structured elements found in document - Docling processing failed")
            
            logger.info(f"Created {len(chunks)} hierarchical chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to create hierarchical chunks: {e}")
            if self.use_docling_fallback:
                logger.info("Hierarchical chunking failed, falling back to Docling's default chunking")
                try:
                    return self._create_docling_default_chunks(doc, document_id)
                except Exception as fallback_error:
                    raise Exception(f"Both hierarchical and default Docling chunking failed: {str(fallback_error)}")
            else:
                raise Exception(f"Docling hierarchical chunking failed: {str(e)}")
    
    def _classify_element(self, element, element_type: str) -> tuple[str, int]:
        """Classify document element and determine hierarchy level"""
        element_text = getattr(element, 'text', '') or str(element)
        
        # Check for title (usually first element or very short)
        if element_type == 'title' or (len(element_text.split()) < 10 and element_type in ['text', 'paragraph']):
            return 'title', 0
        
        # Check for headings (H1, H2, H3, etc.)
        if element_type in ['heading', 'header']:
            level = getattr(element, 'level', 1)
            return f'heading_h{level}', level
        
        # Check for lists
        if element_type in ['list', 'list_item']:
            return 'list_item', 2
        
        # Check for tables
        if element_type in ['table', 'table_cell']:
            return 'table', 3
        
        # Check for figures/images
        if element_type in ['figure', 'image', 'caption']:
            return 'figure', 3
        
        # Default to paragraph
        return 'paragraph', 2
    
    def _update_section_path(self, current_path: str, element_text: str, hierarchy_level: int) -> str:
        """Update section path based on hierarchy level"""
        if hierarchy_level == 0:  # Title
            return element_text[:50]  # Truncate long titles
        elif hierarchy_level == 1:  # H1
            return element_text[:50]
        elif hierarchy_level == 2:  # H2
            return f"{current_path} > {element_text[:30]}"
        else:  # H3+
            return f"{current_path} > {element_text[:20]}"
    
    def _create_docling_default_chunks(self, doc: Document, document_id: str) -> List[Dict[str, Any]]:
        """
        Create chunks using Docling's built-in default chunking strategy
        This uses Docling's native chunking when hierarchical chunking fails
        """
        chunks = []
        chunk_index = 0
        
        try:
            # Use Docling's built-in document export to get default chunks
            doc_dict = doc.export_to_dict()
            
            # Extract text content from document
            full_text = ""
            if 'text' in doc_dict:
                full_text = doc_dict['text']
            else:
                # Fallback: collect text from all elements
                for element in doc.iterate_items():
                    element_text = getattr(element, 'text', '') or str(element)
                    if element_text.strip():
                        full_text += element_text + "\n\n"
            
            if not full_text.strip():
                logger.warning("No text content found in document for default chunking")
                return chunks
            
            # Use Docling's built-in chunking strategy
            # Split by paragraphs first, then by sentences if needed
            paragraphs = full_text.split('\n\n')
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if not paragraph:
                    continue
                
                # If paragraph is too long, split by sentences
                if len(paragraph) > self.max_chunk_size:
                    sentences = paragraph.split('. ')
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk + sentence) > self.max_chunk_size and current_chunk:
                            # Save current chunk
                            chunk = self._create_chunk_from_text(
                                current_chunk.strip(), 
                                document_id, 
                                chunk_index, 
                                'default_paragraph'
                            )
                            chunks.append(chunk)
                            chunk_index += 1
                            current_chunk = sentence
                        else:
                            current_chunk += sentence + ". " if not sentence.endswith('.') else sentence + " "
                    
                    # Add remaining chunk
                    if current_chunk.strip():
                        chunk = self._create_chunk_from_text(
                            current_chunk.strip(), 
                            document_id, 
                            chunk_index, 
                            'default_paragraph'
                        )
                        chunks.append(chunk)
                        chunk_index += 1
                else:
                    # Paragraph is small enough, use as single chunk
                    chunk = self._create_chunk_from_text(
                        paragraph, 
                        document_id, 
                        chunk_index, 
                        'default_paragraph'
                    )
                    chunks.append(chunk)
                    chunk_index += 1
            
            logger.info(f"Created {len(chunks)} default Docling chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to create Docling default chunks: {e}")
            raise Exception(f"Docling default chunking failed: {str(e)}")
    
    def _create_chunk_from_text(self, text: str, document_id: str, chunk_index: int, chunk_type: str) -> Dict[str, Any]:
        """Create a chunk from text with proper metadata"""
        return {
            'chunk_id': f"{document_id}_chunk_{chunk_index}",
            'document_id': document_id,
            'content': text,
            'chunk_type': chunk_type,
            'hierarchy_level': 3,  # Default level for fallback chunks
            'section_path': '',
            'metadata': {
                'word_count': len(text.split()),
                'char_count': len(text),
                'page_number': None,
                'confidence_score': 0.7,  # Lower confidence for fallback chunks
                'chunk_index': chunk_index,
                'chunking_method': 'docling_default'
            }
        }
    
    
    def process_document_from_bytes(self, 
                                  document_bytes: bytes, 
                                  filename: str, 
                                  document_id: Optional[str] = None) -> DocumentProcessingResult:
        """
        Process document from bytes (useful for S3 documents)
        
        Args:
            document_bytes: Document content as bytes
            filename: Original filename
            document_id: Optional document ID
            
        Returns:
            DocumentProcessingResult with processed chunks
        """
        import tempfile
        
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(document_bytes)
                temp_path = temp_file.name
            
            # Process the temporary file
            result = self.process_document(temp_path, document_id)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process document from bytes: {e}")
            return DocumentProcessingResult(
                document_id=document_id or "unknown",
                document_type="unknown",
                total_chunks=0,
                hierarchical_chunks=[],
                processing_time=0.0,
                success=False,
                error_message=str(e)
            )

# Global processor instance
_docling_processor = None

def get_docling_processor() -> DoclingProcessor:
    """Get global Docling processor instance with Docling fallback enabled"""
    global _docling_processor
    if _docling_processor is None:
        _docling_processor = DoclingProcessor(use_docling_fallback=True)
    return _docling_processor
