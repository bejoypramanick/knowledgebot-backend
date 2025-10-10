#!/usr/bin/env python3
"""
Production Error Handling System
Comprehensive error handling with natural language messages and detailed logging
"""

import json
import logging
import traceback
import functools
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionErrorHandler:
    """Production-grade error handling with natural language messages"""
    
    ERROR_MESSAGES = {
        # API Gateway & Lambda Errors
        'invalid_request': "I'm sorry, but I couldn't understand your request. Please try rephrasing your question.",
        'missing_query': "I need a question or message to help you. Please provide your query.",
        'timeout_error': "I'm taking longer than expected to process your request. Please try again in a moment.",
        'rate_limit': "I'm receiving too many requests right now. Please wait a moment before trying again.",
        
        # Database Errors
        'neo4j_connection': "I'm having trouble accessing the knowledge graph. Please try again shortly.",
        'pinecone_connection': "I'm experiencing issues with the vector database. Please try again in a moment.",
        'dynamodb_error': "I'm having trouble accessing the document metadata. Please try again.",
        's3_error': "I'm experiencing issues accessing documents. Please try again shortly.",
        
        # AI/LLM Errors
        'openai_error': "I'm having trouble processing your request with the AI service. Please try again.",
        'embedding_error': "I'm experiencing issues generating text embeddings. Please try again.",
        'model_error': "I'm having trouble with the AI model. Please try rephrasing your question.",
        
        # Document Processing Errors
        'docling_error': "I'm having trouble processing the document. Please ensure it's a supported format.",
        'file_too_large': "The document is too large for processing. Please try with a smaller file.",
        'unsupported_format': "I can't process this file format. Please use PDF, Word, or text files.",
        'corrupted_file': "The document appears to be corrupted. Please try uploading it again.",
        
        # System Errors
        'memory_error': "I'm running low on memory. Please try with a smaller request.",
        'network_error': "I'm experiencing network issues. Please try again shortly.",
        'service_unavailable': "One of my services is temporarily unavailable. Please try again later.",
        'internal_error': "I encountered an unexpected error. Please try again or contact support if the issue persists."
    }
    
    @staticmethod
    def get_user_friendly_message(error_type: str, original_error: str = "") -> str:
        """Get user-friendly error message"""
        return ProductionErrorHandler.ERROR_MESSAGES.get(
            error_type, 
            ProductionErrorHandler.ERROR_MESSAGES['internal_error']
        )
    
    @staticmethod
    def categorize_error(error: Exception) -> str:
        """Categorize error for appropriate handling"""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Network/Connection errors
        if any(keyword in error_str for keyword in ['connection', 'timeout', 'network', 'unreachable']):
            return 'network_error'
        
        # Database errors
        if 'neo4j' in error_str or 'cypher' in error_str:
            return 'neo4j_connection'
        elif 'pinecone' in error_str or 'vector' in error_str:
            return 'pinecone_connection'
        elif 'dynamodb' in error_str or 'dynamo' in error_str:
            return 'dynamodb_error'
        elif 's3' in error_str or 'bucket' in error_str:
            return 's3_error'
        
        # AI/LLM errors
        if 'openai' in error_str or 'api key' in error_str:
            return 'openai_error'
        elif 'embedding' in error_str:
            return 'embedding_error'
        elif 'model' in error_str or 'gpt' in error_str:
            return 'model_error'
        
        # Document processing errors
        if 'docling' in error_str:
            return 'docling_error'
        elif 'file too large' in error_str or 'size' in error_str:
            return 'file_too_large'
        elif 'format' in error_str or 'unsupported' in error_str:
            return 'unsupported_format'
        elif 'corrupted' in error_str or 'invalid' in error_str:
            return 'corrupted_file'
        
        # System errors
        if 'memory' in error_str or 'oom' in error_str:
            return 'memory_error'
        elif 'rate limit' in error_str:
            return 'rate_limit'
        elif 'service unavailable' in error_str:
            return 'service_unavailable'
        
        return 'internal_error'

def production_error_handler(func: Callable) -> Callable:
    """Decorator for production-grade error handling"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        request_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            logger.info(f"🚀 Starting {func.__name__} - Request ID: {request_id}")
            result = func(*args, **kwargs)
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"✅ Completed {func.__name__} - Request ID: {request_id} - Time: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            error_category = ProductionErrorHandler.categorize_error(e)
            user_message = ProductionErrorHandler.get_user_friendly_message(error_category, str(e))
            
            # Log detailed error information
            logger.error(f"❌ Error in {func.__name__} - Request ID: {request_id}")
            logger.error(f"Error Category: {error_category}")
            logger.error(f"Error Type: {type(e).__name__}")
            logger.error(f"Error Message: {str(e)}")
            logger.error(f"Processing Time: {processing_time:.2f}s")
            logger.error(f"Full Traceback: {traceback.format_exc()}")
            
            # Create error response
            error_response = {
                "success": False,
                "error": user_message,
                "error_category": error_category,
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat(),
                "debug_info": {
                    "original_error": str(e),
                    "traceback": traceback.format_exc()
                }
            }
            
            # Return appropriate HTTP response
            if hasattr(func, '__name__') and 'lambda_handler' in func.__name__:
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
            else:
                return error_response
                
    return wrapper

def validate_request_body(body: Dict[str, Any], required_fields: list) -> Dict[str, Any]:
    """Validate request body and return appropriate error if invalid"""
    if not body:
        return {
            "success": False,
            "error": "Request body is required",
            "error_category": "invalid_request"
        }
    
    missing_fields = [field for field in required_fields if not body.get(field)]
    if missing_fields:
        return {
            "success": False,
            "error": f"Missing required fields: {', '.join(missing_fields)}",
            "error_category": "invalid_request"
        }
    
    return {"success": True}

def safe_json_parse(data: str, default: Any = None) -> Any:
    """Safely parse JSON with error handling"""
    try:
        return json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error: {e}")
        return default

def create_success_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }

def create_error_response(error_message: str, error_category: str = "internal_error", 
                         status_code: int = 500, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "success": False,
        "error": error_message,
        "error_category": error_category,
        "timestamp": datetime.now().isoformat()
    }
    
    if additional_data:
        response.update(additional_data)
    
    if status_code:
        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(response)
        }
    
    return response
