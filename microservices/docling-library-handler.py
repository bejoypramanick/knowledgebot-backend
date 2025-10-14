#!/usr/bin/env python3
"""
Docling Library Handler - Docker Lambda
ONLY handles Docling library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import logging
import traceback
import sys
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Docling components - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import os
    # Set cache directories to PERSISTENT locations in the image filesystem
    os.environ['TRANSFORMERS_CACHE'] = '/opt/models/transformers_cache'
    os.environ['HF_HOME'] = '/opt/models/huggingface'
    os.environ['DOCLING_CACHE'] = '/opt/models/docling_cache'
    
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.datamodel.document import DsDocument
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    
    # Initialize converter with pre-downloaded models from PERSISTENT cache (should be cached from Docker build)
    logger.info("🔄 Loading pre-downloaded Docling models from persistent cache...")
    converter = DocumentConverter()
    logger.info("✅ Docling library imported and initialized successfully")
    logger.info("✅ Models loaded from persistent cache - no downloads needed")
    
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
    logger.error(f"📊 Error details: {str(e)}")
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
        
        # Log error to centralized system
        log_error(
            'docling-library-handler',
            e,
            context,
            {
                'operation_type': event.get('operation_type', 'unknown'),
                'event_keys': list(event.keys()) if event else [],
                'function_name': 'docling-library-handler'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
