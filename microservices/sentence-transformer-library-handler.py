#!/usr/bin/env python3
"""
Sentence Transformer Library Handler - Docker Lambda
ONLY handles Sentence Transformer library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import logging
import traceback
import sys
import os
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

# Initialize Sentence Transformer - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    import os
    import time
    
    # Set cache directory to PERSISTENT locations in the image filesystem
    os.environ['TRANSFORMERS_CACHE'] = '/opt/models/transformers_cache'
    os.environ['HF_HOME'] = '/opt/models/huggingface'
    os.environ['SENTENCE_TRANSFORMERS_CACHE'] = '/opt/models/sentence_transformers_cache'
    
    # Disable progress bars and verbose logging for Lambda
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = '1'
    
    logger.info("🔄 Starting Sentence Transformer initialization...")
    start_time = time.time()
    
    from sentence_transformers import SentenceTransformer
    
    # Check if cache directory exists and has content
    cache_dir = '/opt/models/sentence_transformers_cache'
    if os.path.exists(cache_dir):
        cache_files = os.listdir(cache_dir)
        logger.info(f"📁 Cache directory exists with {len(cache_files)} files")
        logger.info(f"📁 Cache files: {cache_files[:5]}...")  # Show first 5 files
    else:
        logger.warning(f"⚠️ Cache directory {cache_dir} does not exist!")
    
    # Load the pre-downloaded model from PERSISTENT cache (should be cached from Docker build)
    logger.info("🔄 Loading pre-downloaded model from persistent cache...")
    model_start = time.time()
    
    embedding_model = SentenceTransformer(
        'all-MiniLM-L6-v2', 
        cache_folder='/opt/models/sentence_transformers_cache',
        device='cpu'  # Force CPU usage
    )
    
    model_load_time = time.time() - model_start
    total_time = time.time() - start_time
    
    logger.info("✅ Sentence Transformer library imported and initialized successfully")
    logger.info(f"✅ Model loaded from persistent cache in {model_load_time:.2f}s (total: {total_time:.2f}s)")
    logger.info(f"✅ Model device: {embedding_model.device}")
    logger.info(f"✅ Model max sequence length: {embedding_model.max_seq_length}")
    
    # Export the initialized components for use by Zip Lambdas
    SENTENCE_TRANSFORMER_COMPONENTS = {
        "SentenceTransformer": SentenceTransformer,
        "embedding_model": embedding_model
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Sentence Transformer library: {e}")
    logger.error(f"📊 Error details: {str(e)}")
    logger.error(f"📊 Error type: {type(e).__name__}")
    import traceback
    logger.error(f"📊 Stack trace: {traceback.format_exc()}")
    SENTENCE_TRANSFORMER_COMPONENTS = None

def lambda_handler(event, context):
    """Sentence Transformer Library Handler - ONLY library imports and initialization"""
    logger.info("=== SENTENCE TRANSFORMER LIBRARY HANDLER STARTED ===")
    logger.info(f"📊 Event type: {type(event)}")
    logger.info(f"📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    logger.info(f"📊 Context: {context}")
    logger.info(f"📊 Event details: {json.dumps(event, default=str, indent=2)}")
    
    try:
        if SENTENCE_TRANSFORMER_COMPONENTS is None:
            logger.error("❌ Sentence Transformer components not available - initialization failed")
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Sentence Transformer library not available - initialization failed during container startup"
                })
            }
        
        logger.info(f"✅ Sentence Transformer components available: {list(SENTENCE_TRANSFORMER_COMPONENTS.keys())}")
        
        # Parse the request - handle both direct event and body-wrapped formats
        logger.info(f"📊 Parsing request...")
        
        # Check if texts is directly in the event (Lambda invocation format)
        if 'texts' in event:
            logger.info(f"✅ Found 'texts' directly in event")
            body = event
        # Check if texts is in the body field (API Gateway format)
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
        
        # Check if this is an embedding request
        if 'texts' in body:
            texts = body['texts']
            logger.info(f"🔧 Processing embedding request for {len(texts)} texts")
            logger.info(f"📝 Text preview: {texts[:2] if len(texts) > 2 else texts}")
            
            if not isinstance(texts, list):
                logger.error(f"❌ 'texts' must be a list, got: {type(texts)}")
                raise Exception(f"'texts' must be a list, got {type(texts)}")
            
            if len(texts) == 0:
                logger.error(f"❌ 'texts' list is empty")
                raise Exception("'texts' list cannot be empty")
            
            logger.info(f"🧠 Generating embeddings using pre-loaded model...")
            try:
                # Generate embeddings using the pre-loaded model (no downloads needed)
                embeddings = SENTENCE_TRANSFORMER_COMPONENTS['embedding_model'].encode(
                    texts, 
                    convert_to_tensor=False,  # Keep as numpy array for efficiency
                    show_progress_bar=False   # Disable progress bar for Lambda
                )
                logger.info(f"✅ Successfully generated embeddings")
                logger.info(f"📊 Embeddings shape: {embeddings.shape if hasattr(embeddings, 'shape') else len(embeddings)}")
                logger.info(f"📊 Embeddings type: {type(embeddings)}")
                
                # Convert numpy array to list
                embeddings_list = embeddings.tolist()
                logger.info(f"✅ Converted embeddings to list format")
                
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "success": True,
                        "embeddings": embeddings_list
                    })
                }
            except Exception as e:
                logger.error(f"❌ Error generating embeddings: {e}")
                logger.error(f"📊 Stack trace: {traceback.format_exc()}")
                raise Exception(f"Failed to generate embeddings: {e}")
        else:
            # Return success - library is loaded and ready
            logger.info(f"📊 No 'texts' field found, returning library status")
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "message": "Sentence Transformer library loaded successfully",
                    "components_available": list(SENTENCE_TRANSFORMER_COMPONENTS.keys())
                })
            }
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON decode error in Sentence Transformer handler: {e}")
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
        logger.error(f"❌ Error in Sentence Transformer library handler: {e}")
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
