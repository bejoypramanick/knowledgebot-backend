#!/usr/bin/env python3
"""
Lambda Handlers with CRUD Tools Only
All business logic and formatting handled by AgentBuilder model

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

# Configure logging first
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("✅ Configured logging")

import json
logger.info("✅ Imported json module")

import os
logger.info("✅ Imported os module")

import asyncio
logger.info("✅ Imported asyncio module")

from typing import Dict, Any
logger.info("✅ Imported typing.Dict, Any")

import traceback
logger.info("✅ Imported traceback module")

from datetime import datetime, timedelta
logger.info("✅ Imported datetime module")

import boto3
logger.info("✅ Imported boto3 module")

import uuid
logger.info("✅ Imported uuid module")

# Import our RAG agent
from rag_agent import run_unified_crud_processing, CRUDAgentInput
logger.info("✅ Imported rag_agent modules: run_unified_crud_processing, CRUDAgentInput")

# Initialize AWS clients
s3_client = boto3.client('s3')
logger.info("✅ Initialized S3 client")

async def generate_presigned_url_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Generate presigned URL for document upload"""
    logger.info("=== PRESIGNED URL GENERATION HANDLER STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        filename = body.get('filename', '')
        content_type = body.get('content_type', 'application/octet-stream')
        metadata = body.get('metadata', {})
        
        if not filename:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                    "Access-Control-Allow-Methods": "POST, OPTIONS"
                },
                "body": json.dumps({
                    "error": "Filename is required"
                })
            }
        
        # Generate unique document ID and S3 key
        document_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y/%m/%d")
        s3_key = f"documents/{timestamp}/{document_id}/{filename}"
        
        # Get S3 bucket from environment
        bucket_name = os.environ.get('DOCUMENTS_BUCKET', 'chatbot-documents-ap-south-1')
        
        # Generate presigned URL with CORS headers
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': s3_key,
                'ContentType': content_type,
                'Metadata': {
                    'document_id': document_id,
                    'original_filename': filename,
                    'title': metadata.get('title', filename),
                    'category': metadata.get('category', 'general'),
                    'author': metadata.get('author', 'unknown'),
                    'upload_timestamp': datetime.now().isoformat()
                }
            },
            ExpiresIn=3600  # 1 hour expiration
        )
        
        logger.info(f"Generated presigned URL for document: {document_id}")
        logger.info(f"S3 Key: {s3_key}")
        logger.info(f"Bucket: {bucket_name}")
        
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
                "presigned_url": presigned_url,
                "document_id": document_id,
                "s3_key": s3_key,
                "bucket": bucket_name,
                "expires_in": 3600,
                "metadata": {
                    "document_id": document_id,
                    "original_filename": filename,
                    "title": metadata.get('title', filename),
                    "category": metadata.get('category', 'general'),
                    "author": metadata.get('author', 'unknown'),
                    "upload_timestamp": datetime.now().isoformat()
                }
            })
        }
        
    except Exception as e:
        logger.error("=== ERROR IN PRESIGNED URL GENERATION ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc()
            })
        }

