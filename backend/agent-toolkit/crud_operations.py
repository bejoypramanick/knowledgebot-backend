"""
CRUD Tools Only - Pure Data Operations
All business logic and formatting handled by AgentBuilder model
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
    PINECONE_AVAILABLE = False
    NEO4J_AVAILABLE = False
    _pinecone_index = None
    _neo4j_driver = None
    _embedding_model = None
    
    # Try to initialize Pinecone
    try:
        import pinecone
        pinecone.init(
            api_key=os.environ.get('PINECONE_API_KEY'),
            environment=os.environ.get('PINECONE_ENVIRONMENT')
        )
        _pinecone_index = pinecone.Index(os.environ.get('PINECONE_INDEX_NAME'))
        PINECONE_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Pinecone not available: {e}")
    
    # Try to initialize Neo4j
    try:
        from neo4j import GraphDatabase
        _neo4j_driver = GraphDatabase.driver(
            os.environ.get('NEO4J_URI'),
            auth=(os.environ.get('NEO4J_USER'), os.environ.get('NEO4J_PASSWORD'))
        )
        NEO4J_AVAILABLE = True
    except Exception as e:
        logger.warning(f"Neo4j not available: {e}")
    
    # Try to initialize embedding model
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        logger.warning(f"Embedding model not available: {e}")

except Exception as e:
    logger.error(f"Error initializing services: {e}")
    s3_client = None
    dynamodb = None
    PINECONE_AVAILABLE = False
    NEO4J_AVAILABLE = False
    _pinecone_index = None
    _neo4j_driver = None
    _embedding_model = None

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

def search_pinecone_crud(query_vector: List[float], limit: int = 10) -> Dict[str, Any]:
    """
    CRUD: Search Pinecone vector database
    
    Args:
        query_vector: Vector representation of query
        limit: Maximum number of results
        
    Returns:
        Raw Pinecone search results
    """
    try:
        if not PINECONE_AVAILABLE or not _pinecone_index:
            return {
                'success': False,
                'error': 'Pinecone not available'
            }
        
        results = _pinecone_index.query(
            vector=query_vector,
            top_k=limit,
            include_metadata=True
        )
        
        return {
            'success': True,
            'matches': results.matches,
            'namespace': results.namespace,
            'query_vector_length': len(query_vector)
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
        if not NEO4J_AVAILABLE or not _neo4j_driver:
            return {
                'success': False,
                'error': 'Neo4j not available'
            }
        
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
    CRUD: Generate embedding vector for text
    
    Args:
        text: Text to embed
        
    Returns:
        Raw embedding vector or error
    """
    try:
        if not _embedding_model:
            return {
                'success': False,
                'error': 'Embedding model not available'
            }
        
        embedding = _embedding_model.encode(text)
        
        return {
            'success': True,
            'embedding': embedding.tolist(),
            'text_length': len(text),
            'embedding_dimension': len(embedding)
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
        if not PINECONE_AVAILABLE or not _pinecone_index:
            return {
                'success': False,
                'error': 'Pinecone not available'
            }
        
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
        if not PINECONE_AVAILABLE or not _pinecone_index:
            return {
                'success': False,
                'error': 'Pinecone not available'
            }
        
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
        if not NEO4J_AVAILABLE or not _neo4j_driver:
            return {
                'success': False,
                'error': 'Neo4j not available'
            }
        
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
