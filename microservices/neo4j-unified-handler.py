#!/usr/bin/env python3
"""
Neo4j Unified Handler - Single Purpose Lambda
Handles both Neo4j search and write operations
"""

import json
import os
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Neo4j
try:
    from neo4j import GraphDatabase
    neo4j_uri = os.environ.get('NEO4J_URI')
    neo4j_user = os.environ.get('NEO4J_USER')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')
    
    neo4j_driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    logger.info("Neo4j initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Neo4j: {e}")
    neo4j_driver = None

def execute_neo4j_query(cypher_query: str, parameters: Dict[str, Any] = None, operation_type: str = "read") -> Dict[str, Any]:
    """Execute Neo4j query with proper error handling"""
    try:
        if not neo4j_driver:
            return {
                "success": False,
                "error": "Neo4j not available"
            }
        
        with neo4j_driver.session() as session:
            if operation_type == "write":
                # For write operations, use write transaction
                result = session.execute_write(lambda tx: tx.run(cypher_query, parameters or {}))
            else:
                # For read operations, use read transaction
                result = session.execute_read(lambda tx: tx.run(cypher_query, parameters or {}))
            
            records = [dict(record) for record in result]
            
            return {
                "success": True,
                "records": records,
                "query": cypher_query,
                "parameters": parameters,
                "operation_type": operation_type,
                "total_results": len(records)
            }
    except Exception as e:
        logger.error(f"Error executing Neo4j query: {e}")
        return {
            "success": False,
            "error": str(e),
            "query": cypher_query,
            "operation_type": operation_type
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Unified Neo4j handler for both search and write operations"""
    logger.info("=== NEO4J UNIFIED HANDLER STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        cypher_query = body.get('cypher_query', '')
        parameters = body.get('parameters', {})
        operation_type = body.get('operation_type', 'read')  # 'read' or 'write'
        
        if not cypher_query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Cypher query is required"})
            }
        
        # Validate operation type
        if operation_type not in ['read', 'write']:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Operation type must be 'read' or 'write'"})
            }
        
        # Execute query
        result = execute_neo4j_query(cypher_query, parameters, operation_type)
        
        return {
            "statusCode": 200 if result["success"] else 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in Neo4j unified handler: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