async def knowledge_chat_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Knowledge chat handler - all business logic handled by AgentBuilder model"""
    logger.info("=== KNOWLEDGE CHAT HANDLER STARTED ===")
    logger.info(f"Event received: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        logger.info("Step 1: Extracting query from event")
        # Extract query from event
        if 'body' in event:
            logger.info("Body found in event, parsing JSON")
            body = json.loads(event['body'])
        else:
            logger.info("No body in event, using event directly")
            body = event
        
        logger.info(f"Parsed body: {json.dumps(body, default=str)}")
        
        user_query = body.get('message', body.get('user_query', ''))
        conversation_id = body.get('conversation_id', '')
        conversation_history = body.get('conversation_history', [])
        user_preferences = body.get('user_preferences', {})
        
        logger.info(f"Extracted - User query: {user_query}")
        logger.info(f"Extracted - Conversation ID: {conversation_id}")
        logger.info(f"Extracted - Conversation history length: {len(conversation_history)}")
        logger.info(f"Extracted - User preferences: {user_preferences}")
        
        if not user_query:
            logger.error("No user query provided")
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "User query is required"
                })
            }
        
        logger.info("Step 2: Creating CRUDAgentInput")
        # Create knowledge agent input
        knowledge_input = CRUDAgentInput(
            user_query=user_query,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            user_preferences=user_preferences
        )
        logger.info(f"Created CRUDAgentInput: {knowledge_input}")
        
        logger.info("Step 3: Running unified CRUD processing")
        # Run the knowledge processing
        result = await run_unified_crud_processing(knowledge_input)
        logger.info(f"Processing result: {json.dumps(result, default=str)}")
        
        logger.info("Step 4: Preparing success response")
        response_body = {
            "response": result.get("response", ""),
            "sources": result.get("sources", []),
            "conversation_id": result.get("conversation_id", conversation_id),
            "processing_time": result.get("processing_time", 0),
            "workflow_type": result.get("workflow_type", "knowledge_processing"),
            "agent_used": result.get("agent_used", "knowledge_agent"),
            "tools_used": result.get("tools_used", "crud_only"),
            "business_logic": result.get("business_logic", "ai_handled"),
            "timestamp": datetime.now().isoformat(),
            "needs_clarification": False
        }
        logger.info(f"Success response body: {json.dumps(response_body, default=str)}")
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error("=== ERROR IN KNOWLEDGE CHAT HANDLER ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "response": "I apologize, but I encountered an error while processing your request. Please try again.",
            "sources": [],
            "conversation_id": "",
            "processing_time": 0,
            "workflow_type": "knowledge_processing",
            "agent_used": "knowledge_agent"
        }
        logger.error(f"Error response: {json.dumps(error_response, default=str)}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps(error_response)
        }

# Document ingestion is now handled by docling-unified-handler.py
# This function is removed as S3 events should directly trigger the docling service

# Synchronous wrappers for Lambda
def lambda_handler_knowledge_chat(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for knowledge chat handler"""
    logger.info("=== LAMBDA HANDLER KNOWLEDGE CHAT STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        result = asyncio.run(knowledge_chat_handler_async(event, context))
        logger.info(f"Chat handler result: {json.dumps(result, default=str)}")
        return result
    except Exception as e:
        logger.error(f"Error in lambda_handler_knowledge_chat: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

def lambda_handler_presigned_url(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for presigned URL generation handler"""
    logger.info("=== LAMBDA HANDLER PRESIGNED URL STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        result = asyncio.run(generate_presigned_url_handler_async(event, context))
        logger.info(f"Presigned URL handler result: {json.dumps(result, default=str)}")
        return result
    except Exception as e:
        logger.error(f"Error in lambda_handler_presigned_url: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# Document ingestion is now handled by docling-unified-handler.py
# This function is removed as S3 events should directly trigger the docling service

# Main Lambda handler (can be used for both chat and document processing)
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler that intelligently routes requests"""
    try:
        # Handle OPTIONS request for CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With, Accept, Origin',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Credentials': 'true',
                    'Access-Control-Max-Age': '86400'
                },
                'body': ''
            }
        
        # Check if this is a presigned URL request
        if event.get('httpMethod') == 'POST':
            try:
                # Parse request body to check for presigned URL action
                if isinstance(event.get('body'), str):
                    body = json.loads(event['body'])
                else:
                    body = event.get('body', {})
                
                # Check if this is a presigned URL request
                if body.get('action') == 'get-upload-url':
                    logger.info("Processing presigned URL request")
                    return lambda_handler_presigned_url(event, context)
            except (json.JSONDecodeError, KeyError):
                # If we can't parse the body, continue with normal flow
                pass
        
        # Check if this is an S3 event (document processing)
        # S3 events should now directly trigger docling-unified-handler
        # This handler only processes chat requests
        if 'Records' in event and event['Records']:
            record = event['Records'][0]
            if record.get('eventSource') == 'aws:s3':
                logger.info("S3 event detected - should be handled by docling-unified-handler")
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "error": "S3 events should be handled by docling-unified-handler, not this agent handler"
                    })
                }
        
        # Otherwise, treat as chat request
        logger.info("Processing chat request")
        return lambda_handler_knowledge_chat(event, context)
        
    except Exception as e:
        logger.error("=== ERROR IN MAIN LAMBDA HANDLER ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "response": "I apologize, but I encountered an error while processing your request.",
            "sources": [],
            "conversation_id": "",
            "processing_time": 0,
            "workflow_type": "knowledge_processing",
            "agent_used": "knowledge_agent"
        }
        logger.error(f"Error response: {json.dumps(error_response, default=str)}")
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept, Origin",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Credentials": "true"
            },
            "body": json.dumps(error_response)
        }

# Alternative handlers for specific use cases
def chat_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Dedicated chat Lambda handler"""
    logger.info("=== CHAT LAMBDA HANDLER STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        result = lambda_handler_knowledge_chat(event, context)
        logger.info(f"Chat lambda handler result: {json.dumps(result, default=str)}")
        return result
    except Exception as e:
        logger.error(f"Error in chat_lambda_handler: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

# Document ingestion is now handled by docling-unified-handler.py
# This function is removed as S3 events should directly trigger the docling service
