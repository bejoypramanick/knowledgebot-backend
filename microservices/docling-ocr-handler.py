#!/usr/bin/env python3
"""
Docling OCR Processor - Single Purpose Lambda
Processes documents using Docling for OCR and structure detection
"""

import json
import os
from typing import Dict, Any, Optional
import logging
import hashlib
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Docling
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.document import DsDocument
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    
    # Initialize converter
    converter = DocumentConverter()
    logger.info("Docling initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docling: {e}")
    converter = None

def process_document_with_docling(document_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process document using Docling"""
    if not converter:
        raise Exception("Docling not available")
    
    # Save bytes to temporary file
    temp_path = f"/tmp/{filename}"
    with open(temp_path, 'wb') as f:
        f.write(document_bytes)
    
    try:
        # Convert document
        doc = converter.convert(temp_path)
        
        # Extract text and structure
        chunks = []
        for element in doc.iterate_items():
            chunk = {
                "text": element.text,
                "type": element.label,
                "page": getattr(element, 'page', None),
                "bbox": getattr(element, 'bbox', None)
            }
            chunks.append(chunk)
        
        return {
            "success": True,
            "chunks": chunks,
            "total_chunks": len(chunks),
            "document_type": "pdf" if filename.lower().endswith('.pdf') else "document"
        }
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process document using Docling OCR"""
    logger.info("=== DOCLING OCR PROCESSOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        document_bytes_b64 = body.get('document_bytes', '')
        filename = body.get('filename', 'document.pdf')
        
        if not document_bytes_b64:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Document bytes are required"})
            }
        
        # Decode base64 document
        import base64
        document_bytes = base64.b64decode(document_bytes_b64)
        
        # Process document
        result = process_document_with_docling(document_bytes, filename)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error processing document with Docling: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
