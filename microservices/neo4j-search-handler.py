#!/usr/bin/env python3
"""
Neo4j Graph Search - Single Purpose Lambda
Searches Neo4j graph database
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

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Search Neo4j graph database"""
    logger.info("=== NEO4J SEARCH STARTED ===")
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Extract parameters
        cypher_query = body.get('cypher_query', '')
        parameters = body.get('parameters', {})
        
        if not cypher_query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Cypher query is required"})
            }
        
        if not neo4j_driver:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Neo4j not available"})
            }
        
        # Execute query
        with neo4j_driver.session() as session:
            result = session.run(cypher_query, parameters)
            records = [dict(record) for record in result]
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": True,
                "results": records,
                "total_results": len(records),
                "query": cypher_query
            })
        }
        
    except Exception as e:
        logger.error(f"Error searching Neo4j: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
