"""
CRUD Tools Only - Pure Data Operations
All business logic and formatting handled by AgentBuilder model

Copyright (c) 2024 Bejoy Pramanick
All rights reserved. Commercial use prohibited without written permission.
Contact: bejoy.pramanick@globistaan.com for licensing inquiries.
"""

import json
import logging
import boto3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize AWS services
try:
    s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))
    # Initialize Pinecone (Required) - Updated to new API
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.environ.get('PINECONE_API_KEY'))
    _pinecone_index = pc.Index(os.environ.get('PINECONE_INDEX_NAME'))
    
    # Store Pinecone configuration for validation
    _pinecone_host = os.environ.get('PINECONE_HOST')
    _pinecone_dimensions = int(os.environ.get('PINECONE_DIMENSIONS', '1536'))
    _pinecone_metric = os.environ.get('PINECONE_METRIC', 'cosine')
    
    # Initialize Neo4j (Required)
    from neo4j import GraphDatabase
    _neo4j_driver = GraphDatabase.driver(
        os.environ.get('NEO4J_URI'),
        auth=(os.environ.get('NEO4J_USER'), os.environ.get('NEO4J_PASSWORD'))
    )
    
    # Initialize embedding model (sentence transformers by default)
    try:
        embedding_type = os.environ.get('EMBEDDING_TYPE', 'local').lower()
        
        if embedding_type == 'local':
            from sentence_transformers import SentenceTransformer
            model_name = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            _embedding_model = SentenceTransformer(model_name)
            _embedding_type = 'local'
            logger.info(f"Using local sentence transformers model: {model_name}")
        else:
            import openai
            _embedding_model = None  # We'll use OpenAI API directly
            openai.api_key = os.environ.get('OPENAI_API_KEY')
            _embedding_type = 'openai'
            logger.info("Using OpenAI embedding API")
    except Exception as e:
        logger.warning(f"Embedding model not available: {e}")
        _embedding_type = 'none'

except Exception as e:
    logger.error(f"Error initializing services: {e}")
    raise e  # Fail fast if required services can't be initialized

# ============================================================================
# PURE CRUD TOOLS - NO BUSINESS LOGIC
# ============================================================================

