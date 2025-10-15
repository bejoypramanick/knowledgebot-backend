#!/usr/bin/env python3
"""
LLM Agent Example - Shows how an LLM agent intelligently routes queries to MCP servers
This demonstrates the correct architecture where the LLM agent determines which MCP server to use
"""

import asyncio
import json
import logging
from typing import Dict, Any, List
from openai import OpenAI
from microservices.mcp_client import UniversalMCPClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntelligentLLMAgent:
    """LLM Agent that intelligently routes queries to appropriate MCP servers"""
    
    def __init__(self, openai_api_key: str):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.mcp_client = UniversalMCPClient()
    
    async def process_query(self, user_query: str) -> Dict[str, Any]:
        """Process a natural language query and route to appropriate MCP servers"""
        
        # Use OpenAI to analyze the query and determine which MCP servers to use
        analysis_prompt = f"""
        Analyze this user query and determine which MCP servers and operations are needed:
        
        User Query: "{user_query}"
        
        Available MCP servers and their capabilities:
        1. Pinecone MCP Server:
           - Vector search and similarity search
           - Document indexing and retrieval
           - Semantic search operations
           
        2. DynamoDB MCP Server:
           - Database table operations
           - CRUD operations on structured data
           - Data storage and retrieval
           
        3. Docling MCP Server:
           - Document processing and parsing
           - Text extraction and chunking
           - Document analysis
           
        4. Neo4j Cypher MCP Server:
           - Graph database query operations
           - Cypher query execution
           - Graph data retrieval and analysis
           
        5. Neo4j Data Modeling MCP Server:
           - Graph schema design and validation
           - Node and relationship creation
           - Graph data modeling operations
        
        Respond with a JSON object containing:
        - required_servers: List of MCP servers needed
        - operations: List of specific operations to perform
        - reasoning: Why these servers and operations are needed
        - parameters: Parameters for each operation
        """
        
        try:
            analysis_response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an AI assistant that analyzes queries and determines appropriate MCP server operations."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            analysis = json.loads(analysis_response.choices[0].message.content)
            logger.info(f"Query analysis: {analysis}")
            
            # Execute operations based on analysis
            results = {}
            
            async with self.mcp_client as client:
                for server in analysis.get("required_servers", []):
                    server_results = []
                    
                    if server == "pinecone":
                        # Handle Pinecone operations
                        if "search" in analysis.get("operations", []):
                            search_result = await client.pinecone_search(
                                index_name=analysis.get("parameters", {}).get("index_name", "default"),
                                query=user_query,
                                top_k=analysis.get("parameters", {}).get("top_k", 10)
                            )
                            server_results.append({"operation": "search", "result": search_result})
                    
                    elif server == "dynamodb":
                        # Handle DynamoDB operations
                        if "list_tables" in analysis.get("operations", []):
                            tables_result = await client.dynamodb_list_tables()
                            server_results.append({"operation": "list_tables", "result": tables_result})
                        
                        if "scan" in analysis.get("operations", []):
                            scan_result = await client.dynamodb_scan(
                                table_name=analysis.get("parameters", {}).get("table_name", "default")
                            )
                            server_results.append({"operation": "scan", "result": scan_result})
                    
                    elif server == "docling":
                        # Handle Docling operations
                        if "process_document" in analysis.get("operations", []):
                            doc_result = await client.docling_process_document(
                                content=analysis.get("parameters", {}).get("content", user_query)
                            )
                            server_results.append({"operation": "process_document", "result": doc_result})
                    
                    elif server == "neo4j-cypher":
                        # Handle Neo4j Cypher operations
                        if "execute_query" in analysis.get("operations", []):
                            cypher_result = await client.neo4j_execute_query(
                                cypher=analysis.get("parameters", {}).get("cypher", "MATCH (n) RETURN n LIMIT 10")
                            )
                            server_results.append({"operation": "execute_query", "result": cypher_result})
                        
                        if "list_nodes" in analysis.get("operations", []):
                            nodes_result = await client.neo4j_list_nodes(
                                label=analysis.get("parameters", {}).get("label"),
                                limit=analysis.get("parameters", {}).get("limit", 100)
                            )
                            server_results.append({"operation": "list_nodes", "result": nodes_result})
                    
                    elif server == "neo4j-modeling":
                        # Handle Neo4j Data Modeling operations
                        if "create_node" in analysis.get("operations", []):
                            node_result = await client.neo4j_create_node(
                                label=analysis.get("parameters", {}).get("label", "Node"),
                                properties=analysis.get("parameters", {}).get("properties", {})
                            )
                            server_results.append({"operation": "create_node", "result": node_result})
                        
                        if "validate_schema" in analysis.get("operations", []):
                            schema_result = await client.neo4j_validate_schema(
                                schema=analysis.get("parameters", {}).get("schema", {})
                            )
                            server_results.append({"operation": "validate_schema", "result": schema_result})
                    
                    results[server] = server_results
            
            # Generate final response using OpenAI
            final_prompt = f"""
            Based on the user query and the results from MCP servers, provide a comprehensive response:
            
            User Query: "{user_query}"
            Analysis: {json.dumps(analysis, indent=2)}
            MCP Results: {json.dumps(results, indent=2)}
            
            Provide a natural, helpful response that incorporates the relevant information from the MCP servers.
            """
            
            final_response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful AI assistant that provides comprehensive responses based on data from various MCP servers."},
                    {"role": "user", "content": final_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return {
                "success": True,
                "user_query": user_query,
                "analysis": analysis,
                "mcp_results": results,
                "final_response": final_response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "success": False,
                "error": str(e),
                "user_query": user_query
            }

# Example usage
async def main():
    """Example of how to use the intelligent LLM agent"""
    
    # Initialize the agent
    agent = IntelligentLLMAgent(openai_api_key="your-openai-api-key")
    
    # Example queries that would be routed to different MCP servers
    example_queries = [
        "Find documents similar to 'machine learning algorithms'",
        "List all tables in my database",
        "Process this PDF document and extract key information",
        "Find all users connected to user John in the social network",
        "Create a new Person node in the graph database",
        "Validate the schema for my social network graph",
        "Search for research papers about climate change and store the results"
    ]
    
    for query in example_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = await agent.process_query(query)
        
        if result["success"]:
            print(f"Response: {result['final_response']}")
            print(f"Used MCP servers: {list(result['mcp_results'].keys())}")
        else:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())
