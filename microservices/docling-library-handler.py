#!/usr/bin/env python3
"""
Docling Library Handler - Docker Lambda
ONLY handles Docling library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Docling components - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import os
    # Set cache directories to /tmp which is writable in Lambda
    os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
    os.environ['HF_HOME'] = '/tmp/huggingface'
    os.environ['DOCLING_CACHE'] = '/tmp/docling_cache'
    
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.document import DsDocument
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    
    # Initialize converter with optimized settings
    converter = DocumentConverter()
    logger.info("✅ Docling library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    DOCLING_COMPONENTS = {
        "DocumentConverter": DocumentConverter,
        "InputFormat": InputFormat,
        "PdfPipelineOptions": PdfPipelineOptions,
        "DsDocument": DsDocument,
        "PyPdfiumDocumentBackend": PyPdfiumDocumentBackend,
        "converter": converter
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Docling library: {e}")
    DOCLING_COMPONENTS = None

def lambda_handler(event, context):
    """Docling Library Handler - ONLY library imports and initialization"""
    logger.info("=== DOCLING LIBRARY HANDLER STARTED ===")
    
    try:
        if DOCLING_COMPONENTS is None:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Docling library not available"
                })
            }
        
        # Return success - library is loaded and ready
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Docling library loaded successfully",
                "components_available": list(DOCLING_COMPONENTS.keys())
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Docling library handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
