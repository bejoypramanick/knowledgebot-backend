#!/usr/bin/env python3
"""
OpenAI Library Handler - Docker Lambda
ONLY handles OpenAI library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import os
import logging
import traceback
import sys
from datetime import datetime

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

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

# Initialize OpenAI - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import openai
    openai.api_key = os.environ.get('OPENAI_API_KEY')
    logger.info("✅ OpenAI library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    OPENAI_COMPONENTS = {
        "openai": openai
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize OpenAI library: {e}")
    OPENAI_COMPONENTS = None

def lambda_handler(event, context):
    """OpenAI Library Handler - ONLY library imports and initialization with comprehensive logging and error handling"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== OPENAI LIBRARY HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Validate OpenAI components availability
        if OPENAI_COMPONENTS is None:
            logger.error("❌ OpenAI components not available - initialization failed")
            log_service_failure(
                'openai-library-handler',
                'OpenAI library not available',
                {
                    'request_id': request_id,
                    'components_available': 'None'
                },
                'ERROR'
            )
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "OpenAI library not available - initialization failed during container startup",
                    "request_id": request_id
                })
            }
        
        logger.info(f"✅ OpenAI components available: {list(OPENAI_COMPONENTS.keys())}")
        
        # Parse the request - handle both direct event and body-wrapped formats
        logger.info(f"📊 Parsing request...")
        
        try:
            # Check if operation_type is directly in the event (Lambda invocation format)
            if 'operation_type' in event:
                logger.info(f"✅ Found 'operation_type' directly in event")
                body = event
            # Check if operation_type is in the body field (API Gateway format)
            elif isinstance(event.get('body'), str):
                try:
                    body = json.loads(event['body'])
                    logger.info(f"✅ Successfully parsed JSON body")
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON decode error: {e}")
                    logger.error(f"📊 Raw body: {event.get('body')}")
                    raise ValueError(f"Invalid JSON in request body: {e}")
            else:
                body = event.get('body', {})
                logger.info(f"✅ Using direct body object")
            
            logger.info(f"📊 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
            
        except ValueError as ve:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ Request parsing error: {ve}")
            log_error(
                'openai-library-handler',
                ve,
                context,
                {
                    'request_id': request_id,
                    'processing_time': processing_time,
                    'error_type': 'RequestParsingError'
                },
                'WARNING'
            )
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "error": str(ve),
                    "request_id": request_id,
                    "processing_time": processing_time
                })
            }
        
        # Check if this is a chat completion request
        if 'operation_type' in body and body['operation_type'] == 'chat':
            logger.info(f"🔧 Processing chat completion request")
            messages = body.get('messages', [])
            model = body.get('model', 'gpt-4o-mini')
            max_tokens = body.get('max_tokens', 1000)
            temperature = body.get('temperature', 0.7)
            
            logger.info(f"📝 Messages count: {len(messages)}")
            logger.info(f"📝 Model: {model}")
            logger.info(f"📝 Max tokens: {max_tokens}")
            logger.info(f"📝 Temperature: {temperature}")
            
            # Validate input parameters
            if not messages or not isinstance(messages, list):
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Messages must be a non-empty list"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'openai-library-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'model': model,
                        'messages_count': len(messages) if messages else 0,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Max tokens must be a positive integer"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'openai-library-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'model': model,
                        'max_tokens': max_tokens,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = "Temperature must be a number between 0 and 2"
                logger.error(f"❌ Validation error: {error_msg}")
                
                log_error(
                    'openai-library-handler',
                    ValueError(error_msg),
                    context,
                    {
                        'request_id': request_id,
                        'model': model,
                        'temperature': temperature,
                        'processing_time': processing_time,
                        'error_type': 'ValidationError'
                    },
                    'WARNING'
                )
                
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            try:
                logger.info(f"🔄 Calling OpenAI API for chat completion")
                # Use OpenAI client for chat completion
                response = OPENAI_COMPONENTS['openai'].chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"✅ Successfully generated chat completion")
                logger.info(f"📊 Processing time: {processing_time:.3f}s")
                logger.info(f"📊 Response usage: {response.usage}")
                logger.info(f"📊 Response length: {len(response.choices[0].message.content) if response.choices else 0} characters")
                
                # Log success to centralized error logger
                log_custom_error(
                    'openai-library-handler',
                    'chat_completion_success',
                    {
                        'request_id': request_id,
                        'model': model,
                        'messages_count': len(messages),
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'prompt_tokens': response.usage.prompt_tokens,
                        'completion_tokens': response.usage.completion_tokens,
                        'total_tokens': response.usage.total_tokens,
                        'processing_time': processing_time
                    },
                    'INFO'
                )
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "response": response.choices[0].message.content,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        },
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
                
            except Exception as e:
                processing_time = (datetime.now() - start_time).total_seconds()
                error_msg = f"Failed to generate chat completion: {str(e)}"
                logger.error(f"❌ Error generating chat completion: {error_msg}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                
                log_error(
                    'openai-library-handler',
                    e,
                    context,
                    {
                        'request_id': request_id,
                        'model': model,
                        'messages_count': len(messages),
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'processing_time': processing_time,
                        'error_type': 'OpenAIAPIError'
                    },
                    'ERROR'
                )
                
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "success": False,
                        "error": error_msg,
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
        else:
            # Return success - library is loaded and ready
            logger.info(f"📊 No chat completion request found, returning library status")
            processing_time = (datetime.now() - start_time).total_seconds()
            status_info = {
                "success": True,
                "message": "OpenAI library loaded successfully",
                "components_available": list(OPENAI_COMPONENTS.keys()),
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
    except json.JSONDecodeError as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ JSON decode error in OpenAI handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        # Log JSON decode error
        log_error(
            'openai-library-handler',
            e,
            context,
            {
                'request_id': request_id,
                'processing_time': processing_time,
                'error_type': 'JSONDecodeError'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": f"Invalid JSON in request: {e}",
                "error_type": "JSONDecodeError",
                "request_id": request_id,
                "processing_time": processing_time
            })
        }
    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Error in OpenAI library handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'openai-library-handler',
            e,
            context,
            {
                'request_id': request_id,
                'operation_type': event.get('operation_type', 'unknown'),
                'model': event.get('model', 'unknown'),
                'event_keys': list(event.keys()) if event else [],
                'processing_time': processing_time,
                'error_type': 'HandlerError'
            },
            'ERROR'
        )
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
        }
