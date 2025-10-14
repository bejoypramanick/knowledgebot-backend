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
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

def call_sentence_transformer_library(texts: List[str]) -> List[List[float]]:
    """Call Sentence Transformer library Lambda for query embeddings"""
    try:
        logger.info(f"🔧 Calling Sentence Transformer library for query embedding")
        
        payload = {
            'texts': texts
        }
        
        # Get Sentence Transformer library function name from environment
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
                logger.info(f"✅ Sentence Transformer library generated query embedding")
                return st_result['embeddings'][0]  # Return first (and only) embedding
            else:
                logger.error(f"❌ Sentence Transformer library failed: {st_result.get('error')}")
                raise Exception(f"Sentence Transformer failed: {st_result.get('error')}")
        else:
            logger.error(f"❌ Sentence Transformer library Lambda call failed: {result}")
            raise Exception(f"Sentence Transformer Lambda call failed: {result}")
            
    except Exception as e:
        logger.error(f"❌ Error calling Sentence Transformer library: {e}")
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
    """Perform RAG search using vector similarity and graph relations - BUSINESS LOGIC"""
    try:
        logger.info(f"🔍 Starting RAG search for query: {query[:50]}...")
        
        # Step 1: Generate query embedding
        logger.info("🧠 Step 1: Generating query embedding")
        query_embedding = call_sentence_transformer_library([query])
        
        # Step 2: Search Pinecone for similar chunks
        logger.info("🔍 Step 2: Searching Pinecone for similar chunks")
        pinecone_result = call_pinecone_library(query_embedding, limit)
        
        # Step 3: Search Neo4j for related documents
        logger.info("🕸️ Step 3: Searching Neo4j for related documents")
        neo4j_query = """
        MATCH (d:Document)-[:CONTAINS]->(c:Chunk)
        WHERE c.text CONTAINS $query
        RETURN d.id as document_id, d.filename, c.text as chunk_text, c.type as chunk_type
        LIMIT $limit
        """
        neo4j_result = call_neo4j_library(neo4j_query, {'query': query, 'limit': limit})
        
        # Step 4: Search DynamoDB for additional context
        logger.info("💾 Step 4: Searching DynamoDB for additional context")
        dynamodb_chunks = search_dynamodb_chunks(query, limit)
        
        # Combine results
        rag_results = {
            "success": True,
            "query": query,
            "vector_results": pinecone_result.get('results', []),
            "graph_results": neo4j_result.get('records', []),
            "dynamodb_results": dynamodb_chunks,
            "total_results": len(pinecone_result.get('results', [])) + len(neo4j_result.get('records', [])) + len(dynamodb_chunks)
        }
        
        logger.info(f"✅ RAG search completed: {rag_results['total_results']} total results")
        return rag_results
        
    except Exception as e:
        logger.error(f"❌ Error in RAG search: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": query
        }

def generate_chat_response(query: str, conversation_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate chat response using RAG and OpenAI - BUSINESS LOGIC"""
    try:
        logger.info(f"💬 Generating chat response for query: {query[:50]}...")
        
        # Step 1: Perform RAG search
        logger.info("🔍 Step 1: Performing RAG search")
        rag_results = perform_rag_search(query, limit=5)
        
        if not rag_results.get('success'):
            raise Exception("RAG search failed")
        
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
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
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
        
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        query = body.get('query', '')
        conversation_history = body.get('conversation_history', [])
        
        if not query:
            logger.warning("⚠️ No query provided in request")
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
        
        # Generate response
        result = generate_chat_response(query, conversation_history)
        
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
        logger.error(f"💥 Error in chat orchestrator business logic: {e}")
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
                "error": str(e)
            })
        }
