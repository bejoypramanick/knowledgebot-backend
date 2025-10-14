#!/usr/bin/env python3
"""
Pinecone Library Handler - Docker Lambda
ONLY handles Pinecone library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Pinecone - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    pinecone_index = pc.Index(os.environ.get('PINECONE_INDEX_NAME'))
    logger.info("✅ Pinecone library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    PINECONE_COMPONENTS = {
        "Pinecone": Pinecone,
        "pc": pc,
        "pinecone_index": pinecone_index
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Pinecone library: {e}")
    PINECONE_COMPONENTS = None

def lambda_handler(event, context):
    """Pinecone Library Handler - ONLY library imports and initialization"""
    logger.info("=== PINECONE LIBRARY HANDLER STARTED ===")
    
    try:
        if PINECONE_COMPONENTS is None:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Pinecone library not available"
                })
            }
        
        # Return success - library is loaded and ready
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Pinecone library loaded successfully",
                "components_available": list(PINECONE_COMPONENTS.keys())
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Pinecone library handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
