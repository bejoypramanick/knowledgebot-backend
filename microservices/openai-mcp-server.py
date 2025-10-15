#!/usr/bin/env python3
"""
OpenAI Agents SDK Handler - Uses OpenAI Agents SDK directly
Provides OpenAI operations through the Agents SDK
"""

import json
import logging
import os
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, List

# Import error logging utility
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
from error_logger import log_error, log_custom_error, log_service_failure

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OpenAI Agents SDK imports
try:
    from agents import Agent, Runner
    from openai import OpenAI
    AGENTS_SDK_AVAILABLE = True
    logger.info("✅ OpenAI Agents SDK imported successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import OpenAI Agents SDK: {e}")
    AGENTS_SDK_AVAILABLE = False

class OpenAIAgentsHandler:
    """OpenAI Agents SDK Handler for AI operations"""
    
    def __init__(self):
        self.client = None
        self.agent = None
        self._initialize_client()
        self._initialize_agent()
    
    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            api_key = os.environ.get('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required")
            
            self.client = OpenAI(api_key=api_key)
            
            # Test connection by listing models
            models = self.client.models.list()
            
            logger.info(f"✅ OpenAI client initialized successfully with {len(models.data)} models available")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def _initialize_agent(self):
        """Initialize OpenAI Agent"""
        try:
            if not AGENTS_SDK_AVAILABLE:
                logger.error("❌ OpenAI Agents SDK not available")
                self.agent = None
                return
            
            self.agent = Agent(
                name="KnowledgeBot Assistant",
                instructions="You are a helpful AI assistant that provides accurate and helpful responses based on the knowledge base and context provided."
            )
            
            logger.info("✅ OpenAI Agent initialized successfully")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize OpenAI Agent: {e}")
            self.agent = None
    
    def chat_completion(self, messages: List[Dict[str, str]], model: str = "gpt-4o-mini", 
                       max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate chat completion using OpenAI Agents SDK"""
        try:
            logger.info(f"💬 Generating chat completion with {len(messages)} messages")
            
            if not self.client:
                return {
                    "success": False,
                    "error": "OpenAI client not initialized"
                }
            
            if not messages:
                return {
                    "success": False,
                    "error": "messages are required"
                }
            
            # Validate messages format
            for i, message in enumerate(messages):
                if not isinstance(message, dict) or "role" not in message or "content" not in message:
                    return {
                        "success": False,
                        "error": f"Invalid message format at index {i}. Each message must have 'role' and 'content'"
                    }
                
                if message["role"] not in ["system", "user", "assistant"]:
                    return {
                        "success": False,
                        "error": f"Invalid role '{message['role']}' at index {i}. Role must be 'system', 'user', or 'assistant'"
                    }
            
            # Use Agents SDK if available, otherwise fall back to direct client
            if self.agent and AGENTS_SDK_AVAILABLE:
                try:
                    # Convert messages to a single prompt for the agent
                    prompt = self._messages_to_prompt(messages)
                    
                    # Run the agent
                    result = Runner.run_sync(self.agent, prompt)
                    
                    return {
                        "success": True,
                        "response": result.final_output,
                        "model": model,
                        "method": "agents_sdk"
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Agents SDK failed, falling back to direct client: {e}")
                    # Fall back to direct client call
            
            # Direct client call
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason,
                "method": "direct_client"
            }
            
        except Exception as e:
            logger.error(f"❌ Error in chat completion: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def completion(self, prompt: str, model: str = "gpt-3.5-turbo-instruct", 
                  max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """Generate text completion using OpenAI"""
        try:
            logger.info(f"📝 Generating text completion for prompt length: {len(prompt)}")
            
            if not self.client:
                return {
                    "success": False,
                    "error": "OpenAI client not initialized"
                }
            
            if not prompt:
                return {
                    "success": False,
                    "error": "prompt is required"
                }
            
            # Use Agents SDK if available
            if self.agent and AGENTS_SDK_AVAILABLE:
                try:
                    result = Runner.run_sync(self.agent, prompt)
                    
                    return {
                        "success": True,
                        "response": result.final_output,
                        "model": model,
                        "method": "agents_sdk"
                    }
                except Exception as e:
                    logger.warning(f"⚠️ Agents SDK failed, falling back to direct client: {e}")
            
            # Direct client call
            response = self.client.completions.create(
                model=model,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "success": True,
                "response": response.choices[0].text,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason,
                "method": "direct_client"
            }
            
        except Exception as e:
            logger.error(f"❌ Error in completion: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def embedding(self, input_texts: List[str], model: str = "text-embedding-3-small") -> Dict[str, Any]:
        """Generate embeddings using OpenAI"""
        try:
            logger.info(f"🧠 Generating embeddings for {len(input_texts)} texts")
            
            if not self.client:
                return {
                    "success": False,
                    "error": "OpenAI client not initialized"
                }
            
            if not input_texts:
                return {
                    "success": False,
                    "error": "input is required"
                }
            
            if not isinstance(input_texts, list):
                input_texts = [input_texts]
            
            response = self.client.embeddings.create(
                model=model,
                input=input_texts
            )
            
            embeddings = [data.embedding for data in response.data]
            
            return {
                "success": True,
                "embeddings": embeddings,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error in embedding: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_models(self) -> Dict[str, Any]:
        """List available models"""
        try:
            if not self.client:
                return {
                    "success": False,
                    "error": "OpenAI client not initialized"
                }
            
            models = self.client.models.list()
            
            model_list = []
            for model in models.data:
                model_list.append({
                    "id": model.id,
                    "object": model.object,
                    "created": model.created,
                    "owned_by": model.owned_by
                })
            
            return {
                "success": True,
                "models": model_list,
                "count": len(model_list)
            }
            
        except Exception as e:
            logger.error(f"❌ Error listing models: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status"""
        return {
            "status": "healthy" if self.client else "unhealthy",
            "client_initialized": self.client is not None,
            "agents_sdk_available": AGENTS_SDK_AVAILABLE,
            "agent_initialized": self.agent is not None,
            "server": "openai-agents-handler",
            "version": "1.0.0"
        }
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single prompt for the agent"""
        prompt_parts = []
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt_parts.append(f"System: {content}")
            elif role == "user":
                prompt_parts.append(f"User: {content}")
            elif role == "assistant":
                prompt_parts.append(f"Assistant: {content}")
        
        return "\n\n".join(prompt_parts)

# Initialize the handler
openai_handler = OpenAIAgentsHandler()

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """OpenAI Agents SDK Lambda Handler"""
    start_time = datetime.now()
    request_id = context.aws_request_id if context else "unknown"
    
    logger.info("=== OPENAI AGENTS SDK HANDLER STARTED ===")
    logger.info(f"📊 Request ID: {request_id}")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        # Parse the request
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
                'openai-agents-handler',
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
        
        # Check operation type and route to appropriate function
        operation_type = body.get('operation_type', 'status')
        logger.info(f"📊 Operation type: {operation_type}")
        
        if operation_type == 'chat':
            logger.info(f"💬 Processing chat completion request")
            messages = body.get('messages', [])
            model = body.get('model', 'gpt-4o-mini')
            max_tokens = body.get('max_tokens', 1000)
            temperature = body.get('temperature', 0.7)
            
            logger.info(f"📝 Messages count: {len(messages)}")
            logger.info(f"📝 Model: {model}")
            logger.info(f"📝 Max tokens: {max_tokens}")
            logger.info(f"📝 Temperature: {temperature}")
            
            # Validate input
            if not messages:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No messages provided for chat completion")
                log_custom_error(
                    'openai-agents-handler',
                    'No messages provided for chat completion',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No messages provided for chat completion",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI Agents SDK
            result = openai_handler.chat_completion(messages, model, max_tokens, temperature)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 Total processing time: {processing_time:.3f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["request_id"] = request_id
            
            return {
                "statusCode": 200 if result["success"] else 500,
                "body": json.dumps(result)
            }
            
        elif operation_type == 'completion':
            logger.info(f"📝 Processing text completion request")
            prompt = body.get('prompt', '')
            model = body.get('model', 'gpt-3.5-turbo-instruct')
            max_tokens = body.get('max_tokens', 1000)
            temperature = body.get('temperature', 0.7)
            
            logger.info(f"📝 Prompt length: {len(prompt)}")
            logger.info(f"📝 Model: {model}")
            logger.info(f"📝 Max tokens: {max_tokens}")
            logger.info(f"📝 Temperature: {temperature}")
            
            # Validate input
            if not prompt:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No prompt provided for completion")
                log_custom_error(
                    'openai-agents-handler',
                    'No prompt provided for completion',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No prompt provided for completion",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI Agents SDK
            result = openai_handler.completion(prompt, model, max_tokens, temperature)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 Total processing time: {processing_time:.3f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["request_id"] = request_id
            
            return {
                "statusCode": 200 if result["success"] else 500,
                "body": json.dumps(result)
            }
            
        elif operation_type == 'embedding':
            logger.info(f"🧠 Processing embedding generation request")
            input_texts = body.get('input', [])
            model = body.get('model', 'text-embedding-3-small')
            
            logger.info(f"📝 Input texts count: {len(input_texts) if isinstance(input_texts, list) else 1}")
            logger.info(f"📝 Model: {model}")
            
            # Validate input
            if not input_texts:
                processing_time = (datetime.now() - start_time).total_seconds()
                logger.error("❌ No input provided for embedding")
                log_custom_error(
                    'openai-agents-handler',
                    'No input provided for embedding',
                    {
                        'request_id': request_id,
                        'processing_time': processing_time
                    },
                    'WARNING'
                )
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "error": "No input provided for embedding",
                        "request_id": request_id,
                        "processing_time": processing_time
                    })
                }
            
            # Call OpenAI Agents SDK
            result = openai_handler.embedding(input_texts, model)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"📊 Total processing time: {processing_time:.3f}s")
            
            # Add processing time to result
            if isinstance(result, dict):
                result["processing_time"] = processing_time
                result["request_id"] = request_id
            
            return {
                "statusCode": 200 if result["success"] else 500,
                "body": json.dumps(result)
            }
            
        else:
            # Return health status
            logger.info(f"📊 No specific operation found, returning health status")
            processing_time = (datetime.now() - start_time).total_seconds()
            status_info = openai_handler.get_health()
            status_info.update({
                "request_id": request_id,
                "processing_time": processing_time,
                "timestamp": datetime.now().isoformat()
            })
            
            logger.info(f"📊 Status response: {status_info}")
            return {
                "statusCode": 200,
                "body": json.dumps(status_info)
            }
        
    except json.JSONDecodeError as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ JSON decode error in OpenAI Agents handler: {e}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        
        log_error(
            'openai-agents-handler',
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
        logger.error(f"❌ Error in OpenAI Agents handler: {e}")
        logger.error(f"📊 Error type: {type(e).__name__}")
        logger.error(f"📊 Error args: {e.args}")
        logger.error(f"📊 Stack trace: {traceback.format_exc()}")
        logger.error(f"📊 Event that caused error: {json.dumps(event, default=str, indent=2)}")
        
        # Log error to centralized system
        log_error(
            'openai-agents-handler',
            e,
            context,
            {
                'request_id': request_id,
                'operation_type': event.get('operation_type', 'unknown'),
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
