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
    """OpenAI Library Handler - ONLY library imports and initialization"""
    logger.info("=== OPENAI LIBRARY HANDLER STARTED ===")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        if OPENAI_COMPONENTS is None:
            logger.error("❌ OpenAI components not available - initialization failed")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "OpenAI library not available - initialization failed during container startup"
                })
            }
        
        logger.info(f"✅ OpenAI components available: {list(OPENAI_COMPONENTS.keys())}")
        
        # Parse the request - handle both direct event and body-wrapped formats
        logger.info(f"📊 Parsing request...")
        
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
                raise Exception(f"Invalid JSON in request body: {e}")
        else:
            body = event.get('body', {})
            logger.info(f"✅ Using direct body object")
        
        logger.info(f"📊 Parsed body keys: {list(body.keys()) if isinstance(body, dict) else 'Not a dict'}")
        
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
            
            try:
                # Use OpenAI client for chat completion
                response = OPENAI_COMPONENTS['openai'].chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                logger.info(f"✅ Successfully generated chat completion")
                logger.info(f"📊 Response usage: {response.usage}")
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "response": response.choices[0].message.content,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        }
                    })
                }
            except Exception as e:
                logger.error(f"❌ Error generating chat completion: {e}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                raise Exception(f"Failed to generate chat completion: {e}")
        else:
            # Return success - library is loaded and ready
            logger.info(f"📊 No chat completion request found, returning library status")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "message": "OpenAI library loaded successfully",
                    "components_available": list(OPENAI_COMPONENTS.keys())
                })
            }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in OpenAI handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        return {
            "statusCode": 400,
            "body": json.dumps({
                "success": False,
                "error": f"Invalid JSON in request: {e}",
                "error_type": "JSONDecodeError"
            })
        }
    except Exception as e:
        logger.error(f"❌ Error in OpenAI library handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            })
        }
