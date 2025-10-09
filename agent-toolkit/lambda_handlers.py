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

from datetime import datetime
logger.info("✅ Imported datetime module")

# Import our RAG agent
from rag_agent import run_unified_crud_processing, CRUDAgentInput
logger.info("✅ Imported rag_agent modules: run_unified_crud_processing, CRUDAgentInput")

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

async def knowledge_document_ingestion_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Knowledge document ingestion handler - all business logic handled by AgentBuilder model"""
    try:
        # Extract S3 event information
        records = event.get('Records', [])
        if not records:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "No S3 records found in event"
                })
            }
        
        record = records[0]
        s3_info = record.get('s3', {})
        bucket = s3_info.get('bucket', {}).get('name', '')
        key = s3_info.get('object', {}).get('key', '')
        
        # Create knowledge agent input for document processing with Docling
        knowledge_input = CRUDAgentInput(
            user_query=f"Process document with Docling hierarchical chunking: s3://{bucket}/{key}",
            conversation_history=[],
            conversation_id=f"doc_processing_{hash(key)}",
            user_preferences={
                "processing_type": "document_ingestion",
                "use_docling": True,
                "hierarchical_chunking": True,
                "document_source": f"s3://{bucket}/{key}"
            }
        )
        
        # Run the knowledge processing
        result = await run_unified_crud_processing(knowledge_input)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "document_id": f"doc_{hash(key)}",
                "status": "completed",
                "s3_bucket": bucket,
                "s3_key": key,
                "processing_time": result.get("processing_time", 0),
                "workflow_type": "docling_document_processing",
                "agent_used": "knowledge_agent",
                "tools_used": "docling_hierarchical_chunking",
                "business_logic": "ai_handled",
                "docling_enabled": True,
                "hierarchical_chunking": True,
                "chunk_types": result.get("chunk_types", []),
                "total_chunks": result.get("total_chunks", 0)
            })
        }
        
    except Exception as e:
        logger.error("=== ERROR IN DOCUMENT INGESTION HANDLER ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        error_response = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "status": "failed",
            "workflow_type": "unified_crud_processing"
        }
        logger.error(f"Error response: {json.dumps(error_response, default=str)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps(error_response)
        }

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

def lambda_handler_knowledge_document_ingestion(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for knowledge document ingestion handler"""
    logger.info("=== LAMBDA HANDLER DOCUMENT INGESTION STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        result = asyncio.run(knowledge_document_ingestion_handler_async(event, context))
        logger.info(f"Document ingestion handler result: {json.dumps(result, default=str)}")
        return result
    except Exception as e:
        logger.error(f"Error in lambda_handler_knowledge_document_ingestion: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

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
                    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS',
                    'Access-Control-Max-Age': '86400'
                },
                'body': ''
            }
        
        # Check if this is an S3 event (document processing)
        if 'Records' in event and event['Records']:
            record = event['Records'][0]
            if record.get('eventSource') == 'aws:s3':
                logger.info("Processing S3 event for document ingestion")
                return lambda_handler_knowledge_document_ingestion(event, context)
        
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
                "Access-Control-Allow-Origin": "*"
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

def document_ingestion_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Dedicated document ingestion Lambda handler"""
    logger.info("=== DOCUMENT INGESTION LAMBDA HANDLER STARTED ===")
    logger.info(f"Event: {json.dumps(event, default=str)}")
    logger.info(f"Context: {context}")
    
    try:
        result = lambda_handler_knowledge_document_ingestion(event, context)
        logger.info(f"Document ingestion lambda handler result: {json.dumps(result, default=str)}")
        return result
    except Exception as e:
        logger.error(f"Error in document_ingestion_lambda_handler: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
