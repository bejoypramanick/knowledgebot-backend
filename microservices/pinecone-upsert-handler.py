#!/usr/bin/env python3
"""
Pinecone Vector Upsert - Single Purpose Lambda
Upserts vectors to Pinecone database
"""

import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Pinecone
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    pinecone_index = pc.Index(os.environ.get('PINECONE_INDEX_NAME'))
    logger.info("Pinecone initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {e}")
    pinecone_index = None

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Upsert vectors to Pinecone database"""
    logger.info("=== PINECONE UPSERT STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        vectors = body.get('vectors', [])
        namespace = body.get('namespace', '')
        
        if not vectors:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Vectors are required"})
            }
        
        if not pinecone_index:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Pinecone not available"})
            }
        
        # Upsert vectors
        upsert_response = pinecone_index.upsert(
            vectors=vectors,
            namespace=namespace if namespace else None
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "upserted_count": upsert_response.upserted_count,
                "namespace": namespace,
                "total_vectors": len(vectors)
            })
        }
        
    except Exception as e:
        logger.error(f"Error upserting to Pinecone: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
