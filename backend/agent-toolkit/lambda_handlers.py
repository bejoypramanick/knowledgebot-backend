"""
Lambda Handlers with CRUD Tools Only
All business logic and formatting handled by AgentBuilder model
"""

import json
import os
import asyncio
from typing import Dict, Any
import logging

# Import our unified AI agent
from unified_ai_agent import run_unified_crud_processing, CRUDAgentInput

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def knowledge_chat_handler_async(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Knowledge chat handler - all business logic handled by AgentBuilder model"""
    try:
        # Extract query from event
        if 'body' in event:
            body = json.loads(event['body'])
        else:
            body = event
        
        user_query = body.get('message', body.get('user_query', ''))
        conversation_id = body.get('conversation_id', '')
        conversation_history = body.get('conversation_history', [])
        user_preferences = body.get('user_preferences', {})
        
        if not user_query:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": "User query is required"
                })
            }
        
        # Create knowledge agent input
        knowledge_input = CRUDAgentInput(
            user_query=user_query,
            conversation_history=conversation_history,
            conversation_id=conversation_id,
            user_preferences=user_preferences
        )
        
        # Run the knowledge processing
        result = await run_unified_crud_processing(knowledge_input)
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps({
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
            })
        }
        
    except Exception as e:
        logger.error(f"Error in knowledge chat handler: {e}")
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
                "response": "I apologize, but I encountered an error while processing your request. Please try again.",
                "sources": [],
                "conversation_id": "",
                "processing_time": 0,
                "workflow_type": "knowledge_processing",
                "agent_used": "knowledge_agent"
            })
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
        
        # Create knowledge agent input for document processing
        knowledge_input = CRUDAgentInput(
            user_query=f"Process document: s3://{bucket}/{key}",
            conversation_history=[],
            conversation_id=f"doc_processing_{hash(key)}",
            user_preferences={"processing_type": "document_ingestion"}
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
                "workflow_type": "knowledge_processing",
                "agent_used": "knowledge_agent",
                "tools_used": "crud_only",
                "business_logic": "ai_handled"
            })
        }
        
    except Exception as e:
        logger.error(f"Error in knowledge document ingestion handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "status": "failed",
                "workflow_type": "unified_crud_processing"
            })
        }

# Synchronous wrappers for Lambda
def lambda_handler_knowledge_chat(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for knowledge chat handler"""
    return asyncio.run(knowledge_chat_handler_async(event, context))

def lambda_handler_knowledge_document_ingestion(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Synchronous wrapper for knowledge document ingestion handler"""
    return asyncio.run(knowledge_document_ingestion_handler_async(event, context))

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
        logger.error(f"Error in main lambda handler: {e}")
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e),
                "response": "I apologize, but I encountered an error while processing your request.",
                "sources": [],
                "conversation_id": "",
                "processing_time": 0,
                "workflow_type": "knowledge_processing",
                "agent_used": "knowledge_agent"
            })
        }

# Alternative handlers for specific use cases
def chat_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Dedicated chat Lambda handler"""
    return lambda_handler_knowledge_chat(event, context)

def document_ingestion_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Dedicated document ingestion Lambda handler"""
    return lambda_handler_knowledge_document_ingestion(event, context)
