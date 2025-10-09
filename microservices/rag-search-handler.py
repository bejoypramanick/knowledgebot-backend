#!/usr/bin/env python3
"""
RAG Search Engine - Single Purpose Lambda
Performs RAG search across multiple data sources
"""

import json
import os
from typing import Dict, Any, List
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration
EMBEDDING_SERVICE_URL = os.environ.get('EMBEDDING_SERVICE_URL', '')
PINECONE_SERVICE_URL = os.environ.get('PINECONE_SERVICE_URL', '')
NEO4J_SERVICE_URL = os.environ.get('NEO4J_SERVICE_URL', '')
DYNAMODB_SERVICE_URL = os.environ.get('DYNAMODB_SERVICE_URL', '')

async def call_microservice(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call a microservice"""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()

async def rag_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Perform RAG search"""
    try:
        # Step 1: Generate embedding
        embedding_response = await call_microservice(
            f"{EMBEDDING_SERVICE_URL}/embedding-generator",
            {"text": query}
        )
        
        if not embedding_response.get('success'):
            raise Exception("Failed to generate embedding")
        
        query_vector = embedding_response['embedding']
        
        # Step 2: Search Pinecone
        pinecone_response = await call_microservice(
            f"{PINECONE_SERVICE_URL}/pinecone-search",
            {
                "query_vector": query_vector,
                "limit": limit
            }
        )
        
        if not pinecone_response.get('success'):
            raise Exception("Failed to search Pinecone")
        
        # Step 3: Get chunk details from DynamoDB
        chunk_ids = [match['id'] for match in pinecone_response['results']]
        
        dynamodb_response = await call_microservice(
            f"{DYNAMODB_SERVICE_URL}/dynamodb-crud",
            {
                "operation": "batch_read",
                "table_name": "document_chunks",
                "keys": [{"id": chunk_id} for chunk_id in chunk_ids]
            }
        )
        
        if not dynamodb_response.get('success'):
            raise Exception("Failed to read chunk details")
        
        # Step 4: Search Neo4j for relationships
        neo4j_response = await call_microservice(
            f"{NEO4J_SERVICE_URL}/neo4j-search",
            {
                "cypher_query": """
                MATCH (c:Chunk)-[r]->(related)
                WHERE c.id IN $chunk_ids
                RETURN c, r, related
                LIMIT 10
                """,
                "parameters": {"chunk_ids": chunk_ids}
            }
        )
        
        return {
            "success": True,
            "query": query,
            "pinecone_results": pinecone_response['results'],
            "chunk_details": dynamodb_response['items'],
            "relationships": neo4j_response.get('results', []),
            "total_results": len(pinecone_response['results'])
        }
        
    except Exception as e:
        logger.error(f"Error in RAG search: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Perform RAG search"""
    logger.info("=== RAG SEARCH ENGINE STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        query = body.get('query', '')
        limit = body.get('limit', 5)
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Query is required"})
            }
        
        # Perform RAG search
        import asyncio
        result = asyncio.run(rag_search(query, limit))
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in RAG search engine: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
