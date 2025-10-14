#!/usr/bin/env python3
"""
Neo4j Library Handler - Docker Lambda
ONLY handles Neo4j library imports and initialization
All business logic happens in Zip Lambdas
"""

import json
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize Neo4j - THIS IS THE ONLY PURPOSE OF THIS DOCKER LAMBDA
try:
    from neo4j import GraphDatabase
    neo4j_uri = os.environ.get('NEO4J_URI')
    neo4j_user = os.environ.get('NEO4J_USER')
    neo4j_password = os.environ.get('NEO4J_PASSWORD')
    
    neo4j_driver = GraphDatabase.driver(
        neo4j_uri,
        auth=(neo4j_user, neo4j_password)
    )
    logger.info("✅ Neo4j library imported and initialized successfully")
    
    # Export the initialized components for use by Zip Lambdas
    NEO4J_COMPONENTS = {
        "GraphDatabase": GraphDatabase,
        "neo4j_driver": neo4j_driver
    }
    
except Exception as e:
    logger.error(f"❌ Failed to initialize Neo4j library: {e}")
    NEO4J_COMPONENTS = None

def lambda_handler(event, context):
    """Neo4j Library Handler - ONLY library imports and initialization"""
    logger.info("=== NEO4J LIBRARY HANDLER STARTED ===")
    
    try:
        if NEO4J_COMPONENTS is None:
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "success": False,
                    "error": "Neo4j library not available"
                })
            }
        
        # Return success - library is loaded and ready
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Neo4j library loaded successfully",
                "components_available": list(NEO4J_COMPONENTS.keys())
            })
        }
        
    except Exception as e:
        logger.error(f"Error in Neo4j library handler: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": str(e)
            })
        }
