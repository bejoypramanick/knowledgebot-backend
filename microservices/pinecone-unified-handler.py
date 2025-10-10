#!/usr/bin/env python3
"""
Pinecone Unified Handler - Single Purpose Lambda
Handles both Pinecone search and upsert operations
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

def search_pinecone(query_vector: List[float], limit: int = 10, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """Search Pinecone vector database"""
    try:
        if not pinecone_index:
            return {
                "success": False,
                "error": "Pinecone not available"
            }
        
        # Build query parameters
        query_params = {
            'vector': query_vector,
            'top_k': limit,
            'include_metadata': True,
            'include_values': False
        }
        
        if filter_dict:
            query_params['filter'] = filter_dict
        if namespace:
            query_params['namespace'] = namespace
        
        results = pinecone_index.query(**query_params)
        
        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "namespace": namespace
        }
    except Exception as e:
        logger.error(f"Error searching Pinecone: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def upsert_pinecone(vectors: List[Dict[str, Any]], namespace: str = None) -> Dict[str, Any]:
    """Upsert vectors to Pinecone"""
    try:
        if not pinecone_index:
            return {
                "success": False,
                "error": "Pinecone not available"
            }
        
        # Prepare upsert parameters
        upsert_params = {
            'vectors': vectors
        }
        
        if namespace:
            upsert_params['namespace'] = namespace
        
        # Execute upsert
        result = pinecone_index.upsert(**upsert_params)
        
        return {
            "success": True,
            "upserted_count": result.upserted_count,
            "namespace": namespace,
            "vectors_count": len(vectors)
        }
    except Exception as e:
        logger.error(f"Error upserting to Pinecone: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Unified Pinecone handler for both search and upsert operations"""
    logger.info("=== PINECONE UNIFIED HANDLER STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract operation type
        operation_type = body.get('operation_type', 'search')  # 'search' or 'upsert'
        
        if operation_type == 'search':
            # Search operation
            query_vector = body.get('query_vector', [])
            limit = body.get('limit', 10)
            filter_dict = body.get('filter_dict', {})
            namespace = body.get('namespace', '')
            
            if not query_vector:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Credentials": "true"
                    },
                    "body": json.dumps({"error": "Query vector is required for search"})
                }
            
            result = search_pinecone(query_vector, limit, filter_dict, namespace)
            
        elif operation_type == 'upsert':
            # Upsert operation
            vectors = body.get('vectors', [])
            namespace = body.get('namespace', '')
            
            if not vectors:
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                        "Access-Control-Allow-Credentials": "true"
                    },
                    "body": json.dumps({"error": "Vectors are required for upsert"})
                }
            
            result = upsert_pinecone(vectors, namespace)
            
        else:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Credentials": "true"
                },
                "body": json.dumps({"error": "Operation type must be 'search' or 'upsert'"})
            }
        
        return {
            "statusCode": 200 if result["success"] else 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in Pinecone unified handler: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({"error": str(e)})
        }
