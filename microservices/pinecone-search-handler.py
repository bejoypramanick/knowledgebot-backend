#!/usr/bin/env python3
"""
Pinecone Vector Search - Single Purpose Lambda
Searches Pinecone vector database
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
    """Search Pinecone vector database"""
    logger.info("=== PINECONE SEARCH STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        query_vector = body.get('query_vector', [])
        limit = body.get('limit', 10)
        filter_dict = body.get('filter_dict', {})
        namespace = body.get('namespace', '')
        
        if not query_vector:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query vector is required"})
            }
        
        if not pinecone_index:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Pinecone not available"})
            }
        
        # Search Pinecone
        search_response = pinecone_index.query(
            vector=query_vector,
            top_k=limit,
            filter=filter_dict if filter_dict else None,
            namespace=namespace if namespace else None,
            include_metadata=True
        )
        
        # Format results
        results = []
        for match in search_response.matches:
            results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            })
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "results": results,
                "total_results": len(results),
                "namespace": namespace
            })
        }
        
    except Exception as e:
        logger.error(f"Error searching Pinecone: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
