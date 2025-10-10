#!/usr/bin/env python3
"""
Embedding Generator - Single Purpose Lambda
Generates embeddings for text using OpenAI or local models
"""

import json
import os
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize embedding model
try:
    embedding_type = os.environ.get('EMBEDDING_TYPE', 'local').lower()
    
    if embedding_type == 'local':
        from sentence_transformers import SentenceTransformer
        model_name = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        embedding_model = SentenceTransformer(model_name)
        logger.info(f"Using local sentence transformers model: {model_name}")
    else:
        import openai
        embedding_model = None
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        logger.info("Using OpenAI embedding API")
except Exception as e:
    logger.error(f"Failed to initialize embedding model: {e}")
    embedding_model = None

def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text"""
    if embedding_type == 'local' and embedding_model:
        return embedding_model.encode(text).tolist()
    elif embedding_type == 'openai':
        import openai
        response = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    else:
        raise Exception("No embedding model available")

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate embedding for input text"""
    logger.info("=== EMBEDDING GENERATOR STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        text = body.get('text', '')
        
        if not text:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Text is required"})
            }
        
        # Generate embedding
        embedding = generate_embedding(text)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({
                "success": True,
                "embedding": embedding,
                "dimensions": len(embedding),
                "text_length": len(text),
                "model_type": embedding_type
            })
        }
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
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
