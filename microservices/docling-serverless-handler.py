#!/usr/bin/env python3
"""
Docling Serverless Handler - Full Document Processing Lambda
Based on aws-serverless-docling repository architecture
Processes documents using Docling for comprehensive extraction
"""

import json
import os
import logging
import base64
import boto3
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile
import hashlib

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# Initialize Docling components
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.document import DsDocument
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    
    # Initialize converter with optimized settings
    converter = DocumentConverter()
    logger.info("Docling initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docling: {e}")
    converter = None

def download_from_s3(bucket: str, key: str) -> bytes:
    """Download file from S3"""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response['Body'].read()
    except Exception as e:
        logger.error(f"Failed to download from S3: {e}")
        raise

def upload_to_s3(bucket: str, key: str, data: bytes) -> str:
    """Upload file to S3"""
    try:
        s3_client.put_object(Bucket=bucket, Key=key, Body=data)
        return f"s3://{bucket}/{key}"
    except Exception as e:
        logger.error(f"Failed to upload to S3: {e}")
        raise

def process_document_with_docling(document_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Process document using Docling with comprehensive extraction"""
    if not converter:
        raise Exception("Docling not available")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
        temp_path = temp_file.name
        temp_file.write(document_bytes)
    
    try:
        logger.info(f"Processing document: {filename}")
        
        # Convert document with Docling
        doc = converter.convert(temp_path)
        
        # Extract comprehensive information
        result = {
            "success": True,
            "document_type": doc.document_type,
            "metadata": {
                "title": getattr(doc, 'title', None),
                "author": getattr(doc, 'author', None),
                "creation_date": getattr(doc, 'creation_date', None),
                "modification_date": getattr(doc, 'modification_date', None),
                "page_count": len(doc.pages) if hasattr(doc, 'pages') else None
            },
            "content": {
                "text": doc.export_to_markdown(),
                "plain_text": doc.export_to_text(),
                "html": doc.export_to_html() if hasattr(doc, 'export_to_html') else None
            },
            "structure": [],
            "tables": [],
            "images": [],
            "chunks": []
        }
        
        # Extract structured elements
        for element in doc.iterate_items():
            element_data = {
                "text": element.text,
                "type": element.label,
                "page": getattr(element, 'page', None),
                "bbox": getattr(element, 'bbox', None),
                "confidence": getattr(element, 'confidence', None)
            }
            
            # Categorize elements
            if element.label in ['table', 'Table']:
                result["tables"].append(element_data)
            elif element.label in ['figure', 'image', 'Image']:
                result["images"].append(element_data)
            else:
                result["structure"].append(element_data)
            
            # Create chunks for RAG
            if element.text and len(element.text.strip()) > 10:
                chunk = {
                    "id": hashlib.md5(element.text.encode()).hexdigest(),
                    "text": element.text.strip(),
                    "type": element.label,
                    "page": getattr(element, 'page', None),
                    "metadata": {
                        "bbox": getattr(element, 'bbox', None),
                        "confidence": getattr(element, 'confidence', None)
                    }
                }
                result["chunks"].append(chunk)
        
        # Add summary statistics
        result["statistics"] = {
            "total_chunks": len(result["chunks"]),
            "total_tables": len(result["tables"]),
            "total_images": len(result["images"]),
            "total_structure_elements": len(result["structure"]),
            "document_size_bytes": len(document_bytes),
            "processing_timestamp": str(doc.creation_time) if hasattr(doc, 'creation_time') else None
        }
        
        logger.info(f"Document processed successfully: {result['statistics']['total_chunks']} chunks extracted")
        return result
        
    except Exception as e:
        logger.error(f"Error processing document: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for document processing"""
    logger.info("=== DOCLING SERVERLESS PROCESSOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Extract parameters
        presigned_url = body.get('presignedUrl') or body.get('presigned_url')
        document_bytes_b64 = body.get('document_bytes')
        filename = body.get('filename', 'document.pdf')
        output_format = body.get('output_format', 'json')
        
        # Validate input
        if not presigned_url and not document_bytes_b64:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Either presignedUrl or document_bytes is required"})
            }
        
        # Get document bytes
        if presigned_url:
            # Parse S3 URL
            if presigned_url.startswith('s3://'):
                url_parts = presigned_url[5:].split('/', 1)
                bucket = url_parts[0]
                key = url_parts[1]
                document_bytes = download_from_s3(bucket, key)
                filename = Path(key).name
            else:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid S3 URL format"})
                }
        else:
            # Decode base64 document
            document_bytes = base64.b64decode(document_bytes_b64)
        
        # Process document
        result = process_document_with_docling(document_bytes, filename)
        
        # Format output based on request
        if output_format == 'markdown':
            output_data = result["content"]["text"]
        elif output_format == 'text':
            output_data = result["content"]["plain_text"]
        elif output_format == 'html':
            output_data = result["content"]["html"]
        else:
            output_data = result
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(output_data, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
