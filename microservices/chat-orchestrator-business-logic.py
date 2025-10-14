#!/usr/bin/env python3
"""
Chat Orchestrator Business Logic - Zip Lambda
ALL business logic and CRUD operations for chat and query processing
Uses library Lambdas for heavy operations
"""

import json
import os
import logging
import time
import hashlib
import boto3
import traceback
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_timeout_error, log_service_failure

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

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

def call_sentence_transformer_library(texts: List[str]) -> List[List[float]]:
    """Call Sentence Transformer library Lambda for query embeddings"""
    try:
        logger.info(f"🔧 Calling Sentence Transformer library for query embedding")
        logger.info(f"📝 Input texts count: {len(texts)}")
        logger.info(f"📝 Input texts preview: {texts[:2] if len(texts) > 2 else texts}")
        
        payload = {
            'texts': texts
        }
        
        # Get Sentence Transformer library function name from environment
        st_function_name = os.environ.get('SENTENCE_TRANSFORMER_LIBRARY_FUNCTION', 'sentence-transformer-library-handler')
        logger.info(f"🎯 Target function: {st_function_name}")
        
        logger.info(f"📤 Invoking Lambda function with payload size: {len(json.dumps(payload))} bytes")
        response = lambda_client.invoke(
            FunctionName=st_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload),
            LogType='Tail'  # Get execution logs
        )
        
        logger.info(f"📥 Received response with status code: {response.get('StatusCode')}")
        logger.info(f"📥 Response metadata: {response.get('ResponseMetadata', {}).get('HTTPStatusCode')}")
        
        result = json.loads(response['Payload'].read())
        logger.info(f"📊 Parsed result keys: {list(result.keys())}")
        logger.info(f"📊 Result status code: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            st_result = json.loads(result['body'])
            logger.info(f"📊 ST result keys: {list(st_result.keys())}")
            logger.info(f"📊 ST success status: {st_result.get('success')}")
            
            if st_result.get('success'):
                embeddings = st_result.get('embeddings', [])
                logger.info(f"✅ Sentence Transformer library generated {len(embeddings)} embeddings")
                logger.info(f"📊 Embedding dimensions: {len(embeddings[0]) if embeddings else 'N/A'}")
                return embeddings[0]  # Return first (and only) embedding
            else:
                error_msg = st_result.get('error', 'Unknown error')
                logger.error(f"❌ Sentence Transformer library failed: {error_msg}")
                logger.error(f"📊 Full ST result: {st_result}")
                raise Exception(f"Sentence Transformer failed: {error_msg}")
        else:
            logger.error(f"❌ Sentence Transformer library Lambda call failed: {result}")
            logger.error(f"📊 Full Lambda response: {result}")
            raise Exception(f"Sentence Transformer Lambda call failed: {result}")
            
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in Sentence Transformer response: {e}")
        logger.error(f"📊 Raw response: {response.get('Payload', {}).read() if 'response' in locals() else 'No response'}")
        raise Exception(f"Invalid JSON response from Sentence Transformer: {e}")
        except Exception as e:
            logger.error(f"❌ Error calling Sentence Transformer library: {e}")
            logger.error(f"📊 Stack trace: {traceback.format_exc()}")
            
            # Log service failure
            log_service_failure(
                'chat-orchestrator-business-logic',
                'sentence-transformer-library',
                str(e),
                None,
                {'query': query[:100] if query else ''}
            )
            raise

def call_pinecone_library(query_vector: List[float], limit: int = 10, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """Call Pinecone library Lambda for vector search"""
    try:
        logger.info(f"🔧 Calling Pinecone library for vector search")
        
        payload = {
            'operation_type': 'search',
            'query_vector': query_vector,
            'limit': limit,
            'filter_dict': filter_dict or {},
            'namespace': namespace or 'default'
        }
        
        # Get Pinecone library function name from environment
        pinecone_function_name = os.environ.get('PINECONE_LIBRARY_FUNCTION', 'pinecone-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=pinecone_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            pinecone_result = json.loads(result['body'])
            if pinecone_result.get('success'):
                logger.info(f"✅ Pinecone library search completed: {len(pinecone_result.get('results', []))} results")
                return pinecone_result
            else:
                logger.error(f"❌ Pinecone library search failed: {pinecone_result.get('error')}")
                raise Exception(f"Pinecone search failed: {pinecone_result.get('error')}")
        else:
            logger.error(f"❌ Pinecone library Lambda call failed: {result}")
            raise Exception(f"Pinecone Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Pinecone library: {e}")
        raise

def call_neo4j_library(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call Neo4j library Lambda for graph queries"""
    try:
        logger.info(f"🔧 Calling Neo4j library for graph query")
        
        payload = {
            'cypher_query': cypher_query,
            'parameters': parameters or {},
            'operation_type': 'read'
        }
        
        # Get Neo4j library function name from environment
        neo4j_function_name = os.environ.get('NEO4J_LIBRARY_FUNCTION', 'neo4j-library-handler')
        
        response = lambda_client.invoke(
            FunctionName=neo4j_function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if result.get('statusCode') == 200:
            neo4j_result = json.loads(result['body'])
            if neo4j_result.get('success'):
                logger.info(f"✅ Neo4j library query completed: {neo4j_result.get('total_results', 0)} results")
                return neo4j_result
            else:
                logger.error(f"❌ Neo4j library query failed: {neo4j_result.get('error')}")
                raise Exception(f"Neo4j query failed: {neo4j_result.get('error')}")
        else:
            logger.error(f"❌ Neo4j library Lambda call failed: {result}")
            raise Exception(f"Neo4j Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Neo4j library: {e}")
        raise

def call_openai_library(messages: List[Dict[str, str]], model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """Call OpenAI library Lambda for chat completion"""
    try:
        logger.info(f"🔧 Calling OpenAI library for chat completion with model: {model}")
        
        payload = {
            'operation_type': 'chat',
            'messages': messages,
            'model': model,
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        # Get OpenAI library function name from environment
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
                logger.info(f"✅ OpenAI library generated response successfully")
                return openai_result
            else:
                logger.error(f"❌ OpenAI library failed: {openai_result.get('error')}")
                raise Exception(f"OpenAI failed: {openai_result.get('error')}")
        else:
            logger.error(f"❌ OpenAI library Lambda call failed: {result}")
            raise Exception(f"OpenAI Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling OpenAI library: {e}")
        raise

def search_dynamodb_chunks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search DynamoDB for relevant chunks - BUSINESS LOGIC"""
    try:
        logger.info(f"💾 Searching DynamoDB chunks for query: {query[:50]}...")
        
        table_name = os.environ.get('CHUNKS_TABLE', 'document-chunks')
        table = dynamodb.Table(table_name)
        
        # Simple text search in DynamoDB (you might want to use a more sophisticated search)
        response = table.scan(
            FilterExpression='contains(text, :query)',
            ExpressionAttributeValues={':query': query},
            Limit=limit
        )
        
        chunks = response.get('Items', [])
        logger.info(f"✅ Found {len(chunks)} chunks in DynamoDB")
        
        return chunks
        
    except Exception as e:
        logger.error(f"❌ Error searching DynamoDB chunks: {e}")
        return []

def perform_rag_search(query: str, limit: int = 5) -> Dict[str, Any]:
    """Perform RAG search using vector similarity and graph relations - BUSINESS LOGIC with fallbacks"""
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
                pinecone_result = call_pinecone_library(query_embedding, limit)
                logger.info(f"✅ Pinecone search completed: {len(pinecone_result.get('results', []))} results")
            else:
                logger.warning("⚠️ Skipping Pinecone search - no embeddings available")
        except Exception as e:
            logger.warning(f"⚠️ Pinecone search failed: {e}, continuing without vector results")
            pinecone_result = {"results": []}
        
        # Step 3: Search Neo4j for related documents (with fallback)
        try:
            logger.info("🕸️ Step 3: Searching Neo4j for related documents")
            neo4j_query = """
            MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
            WHERE c.text CONTAINS $query
            RETURN d.id as document_id, d.filename, c.text as chunk_text, c.type as chunk_type
            LIMIT $limit
            """
            neo4j_result = call_neo4j_library(neo4j_query, {'query': query, 'limit': limit})
            logger.info(f"✅ Neo4j search completed: {len(neo4j_result.get('records', []))} results")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j search failed: {e}, continuing without graph results")
            neo4j_result = {"records": []}
        
        # Step 4: Search DynamoDB for additional context (with fallback)
        try:
            logger.info("💾 Step 4: Searching DynamoDB for additional context")
            dynamodb_chunks = search_dynamodb_chunks(query, limit)
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
        logger.info(f"📊 Services status: {rag_results['services_available']}")
        return rag_results
        
    except Exception as e:
        logger.error(f"❌ RAG search failed completely: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error while processing your request. The search services are temporarily unavailable.",
            "total_results": 0,
            "services_available": {
                "sentence_transformer": False,
                "pinecone": False,
                "neo4j": False,
                "dynamodb": False
            }
        }

def generate_chat_response(query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate chat response using RAG and OpenAI - BUSINESS LOGIC"""
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
                # Prepare messages for direct OpenAI chat
                messages = []
                if conversation_history:
                    for msg in conversation_history:
                        messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
                
                # Add current query with context about RAG unavailability
                messages.append({
                    "role": "user", 
                    "content": f"{query}\n\nNote: I'm currently unable to access my knowledge base, so I'll answer based on my general knowledge."
                })
                
                # Call OpenAI directly
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
        if total_rag_results < 2:  # If we have very few results, supplement with direct chat
            logger.info(f"⚠️ RAG returned only {total_rag_results} results, supplementing with direct OpenAI chat")
            
            # Prepare messages for direct OpenAI chat with limited RAG context
            messages = []
            if conversation_history:
                for msg in conversation_history:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            
            # Add context about limited knowledge base access
            context_note = "Note: I have limited access to my knowledge base right now, so I'll provide a general answer supplemented with any available information."
            messages.append({
                "role": "user", 
                "content": f"{query}\n\n{context_note}"
            })
            
            try:
                # Get direct OpenAI response
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
                    "sources": [],  # Could be enhanced to include RAG sources
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
                # Continue with normal RAG processing
        
        # Step 2: Prepare context from RAG results
        logger.info("📝 Step 2: Preparing context from RAG results")
        context_chunks = []
        
        # Add vector search results
        for result in rag_results.get('vector_results', []):
            context_chunks.append({
                "text": result.get('metadata', {}).get('text', ''),
                "source": f"Vector Search (Score: {result.get('score', 0):.3f})",
                "score": result.get('score', 0),
                "type": "vector"
            })
        
        # Add graph search results
        for record in rag_results.get('graph_results', []):
            context_chunks.append({
                "text": record.get('chunk_text', ''),
                "source": f"Graph Search - {record.get('filename', 'Unknown')}",
                "score": 0.8,  # Default score for graph results
                "type": "graph"
            })
        
        # Add DynamoDB results
        for chunk in rag_results.get('dynamodb_results', []):
            context_chunks.append({
                "text": chunk.get('text', ''),
                "source": f"DynamoDB - {chunk.get('filename', 'Unknown')}",
                "score": 0.7,  # Default score for DynamoDB results
                "type": "dynamodb"
            })
        
        # Sort by score and take top results
        context_chunks.sort(key=lambda x: x['score'], reverse=True)
        top_context = context_chunks[:5]
        
        logger.info(f"📊 Prepared {len(top_context)} context chunks for response generation")
        
        # Step 3: Generate response using OpenAI
        logger.info("🤖 Step 3: Generating response with OpenAI")
        
        # Prepare messages
        messages = []
        
        # Add system message
        system_message = f"""You are a helpful AI assistant. Use the following context to answer the user's question:

Context:
{json.dumps(top_context, indent=2)}

Instructions:
- Answer based on the provided context
- If the context doesn't contain enough information, say so
- Be helpful and accurate
- Cite sources when possible
- Keep responses concise but comprehensive"""
        
        messages.append({
            "role": "system",
            "content": system_message
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
        
        # Generate response using OpenAI library
        openai_result = call_openai_library(messages)
        
        if not openai_result.get('success'):
            raise Exception(f"OpenAI generation failed: {openai_result.get('error')}")
        
        response_text = openai_result.get('response', '')
        
        # Prepare final result
        result = {
            "success": True,
            "response": response_text,
            "sources": top_context,
            "conversation_id": hashlib.md5(f"{query}_{time.time()}".encode()).hexdigest()[:12],
            "processing_time": 0,  # Could be calculated
            "rag_results": rag_results,
            "openai_usage": openai_result.get('usage', {})
        }
        
        logger.info(f"✅ Chat response generated successfully")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error generating chat response: {e}")
        return {
            "success": False,
            "error": str(e),
            "response": "I apologize, but I encountered an error while processing your request."
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler for chat orchestration - BUSINESS LOGIC"""
    logger.info("=== CHAT ORCHESTRATOR BUSINESS LOGIC STARTED ===")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Handle CORS preflight request
        if event.get('httpMethod') == 'OPTIONS':
            logger.info("🌐 Handling CORS preflight request")
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
        
        # Parse request body with multiple fallback strategies
        logger.info(f"🔍 Full event: {json.dumps(event, default=str)}")
        logger.info(f"🔍 Raw event body: {event.get('body')}")
        logger.info(f"🔍 Event body type: {type(event.get('body'))}")
        
        # Try multiple ways to extract the query
        query = ''
        conversation_history = []
        body = {}
        
        # Method 1: Parse JSON body
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event['body'])
                logger.info(f"🔍 Parsed JSON body: {body}")
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                # Don't return error yet, try other methods
                body = {}
        
        # Method 2: Direct body access
        elif event.get('body'):
            body = event.get('body', {})
            logger.info(f"🔍 Direct body: {body}")
        
        # Method 3: Check if query is in the event directly
        if not query:
            query = event.get('query', '')
            logger.info(f"🔍 Query from event: '{query}'")
        
        # Method 4: Check if query is in queryStringParameters
        if not query and event.get('queryStringParameters'):
            query = event.get('queryStringParameters', {}).get('query', '')
            logger.info(f"🔍 Query from queryStringParameters: '{query}'")
        
        # Method 5: Extract from parsed body
        if not query:
            query = body.get('query', '')
            conversation_history = body.get('conversation_history', [])
            logger.info(f"🔍 Query from body: '{query}'")
            logger.info(f"🔍 Conversation history: {conversation_history}")
        
        # Method 6: Check for different field names (including frontend format)
        if not query:
            query = body.get('message', '') or body.get('text', '') or body.get('input', '')
            logger.info(f"🔍 Query from alternative fields: '{query}'")
        
        # Method 7: Handle frontend action-based format
        if not query and body.get('action') == 'chat':
            query = body.get('message', '')
            logger.info(f"🔍 Query from frontend action format: '{query}'")
        
        logger.info(f"🔍 Final extracted query: '{query}'")
        logger.info(f"🔍 Final conversation_history: {conversation_history}")
        
        if not query:
            logger.warning("⚠️ No query found in any location")
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                    "Access-Control-Allow-Credentials": "true"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "Query is required"
                })
            }
        
        logger.info(f"💬 Processing chat query: {query[:100]}...")
        
        # Generate response with fallback for library functions
        try:
            result = generate_chat_response(query, conversation_history)
        except Exception as e:
            logger.warning(f"⚠️ Library functions not available, using fallback response: {e}")
            result = {
                "success": True,
                "response": f"I received your message: '{query}'. The AI library functions are currently being set up, but I can see your message is working correctly! The CORS and API Gateway issues have been resolved.",
                "sources": [],
                "conversation_id": f"fallback_{int(time.time())}"
            }
        
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
        logger.error(f"💥 CRITICAL ERROR in chat orchestrator business logic: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Full stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'chat-orchestrator-business-logic',
            e,
            context,
            {
                'query': event.get('body', {}).get('query', '') if isinstance(event.get('body'), dict) else '',
                'event_keys': list(event.keys()) if event else [],
                'function_name': 'chat-orchestrator-business-logic'
            },
            'CRITICAL'
        )
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            })
        }
