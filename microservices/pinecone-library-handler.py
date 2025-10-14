#!/usr/bin/env python3
"""
Pinecone Library Handler - Docker Lambda
ONLY handles Pinecone library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import os
import logging
import traceback
import sys
from datetime import datetime

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add handler to ensure logs are captured
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        if PINECONE_COMPONENTS is None:
            logger.error("❌ Pinecone components not available - initialization failed")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Pinecone library not available - initialization failed during container startup"
                })
            }
        
        logger.info(f"✅ Pinecone components available: {list(PINECONE_COMPONENTS.keys())}")
        
        # Parse the request
        logger.info(f"📊 Parsing request body...")
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event['body'])
                logger.info(f"✅ Successfully parsed JSON body")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                logger.error(f"📊 Raw body: {event.get('body')}")
                raise Exception(f"Invalid JSON in request body: {e}")
        else:
            body = event.get('body', {})
            logger.info(f"✅ Using direct body object")
        
        logger.info(f"📊 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
        
        # Check if this is a search request
        if 'operation_type' in body and body['operation_type'] == 'search':
            logger.info(f"🔧 Processing vector search request")
            query_vector = body.get('query_vector', [])
            limit = body.get('limit', 10)
            filter_dict = body.get('filter_dict', {})
            namespace = body.get('namespace', 'default')
            
            logger.info(f"📝 Query vector dimensions: {len(query_vector)}")
            logger.info(f"📝 Limit: {limit}")
            logger.info(f"📝 Filter: {filter_dict}")
            logger.info(f"📝 Namespace: {namespace}")
            
            try:
                # Perform vector search
                results = PINECONE_COMPONENTS['pinecone_index'].query(
                    vector=query_vector,
                    top_k=limit,
                    filter=filter_dict if filter_dict else None,
                    namespace=namespace if namespace != 'default' else None
                )
                
                logger.info(f"✅ Successfully performed vector search")
                logger.info(f"📊 Results count: {len(results.matches) if hasattr(results, 'matches') else 'N/A'}")
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "results": {
                            "matches": [
                                {
                                    "id": match.id,
                                    "score": match.score,
                                    "values": match.values,
                                    "metadata": match.metadata
                                } for match in results.matches
                            ] if hasattr(results, 'matches') else [],
                            "namespace": results.namespace if hasattr(results, 'namespace') else namespace
                        }
                    })
                }
            except Exception as e:
                logger.error(f"❌ Error performing vector search: {e}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                raise Exception(f"Failed to perform vector search: {e}")
        else:
            # Return success - library is loaded and ready
            logger.info(f"📊 No search request found, returning library status")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "message": "Pinecone library loaded successfully",
                    "components_available": list(PINECONE_COMPONENTS.keys())
                })
            }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in Pinecone handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": f"Invalid JSON in request: {e}",
                "error_type": "JSONDecodeError"
            })
        }
    except Exception as e:
        logger.error(f"❌ Error in Pinecone library handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            })
        }
