#!/usr/bin/env python3
"""
Chat Orchestrator Business Logic - Optimized for API Gateway 30s timeout
Implements fast model loading and timeout handling for synchronous chat
"""

import json
import os
import logging
import time
import hashlib
import boto3
import traceback
import sys
import signal
from typing import Dict, Any, List, Optional
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

# Initialize AWS clients
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')

class TimeoutError(Exception):
    """Custom timeout exception"""
    pass

def timeout_handler(signum, frame):
    """Handle timeout signal"""
    raise TimeoutError("Operation timed out")

def call_sentence_transformer_library_fast(texts: List[str], timeout: int = 10) -> List[List[float]]:
    """Call Sentence Transformer library Lambda with timeout"""
    try:
        logger.info(f"🔧 Calling Sentence Transformer library for query embedding (timeout: {timeout}s)")
        logger.info(f"📝 Input texts count: {len(texts)}")
        
        payload = {
            'texts': texts
        }
        
        # Get Sentence Transformer library function name from environment
        st_function_name = os.environ.get('SENTENCE_TRANSFORMER_LIBRARY_FUNCTION', 'sentence-transformer-library-handler')
        logger.info(f"🎯 Target function: {st_function_name}")
        
        # Set timeout for Lambda invocation
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            logger.info(f"📤 Invoking Lambda function with payload size: {len(json.dumps(payload))} bytes")
            response = lambda_client.invoke(
                FunctionName=st_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload),
                LogType='Tail'  # Get execution logs
            )
            
            signal.alarm(0)  # Cancel timeout
            
            logger.info(f"📥 Received response with status code: {response.get('StatusCode')}")
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
                
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            logger.warning(f"⏰ Sentence Transformer call timed out after {timeout}s")
            raise TimeoutError(f"Sentence Transformer call timed out after {timeout}s")
            
    except Exception as e:
        logger.error(f"❌ Error calling Sentence Transformer library: {e}")
        raise

def call_openai_library_fast(messages: List[Dict[str, str]], timeout: int = 15) -> str:
    """Call OpenAI library Lambda with timeout"""
    try:
        logger.info(f"🤖 Calling OpenAI library for response generation (timeout: {timeout}s)")
        
        payload = {
            'operation_type': 'chat',
            'messages': messages,
            'model': 'gpt-4o-mini',
            'max_tokens': 1000,
            'temperature': 0.7
        }
        
        # Get OpenAI library function name from environment
        openai_function_name = os.environ.get('OPENAI_LIBRARY_FUNCTION', 'openai-library-handler')
        
        # Set timeout for Lambda invocation
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            response = lambda_client.invoke(
                FunctionName=openai_function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            signal.alarm(0)  # Cancel timeout
            
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
                
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            logger.warning(f"⏰ OpenAI call timed out after {timeout}s")
            raise TimeoutError(f"OpenAI call timed out after {timeout}s")
            
    except Exception as e:
        logger.error(f"❌ Error calling OpenAI library: {e}")
        raise

def generate_fast_response(query: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """Generate response with timeout handling and fallbacks"""
    start_time = time.time()
    
    try:
        # Try to get embeddings with short timeout
        try:
            embeddings = call_sentence_transformer_library_fast([query], timeout=8)
            logger.info(f"✅ Got embeddings in {time.time() - start_time:.2f}s")
        except TimeoutError:
            logger.warning("⏰ Embedding generation timed out, using fallback")
            embeddings = None
        except Exception as e:
            logger.warning(f"⚠️ Embedding generation failed: {e}, using fallback")
            embeddings = None
        
        # Prepare messages for OpenAI
        messages = []
        if conversation_history:
            for msg in conversation_history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": query})
        
        # Try to get OpenAI response with timeout
        try:
            response = call_openai_library_fast(messages, timeout=15)
            logger.info(f"✅ Got OpenAI response in {time.time() - start_time:.2f}s")
        except TimeoutError:
            logger.warning("⏰ OpenAI response timed out, using fallback")
            response = f"I received your message: '{query}'. I'm processing your request but it's taking longer than expected. Please try rephrasing your question or try again in a moment."
        except Exception as e:
            logger.warning(f"⚠️ OpenAI response failed: {e}, using fallback")
            response = f"I received your message: '{query}'. The AI service is temporarily unavailable, but I can see your message is working correctly!"
        
        processing_time = time.time() - start_time
        
        return {
            "success": True,
            "response": response,
            "sources": [],  # Could be enhanced with actual sources
            "metadata": {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "processing_time": processing_time,
                "embeddings_used": embeddings is not None,
                "timeout_occurred": processing_time > 20
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error in fast response generation: {e}")
        return {
            "success": False,
            "response": "I apologize, but I encountered an error while processing your request. Please try again.",
            "sources": [],
            "metadata": {
                "query": query,
                "timestamp": datetime.now().isoformat(),
                "processing_time": time.time() - start_time,
                "error": str(e)
            }
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler optimized for API Gateway 30s timeout"""
    logger.info("=== CHAT ORCHESTRATOR BUSINESS LOGIC (OPTIMIZED) STARTED ===")
    
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
        body = {}
        if isinstance(event.get('body'), str):
            try:
                body = json.loads(event['body'])
            except json.JSONDecodeError as e:
                logger.error(f"❌ JSON decode error: {e}")
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({
                        "success": False,
                        "error": f"Invalid JSON in request body: {e}"
                    })
                }
        else:
            body = event.get('body', {})
        
        # Extract query
        query = body.get('query', '') or body.get('message', '') or body.get('text', '')
        conversation_history = body.get('conversation_history', [])
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": False,
                    "error": "Query is required"
                })
            }
        
        logger.info(f"💬 Processing chat query: {query[:100]}...")
        
        # Set overall timeout (25 seconds to leave buffer for API Gateway)
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(25)
        
        try:
            # Generate response with timeout handling
            result = generate_fast_response(query, conversation_history)
            signal.alarm(0)  # Cancel timeout
            
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
            
        except TimeoutError:
            signal.alarm(0)  # Cancel timeout
            logger.warning("⏰ Overall operation timed out")
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "success": True,
                    "response": "I'm processing your request but it's taking longer than expected. Please try rephrasing your question or try again in a moment.",
                    "sources": [],
                    "metadata": {
                        "query": query,
                        "timestamp": datetime.now().isoformat(),
                        "processing_time": 25,
                        "timeout": True
                    }
                })
            }
        
    except Exception as e:
        logger.error(f"💥 CRITICAL ERROR in optimized chat orchestrator: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
        }
