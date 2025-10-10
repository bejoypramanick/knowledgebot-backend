#!/usr/bin/env python3
"""
Chat Response Generator - Single Purpose Lambda
Generates chat responses using OpenAI
"""

import json
import os
from typing import Dict, Any, List
import logging
import httpx

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuration
RAG_SEARCH_SERVICE_URL = os.environ.get('RAG_SEARCH_SERVICE_URL', '')

async def call_microservice(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call a microservice"""
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        return response.json()

async def generate_chat_response(query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate chat response using RAG and OpenAI"""
    try:
        # Step 1: Perform RAG search
        rag_response = await call_microservice(
            f"{RAG_SEARCH_SERVICE_URL}/rag-search",
            {"query": query, "limit": 5}
        )
        
        if not rag_response.get('success'):
            raise Exception("Failed to perform RAG search")
        
        # Step 2: Prepare context from RAG results
        context_chunks = []
        for chunk in rag_response.get('chunk_details', []):
            context_chunks.append({
                "text": chunk.get('text', ''),
                "source": chunk.get('source', ''),
                "score": chunk.get('score', 0)
            })
        
        # Step 3: Generate response using OpenAI
        import openai
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        
        # Prepare messages
        messages = []
        
        # Add system message
        messages.append({
            "role": "system",
            "content": f"""You are a helpful AI assistant. Use the following context to answer the user's question:

Context:
{json.dumps(context_chunks, indent=2)}

Instructions:
- Answer based on the provided context
- If the context doesn't contain enough information, say so
- Be helpful and accurate
- Cite sources when possible"""
        })
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages
                messages.append(msg)
        
        # Add current query
        messages.append({
            "role": "user",
            "content": query
        })
        
        # Generate response
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1000,
            temperature=0.7
        )
        
        response_text = response.choices[0].message.content
        
        return {
            "success": True,
            "response": response_text,
            "sources": context_chunks,
            "conversation_id": "",  # Could be generated or passed in
            "processing_time": 0,  # Could be calculated
            "rag_results": rag_response
        }
        
    except Exception as e:
        logger.error(f"Error generating chat response: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error while processing your request."
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate chat response"""
    logger.info("=== CHAT RESPONSE GENERATOR STARTED ===")
    
    try:
        # Handle CORS preflight request
        if event.get('httpMethod') == 'OPTIONS':
            logger.info("Handling CORS preflight request")
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Credentials": "true",
                    "Access-Control-Max-Age": "86400"
                },
                "body": ""
            }
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        query = body.get('query', '')
        conversation_history = body.get('conversation_history', [])
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Credentials": "true"
                },
                "body": json.dumps({"error": "Query is required", "success": False})
            }
        
        # Generate response
        import asyncio
        result = asyncio.run(generate_chat_response(query, conversation_history))
        
        return {
            "statusCode": 200,
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
        logger.error(f"Error in chat response generator: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({"error": str(e), "success": False})
        }
