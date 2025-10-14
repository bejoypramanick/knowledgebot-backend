#!/usr/bin/env python3
"""
Sentence Transformer Library Handler - Docker Lambda
ONLY handles Sentence Transformer library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Sentence Transformer - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import os
    # Set cache directory to /tmp which is writable in Lambda
    os.environ['TRANSFORMERS_CACHE'] = '/tmp/transformers_cache'
    os.environ['HF_HOME'] = '/tmp/huggingface'
    
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2', cache_folder='/tmp/sentence_transformers_cache')
    logger.info("✅ Sentence Transformer library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    SENTENCE_TRANSFORMER_COMPONENTS = {
        "SentenceTransformer": SentenceTransformer,
        "embedding_model": embedding_model
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Sentence Transformer library: {e}")
    SENTENCE_TRANSFORMER_COMPONENTS = None

def lambda_handler(event, context):
    """Sentence Transformer Library Handler - ONLY library imports and initialization"""
    logger.info("=== SENTENCE TRANSFORMER LIBRARY HANDLER STARTED ===")
    
    try:
        if SENTENCE_TRANSFORMER_COMPONENTS is None:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Sentence Transformer library not available"
                })
            }
        
        # Return success - library is loaded and ready
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Sentence Transformer library loaded successfully",
                "components_available": list(SENTENCE_TRANSFORMER_COMPONENTS.keys())
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Sentence Transformer library handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
