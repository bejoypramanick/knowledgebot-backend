#!/usr/bin/env python3
"""
OpenAI Library Handler - Docker Lambda
ONLY handles OpenAI library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize OpenAI - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import openai
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    logger.info("✅ OpenAI library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    OPENAI_COMPONENTS = {
        "openai": openai
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI library: {e}")
    OPENAI_COMPONENTS = None

def lambda_handler(event, context):
    """OpenAI Library Handler - ONLY library imports and initialization"""
    logger.info("=== OPENAI LIBRARY HANDLER STARTED ===")
    
    try:
        if OPENAI_COMPONENTS is None:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "OpenAI library not available"
                })
            }
        
        # Return success - library is loaded and ready
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "OpenAI library loaded successfully",
                "components_available": list(OPENAI_COMPONENTS.keys())
            })
        }
        
    except Exception as e:
        logger.error(f"Error in OpenAI library handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