def read_s3_data_crud(bucket: str, key: str) -> Dict[str, Any]:
    """
    CRUD: Read data from S3 bucket
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        Raw S3 data or error
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        return {
            'success': True,
            'data': content,
            'bucket': bucket,
            'key': key,
            'size': len(content)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'bucket': bucket,
            'key': key
        }

def search_pinecone_crud(query_vector: List[float], limit: int = 10, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Search Pinecone vector database with production RAG features
    
    Args:
        query_vector: Vector representation of query
        limit: Maximum number of results
        filter_dict: Metadata filter for Pinecone
        namespace: Pinecone namespace
        
    Returns:
        Raw Pinecone search results with RAG context
    """
    try:
        
        # Build query parameters
        query_params = {
            'vector': query_vector,
            'top_k': limit,
            'include_metadata': True,
            'include_values': False  # Don't return vectors for performance
        }
        
        if filter_dict:
            query_params['filter'] = filter_dict
        if namespace:
            query_params['namespace'] = namespace
        
        results = _pinecone_index.query(**query_params)
        
        # Process results for RAG
        processed_matches = []
        for match in results.matches:
            processed_matches.append({
                'id': match.id,
                'score': match.score,
                'metadata': match.metadata or {},
                'text': match.metadata.get('text', '') if match.metadata else '',
                'source': match.metadata.get('source', '') if match.metadata else '',
                'chunk_id': match.metadata.get('chunk_id', '') if match.metadata else '',
                'document_id': match.metadata.get('document_id', '') if match.metadata else ''
            })
        
        return {
            'success': True,
            'matches': processed_matches,
            'namespace': results.namespace or namespace or '',
            'query_vector_length': len(query_vector),
            'total_matches': len(processed_matches),
            'pinecone_dimensions': _pinecone_dimensions,
            'pinecone_metric': _pinecone_metric,
            'pinecone_host': _pinecone_host
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def search_neo4j_crud(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    CRUD: Execute Cypher query in Neo4j
    
    Args:
        cypher_query: Cypher query string
        parameters: Query parameters
        
    Returns:
        Raw Neo4j query results
    """
    try:
        
        with _neo4j_driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            records = [dict(record) for record in result]
            
            return {
                'success': True,
                'records': records,
                'query': cypher_query,
                'parameters': parameters
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': cypher_query
        }

def read_dynamodb_crud(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """
    CRUD: Read item from DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        key: Primary key
        
    Returns:
        Raw DynamoDB item or error
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key=key)
        
        if 'Item' in response:
            return {
                'success': True,
                'item': response['Item'],
                'table_name': table_name
            }
        else:
            return {
                'success': False,
                'error': 'Item not found',
                'table_name': table_name,
                'key': key
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'table_name': table_name,
            'key': key
        }

def batch_read_dynamodb_crud(table_name: str, keys: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    CRUD: Batch read items from DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        keys: List of primary keys
        
    Returns:
        Raw DynamoDB items or error
    """
    try:
        table = dynamodb.Table(table_name)
        
        # DynamoDB batch_get_item has a limit of 100 items
        items = []
        for i in range(0, len(keys), 100):
            batch_keys = keys[i:i+100]
            response = table.meta.client.batch_get_item(
                RequestItems={
                    table_name: {
                        'Keys': batch_keys
                    }
                }
            )
            
            if table_name in response['Responses']:
                items.extend(response['Responses'][table_name])
        
        return {
            'success': True,
            'items': items,
            'table_name': table_name,
            'requested_count': len(keys),
            'returned_count': len(items)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'table_name': table_name
        }

def write_dynamodb_crud(table_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """
    CRUD: Write item to DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        item: Item to write
        
    Returns:
        Write result or error
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.put_item(Item=item)
        
        return {
            'success': True,
            'table_name': table_name,
            'item_id': item.get('id', 'unknown')
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'table_name': table_name
        }

def update_dynamodb_crud(table_name: str, key: Dict[str, Any], update_expression: str, expression_values: Dict[str, Any]) -> Dict[str, Any]:
    """
    CRUD: Update item in DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        key: Primary key
        update_expression: Update expression
        expression_values: Expression values
        
    Returns:
        Update result or error
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues="UPDATED_NEW"
        )
        
        return {
            'success': True,
            'table_name': table_name,
            'updated_attributes': response.get('Attributes', {})
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'table_name': table_name
        }

def delete_dynamodb_crud(table_name: str, key: Dict[str, Any]) -> Dict[str, Any]:
    """
    CRUD: Delete item from DynamoDB table
    
    Args:
        table_name: DynamoDB table name
        key: Primary key
        
    Returns:
        Delete result or error
    """
    try:
        table = dynamodb.Table(table_name)
        response = table.delete_item(Key=key)
        
        return {
            'success': True,
            'table_name': table_name,
            'deleted_key': key
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'table_name': table_name
        }

def generate_embedding_crud(text: str) -> Dict[str, Any]:
    """
    CRUD: Generate embedding vector for text (local or OpenAI)
    
    Args:
        text: Text to embed
        
    Returns:
        Raw embedding vector or error
    """
    try:
        if _embedding_type == 'local' and _embedding_model:
            # Use local sentence transformers model
            embedding = _embedding_model.encode(text)
            model_name = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            
            # Validate embedding dimensions match Pinecone configuration
            if len(embedding) != _pinecone_dimensions:
                logger.warning(f"Embedding dimension mismatch: expected {_pinecone_dimensions}, got {len(embedding)}")
            
            return {
                'success': True,
                'embedding': embedding.tolist(),
                'text_length': len(text),
                'embedding_dimension': len(embedding),
                'model': model_name,
                'type': 'local',
                'pinecone_dimensions': _pinecone_dimensions,
                'pinecone_metric': _pinecone_metric
            }
            
        elif _embedding_type == 'openai':
            # Use OpenAI API
            import openai
            
            response = openai.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            embedding = response.data[0].embedding
            
            # Validate embedding dimensions match Pinecone configuration
            if len(embedding) != _pinecone_dimensions:
                logger.warning(f"Embedding dimension mismatch: expected {_pinecone_dimensions}, got {len(embedding)}")
            
            return {
                'success': True,
                'embedding': embedding,
                'text_length': len(text),
                'embedding_dimension': len(embedding),
                'model': 'text-embedding-3-small',
                'type': 'openai',
                'pinecone_dimensions': _pinecone_dimensions,
                'pinecone_metric': _pinecone_metric
            }
        else:
            return {
                'success': False,
                'error': 'No embedding model available'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def upsert_pinecone_crud(vectors: List[Dict[str, Any]], namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Upsert vectors to Pinecone
    
    Args:
        vectors: List of vectors with IDs and metadata
        namespace: Pinecone namespace
        
    Returns:
        Upsert result or error
    """
    try:
        
        response = _pinecone_index.upsert(
            vectors=vectors,
            namespace=namespace
        )
        
        return {
            'success': True,
            'upserted_count': response.upserted_count,
            'namespace': namespace
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def delete_pinecone_crud(ids: List[str], namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Delete vectors from Pinecone
    
    Args:
        ids: List of vector IDs to delete
        namespace: Pinecone namespace
        
    Returns:
        Delete result or error
    """
    try:
        
        response = _pinecone_index.delete(
            ids=ids,
            namespace=namespace
        )
        
        return {
            'success': True,
            'deleted_count': len(ids),
            'namespace': namespace
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def execute_neo4j_write_crud(cypher_query: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    CRUD: Execute write Cypher query in Neo4j
    
    Args:
        cypher_query: Cypher query string
        parameters: Query parameters
        
    Returns:
        Write result or error
    """
    try:
        
        with _neo4j_driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            summary = result.consume()
            
            return {
                'success': True,
                'query': cypher_query,
                'nodes_created': summary.counters.nodes_created,
                'relationships_created': summary.counters.relationships_created,
                'properties_set': summary.counters.properties_set
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': cypher_query
        }
