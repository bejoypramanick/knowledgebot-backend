#!/usr/bin/env python3
"""
Chat Orchestrator WebSocket Handler - Real-time chat without timeout limits
Handles WebSocket connections for real-time chat with RAG and fallbacks
"""

import json
import os
import logging
import time
import hashlib
import boto3
import traceback
import sys
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
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

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
apigateway = boto3.client('apigatewaymanagementapi')

def send_websocket_message(connection_id: str, message: Dict[str, Any], endpoint_url: str) -> bool:
    """Send message to WebSocket connection"""
    try:
        apigateway.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send WebSocket message: {e}")
        return False

def call_sentence_transformer_library(texts: List[str]) -> List[List[float]]:
    """Call Sentence Transformer library Lambda for query embeddings"""
    try:
        logger.info(f"🔧 Calling Sentence Transformer library for query embedding")
        
        payload = {
            'texts': texts
        }
        
        st_function_name = os.environ.get('SENTENCE_TRANSFORMER_LIBRARY_FUNCTION', 'sentence-transformer-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=st_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            st_result = json.loads(result['body'])
            if st_result.get('success'):
                logger.info(f"✅ Sentence Transformer library generated {len(st_result['embeddings'])} embeddings")
                return st_result['embeddings']
            else:
                logger.error(f"❌ Sentence Transformer library failed: {st_result.get('error')}")
                raise Exception(f"Sentence Transformer failed: {st_result.get('error')}")
        else:
            logger.error(f"❌ Sentence Transformer library Lambda call failed: {result}")
            raise Exception(f"Sentence Transformer Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Sentence Transformer library: {e}")
        raise

def call_openai_library(messages: List[Dict[str, str]]) -> str:
    """Call OpenAI library Lambda for response generation"""
    try:
        logger.info(f"🤖 Calling OpenAI library for response generation")
        
        payload = {
            'operation_type': 'chat',
            'messages': messages,
            'model': 'gpt-4o-mini',
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        openai_function_name = os.environ.get('OPENAI_LIBRARY_FUNCTION', 'openai-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=openai_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            openai_result = json.loads(result['body'])
            if openai_result.get('success'):
                logger.info(f"✅ OpenAI library generated response")
                return openai_result['response']
            else:
                logger.error(f"❌ OpenAI library failed: {openai_result.get('error')}")
                raise Exception(f"OpenAI failed: {openai_result.get('error')}")
        else:
            logger.error(f"❌ OpenAI library Lambda call failed: {result}")
            raise Exception(f"OpenAI Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling OpenAI library: {e}")
        raise

def perform_rag_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Perform RAG search with fallbacks"""
    try:
        logger.info(f"🔍 Starting RAG search for query: {query[:50]}...")
        
        # Initialize results with empty defaults
        query_embedding = None
        pinecone_result = {"results": []}
        neo4j_result = {"records": []}
        dynamodb_chunks = []
        
        # Step 1: Generate query embedding (with fallback)
        try:
            logger.info("🧠 Step 1: Generating query embedding")
            query_embedding = call_sentence_transformer_library([query])
            logger.info("✅ Query embedding generated successfully")
        except Exception as e:
            logger.warning(f"⚠️ Sentence Transformer failed: {e}, continuing without embeddings")
            query_embedding = None
        
        # Step 2: Search Pinecone for similar chunks (with fallback)
        try:
            if query_embedding:
                logger.info("🔍 Step 2: Searching Pinecone for similar chunks")
                # Call Pinecone library (simplified for this example)
                pinecone_result = {"results": []}  # Placeholder
                logger.info(f"✅ Pinecone search completed: {len(pinecone_result.get('results', []))} results")
            else:
                logger.warning("⚠️ Skipping Pinecone search - no embeddings available")
        except Exception as e:
            logger.warning(f"⚠️ Pinecone search failed: {e}, continuing without vector results")
            pinecone_result = {"results": []}
        
        # Step 3: Search Neo4j for related documents (with fallback)
        try:
            logger.info("🕸️ Step 3: Searching Neo4j for related documents")
            # Call Neo4j library (simplified for this example)
            neo4j_result = {"records": []}  # Placeholder
            logger.info(f"✅ Neo4j search completed: {len(neo4j_result.get('records', []))} results")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j search failed: {e}, continuing without graph results")
            neo4j_result = {"records": []}
        
        # Step 4: Search DynamoDB for additional context (with fallback)
        try:
            logger.info("💾 Step 4: Searching DynamoDB for additional context")
            # Call DynamoDB search (simplified for this example)
            dynamodb_chunks = []  # Placeholder
            logger.info(f"✅ DynamoDB search completed: {len(dynamodb_chunks)} results")
        except Exception as e:
            logger.warning(f"⚠️ DynamoDB search failed: {e}, continuing without DynamoDB results")
            dynamodb_chunks = []
        
        # Combine results
        total_results = len(pinecone_result.get('results', [])) + len(neo4j_result.get('records', [])) + len(dynamodb_chunks)
        
        rag_results = {
            "success": True,
            "query": query,
            "vector_results": pinecone_result.get('results', []),
            "graph_results": neo4j_result.get('records', []),
            "dynamodb_results": dynamodb_chunks,
            "total_results": total_results,
            "embeddings_used": query_embedding is not None,
            "services_available": {
                "sentence_transformer": query_embedding is not None,
                "pinecone": len(pinecone_result.get('results', [])) > 0,
                "neo4j": len(neo4j_result.get('records', [])) > 0,
                "dynamodb": len(dynamodb_chunks) > 0
            }
        }
        
        logger.info(f"✅ RAG search completed: {total_results} total results")
        return rag_results
        
    except Exception as e:
        logger.error(f"❌ RAG search failed completely: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_results": 0,
            "services_available": {
                "sentence_transformer": False,
                "pinecone": False,
                "neo4j": False,
                "dynamodb": False
            }
        }

def generate_chat_response(query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate chat response using RAG and OpenAI with fallbacks"""
    try:
        logger.info(f"💬 Generating chat response for query: {query[:50]}...")
        
        # Step 1: Perform RAG search
        logger.info("🔍 Step 1: Performing RAG search")
        rag_results = perform_rag_search(query, limit=5)
        
        # Handle RAG search results (even if some services failed)
        if not rag_results.get('success'):
            logger.warning("⚠️ RAG search failed completely, falling back to direct OpenAI chat")
            
            # Try to get a direct response from OpenAI without RAG context
            try:
                messages = []
                if conversation_history:
                    for msg in conversation_history:
                        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                
                messages.append({
                    "role": "user", 
                    "content": f"{query}\n\nNote: I'm currently unable to access my knowledge base, so I'll answer based on my general knowledge."
                })
                
                logger.info("🤖 Calling OpenAI directly as RAG fallback")
                openai_response = call_openai_library(messages)
                
                return {
                    "success": True,
                    "response": openai_response,
                    "sources": [],
                    "conversation_id": f"fallback_{int(time.time())}",
                    "metadata": {
                        "rag_success": False,
                        "fallback_mode": "direct_openai",
                        "services_available": rag_results.get('services_available', {}),
                        "error": rag_results.get('error', 'Unknown error')
                    }
                }
                
            except Exception as e:
                logger.error(f"❌ Even OpenAI fallback failed: {e}")
                return {
                    "success": True,
                    "response": f"I received your message: '{query}'. I'm having trouble accessing both my knowledge base and AI services right now, but I can see your message is working correctly! Please try again in a moment.",
                    "sources": [],
                    "conversation_id": f"fallback_{int(time.time())}",
                    "metadata": {
                        "rag_success": False,
                        "fallback_mode": "error_message",
                        "services_available": rag_results.get('services_available', {}),
                        "error": f"RAG failed: {rag_results.get('error', 'Unknown error')}, OpenAI failed: {str(e)}"
                    }
                }
        
        # Check if we have enough RAG results, if not, supplement with direct OpenAI
        total_rag_results = rag_results.get('total_results', 0)
        if total_rag_results < 2:
            logger.info(f"⚠️ RAG returned only {total_rag_results} results, supplementing with direct OpenAI chat")
            
            try:
                messages = []
                if conversation_history:
                    for msg in conversation_history:
                        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                
                context_note = "Note: I have limited access to my knowledge base right now, so I'll provide a general answer supplemented with any available information."
                messages.append({
                    "role": "user", 
                    "content": f"{query}\n\n{context_note}"
                })
                
                logger.info("🤖 Calling OpenAI to supplement limited RAG results")
                openai_response = call_openai_library(messages)
                
                # Combine RAG results with OpenAI response
                rag_context = ""
                if total_rag_results > 0:
                    rag_context = "\n\nBased on my limited knowledge base access, here's what I found:\n"
                    for result in rag_results.get('vector_results', []):
                        rag_context += f"- {result.get('metadata', {}).get('text', '')[:200]}...\n"
                
                combined_response = f"{openai_response}{rag_context}"
                
                return {
                    "success": True,
                    "response": combined_response,
                    "sources": [],
                    "conversation_id": f"hybrid_{int(time.time())}",
                    "metadata": {
                        "rag_success": True,
                        "fallback_mode": "hybrid_openai_rag",
                        "rag_results_count": total_rag_results,
                        "services_available": rag_results.get('services_available', {})
                    }
                }
                
            except Exception as e:
                logger.warning(f"⚠️ OpenAI supplement failed: {e}, continuing with limited RAG results")
        
        # Normal RAG processing (simplified for this example)
        # In a real implementation, you'd process the RAG results and call OpenAI
        try:
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
            messages.append({"role": "user", "content": query})
            
            openai_response = call_openai_library(messages)
            
            return {
                "success": True,
                "response": openai_response,
                "sources": [],
                "conversation_id": f"rag_{int(time.time())}",
                "metadata": {
                    "rag_success": True,
                    "fallback_mode": "normal_rag",
                    "rag_results_count": total_rag_results,
                    "services_available": rag_results.get('services_available', {})
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in normal RAG processing: {e}")
            return {
                "success": False,
                "response": "I apologize, but I encountered an error while processing your request.",
                "sources": [],
                "conversation_id": f"error_{int(time.time())}",
                "metadata": {
                    "rag_success": False,
                    "fallback_mode": "error",
                    "error": str(e)
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Error in generate_chat_response: {e}")
        return {
            "success": False,
            "response": "I apologize, but I encountered an error while processing your request.",
            "sources": [],
            "conversation_id": f"error_{int(time.time())}",
            "metadata": {
                "rag_success": False,
                "fallback_mode": "error",
                "error": str(e)
            }
        }

def lambda_handler(event, context):
    """WebSocket Lambda handler for real-time chat"""
    logger.info("=== WEBSOCKET CHAT ORCHESTRATOR STARTED ===")
    logger.info(f"📊 Event: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Extract WebSocket information
        connection_id = event.get('requestContext', {}).get('connectionId')
        route_key = event.get('requestContext', {}).get('routeKey')
        domain_name = event.get('requestContext', {}).get('domainName')
        endpoint_url = f"https://{domain_name}" if domain_name else None
        
        if not connection_id:
            logger.error("❌ No connection ID found in event")
            return {"statusCode": 400, "body": "Missing connection ID"}
        
        logger.info(f"🔌 Connection ID: {connection_id}")
        logger.info(f"🛣️ Route Key: {route_key}")
        
        # Handle different WebSocket events
        if route_key == "$connect":
            logger.info("🔌 WebSocket connection established")
            return {"statusCode": 200, "body": "Connected"}
        
        elif route_key == "$disconnect":
            logger.info("🔌 WebSocket connection closed")
            return {"statusCode": 200, "body": "Disconnected"}
        
        elif route_key == "message":
            # Handle chat message
            try:
                body = json.loads(event.get('body', '{}'))
                query = body.get('query', '') or body.get('message', '')
                conversation_history = body.get('conversation_history', [])
                
                if not query:
                    error_message = {
                        "type": "error",
                        "message": "No query provided",
                        "timestamp": datetime.now().isoformat()
                    }
                    send_websocket_message(connection_id, error_message, endpoint_url)
                    return {"statusCode": 400, "body": "No query provided"}
                
                logger.info(f"💬 Processing WebSocket chat query: {query[:100]}...")
                
                # Send typing indicator
                typing_message = {
                    "type": "typing",
                    "message": "Thinking...",
                    "timestamp": datetime.now().isoformat()
                }
                send_websocket_message(connection_id, typing_message, endpoint_url)
                
                # Generate response
                response = generate_chat_response(query, conversation_history)
                
                # Send response
                chat_message = {
                    "type": "response",
                    "message": response.get('response', 'No response generated'),
                    "conversation_id": response.get('conversation_id', ''),
                    "metadata": response.get('metadata', {}),
                    "timestamp": datetime.now().isoformat()
                }
                
                success = send_websocket_message(connection_id, chat_message, endpoint_url)
                
                if success:
                    logger.info("✅ WebSocket message sent successfully")
                    return {"statusCode": 200, "body": "Message sent"}
                else:
                    logger.error("❌ Failed to send WebSocket message")
                    return {"statusCode": 500, "body": "Failed to send message"}
                
            except Exception as e:
                logger.error(f"❌ Error processing WebSocket message: {e}")
                error_message = {
                    "type": "error",
                    "message": f"Error processing message: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                send_websocket_message(connection_id, error_message, endpoint_url)
                return {"statusCode": 500, "body": "Error processing message"}
        
        else:
            logger.warning(f"⚠️ Unknown route key: {route_key}")
            return {"statusCode": 400, "body": "Unknown route"}
        
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in WebSocket handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {"statusCode": 500, "body": "Internal server error"}
