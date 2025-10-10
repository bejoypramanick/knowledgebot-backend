#!/usr/bin/env python3
"""
Agent Query Handler - Intelligent Query Processing
Handles chat queries, decides which tools to call, splits tasks, and compiles answers
No document processing - only query handling and response generation
"""

import json
import os
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import traceback

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Import AWS clients
import boto3
lambda_client = boto3.client('lambda')

# Import agent tools
from rag_agent import (
    search_pinecone_tool,
    search_neo4j_tool,
    read_dynamodb_tool,
    read_s3_data_tool,
    rag_search_with_hierarchical_context_tool
)

def analyze_query_complexity(query: str) -> Dict[str, Any]:
    """Analyze query complexity and determine processing strategy"""
    try:
        # Simple heuristics for query analysis
        query_lower = query.lower()
        
        # Check for multi-part questions
        question_indicators = ['?', 'what', 'how', 'why', 'when', 'where', 'which', 'who']
        question_count = sum(1 for indicator in question_indicators if indicator in query_lower)
        
        # Check for complex operations
        complex_indicators = [
            'compare', 'analyze', 'summarize', 'explain', 'describe',
            'find all', 'list all', 'show me', 'give me', 'tell me about'
        ]
        is_complex = any(indicator in query_lower for indicator in complex_indicators)
        
        # Check for specific data sources
        needs_pinecone = any(term in query_lower for term in ['similar', 'related', 'find documents', 'search'])
        needs_neo4j = any(term in query_lower for term in ['relationship', 'connect', 'graph', 'network'])
        needs_dynamodb = any(term in query_lower for term in ['metadata', 'details', 'information'])
        needs_s3 = any(term in query_lower for term in ['content', 'text', 'document'])
        
        complexity_score = question_count + (2 if is_complex else 0)
        
        return {
            "complexity_score": complexity_score,
            "is_complex": is_complex,
            "question_count": question_count,
            "needs_pinecone": needs_pinecone,
            "needs_neo4j": needs_neo4j,
            "needs_dynamodb": needs_dynamodb,
            "needs_s3": needs_s3,
            "processing_strategy": "parallel" if complexity_score > 3 else "sequential"
        }
        
    except Exception as e:
        logger.error(f"Error analyzing query complexity: {e}")
        return {
            "complexity_score": 1,
            "is_complex": False,
            "question_count": 1,
            "needs_pinecone": True,
            "needs_neo4j": False,
            "needs_dynamodb": False,
            "needs_s3": False,
            "processing_strategy": "sequential"
        }

def decompose_complex_query(query: str) -> List[str]:
    """Decompose complex queries into sub-questions"""
    try:
        # Simple decomposition logic
        sub_questions = []
        
        # Split by common separators
        separators = [' and ', ' also ', ' furthermore ', ' additionally ', ' plus ']
        
        current_query = query
        for separator in separators:
            if separator in current_query.lower():
                parts = current_query.split(separator)
                sub_questions.extend([part.strip() for part in parts if part.strip()])
                break
        
        # If no decomposition occurred, return original query
        if not sub_questions:
            sub_questions = [query]
        
        # Clean up sub-questions
        cleaned_questions = []
        for q in sub_questions:
            q = q.strip()
            if q and len(q) > 5:  # Filter out very short fragments
                cleaned_questions.append(q)
        
        return cleaned_questions if cleaned_questions else [query]
        
    except Exception as e:
        logger.error(f"Error decomposing query: {e}")
        return [query]

async def execute_search_strategy(query: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Execute search strategy based on query analysis"""
    try:
        results = {
            "pinecone_results": [],
            "neo4j_results": [],
            "dynamodb_results": [],
            "s3_results": [],
            "rag_results": []
        }
        
        # Execute searches based on analysis
        if analysis.get("needs_pinecone"):
            logger.info("Executing Pinecone search")
            try:
                pinecone_result = search_pinecone_tool(query, limit=10)
                results["pinecone_results"] = json.loads(pinecone_result) if isinstance(pinecone_result, str) else pinecone_result
            except Exception as e:
                logger.error(f"Pinecone search failed: {e}")
        
        if analysis.get("needs_neo4j"):
            logger.info("Executing Neo4j search")
            try:
                neo4j_result = search_neo4j_tool(query)
                results["neo4j_results"] = json.loads(neo4j_result) if isinstance(neo4j_result, str) else neo4j_result
            except Exception as e:
                logger.error(f"Neo4j search failed: {e}")
        
        if analysis.get("needs_dynamodb"):
            logger.info("Executing DynamoDB search")
            try:
                # This would need to be implemented based on your DynamoDB schema
                dynamodb_result = read_dynamodb_tool("document-metadata", query)
                results["dynamodb_results"] = json.loads(dynamodb_result) if isinstance(dynamodb_result, str) else dynamodb_result
            except Exception as e:
                logger.error(f"DynamoDB search failed: {e}")
        
        # Always execute RAG search for comprehensive results
        logger.info("Executing RAG search")
        try:
            rag_result = rag_search_with_hierarchical_context_tool(query, limit=5)
            results["rag_results"] = json.loads(rag_result) if isinstance(rag_result, str) else rag_result
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error executing search strategy: {e}")
        return {"error": str(e)}

def synthesize_response(query: str, search_results: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Synthesize search results into a coherent response"""
    try:
        # Extract relevant information from search results
        all_sources = []
        all_content = []
        
        # Process Pinecone results
        pinecone_results = search_results.get("pinecone_results", [])
        for result in pinecone_results:
            if isinstance(result, dict):
                content = result.get("text", result.get("content", ""))
                if content:
                    all_content.append(content)
                    all_sources.append({
                        "source": "vector_search",
                        "text": content[:200] + "..." if len(content) > 200 else content,
                        "score": result.get("score", 0)
                    })
        
        # Process RAG results
        rag_results = search_results.get("rag_results", [])
        for result in rag_results:
            if isinstance(result, dict):
                content = result.get("text", result.get("content", ""))
                if content:
                    all_content.append(content)
                    all_sources.append({
                        "source": "rag_search",
                        "text": content[:200] + "..." if len(content) > 200 else content,
                        "score": result.get("score", 0)
                    })
        
        # Process Neo4j results
        neo4j_results = search_results.get("neo4j_results", [])
        for result in neo4j_results:
            if isinstance(result, dict):
                content = str(result)
                all_content.append(content)
                all_sources.append({
                    "source": "graph_search",
                    "text": content[:200] + "..." if len(content) > 200 else content,
                    "score": 1.0
                })
        
        # Generate response based on content
        if all_content:
            # Simple response generation (in production, you'd use a more sophisticated approach)
            response_text = f"Based on the available information, here's what I found:\n\n"
            
            # Add relevant content
            for i, content in enumerate(all_content[:5]):  # Limit to top 5 results
                response_text += f"{i+1}. {content[:300]}...\n\n"
            
            # Add summary if multiple sources
            if len(all_sources) > 1:
                response_text += f"\nI found {len(all_sources)} relevant sources that address your query."
        else:
            response_text = "I couldn't find specific information to answer your query. Please try rephrasing your question or check if the relevant documents have been processed."
        
        return {
            "response": response_text,
            "sources": all_sources[:10],  # Limit to top 10 sources
            "total_sources": len(all_sources),
            "search_strategy": analysis.get("processing_strategy", "sequential"),
            "tools_used": list(search_results.keys())
        }
        
    except Exception as e:
        logger.error(f"Error synthesizing response: {e}")
        return {
            "response": "I encountered an error while processing your query. Please try again.",
            "sources": [],
            "error": str(e)
        }

async def process_query_intelligently(query: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
    """Main query processing function"""
    start_time = datetime.now()
    
    try:
        logger.info(f"Processing query: {query}")
        
        # Step 1: Analyze query complexity
        analysis = analyze_query_complexity(query)
        logger.info(f"Query analysis: {analysis}")
        
        # Step 2: Decompose complex queries
        if analysis["is_complex"]:
            sub_queries = decompose_complex_query(query)
            logger.info(f"Decomposed into {len(sub_queries)} sub-queries")
        else:
            sub_queries = [query]
        
        # Step 3: Execute search strategy for each sub-query
        all_results = []
        for sub_query in sub_queries:
            logger.info(f"Processing sub-query: {sub_query}")
            search_results = await execute_search_strategy(sub_query, analysis)
            all_results.append({
                "query": sub_query,
                "results": search_results
            })
        
        # Step 4: Synthesize responses
        if len(sub_queries) == 1:
            # Single query - direct synthesis
            response = synthesize_response(query, all_results[0]["results"], analysis)
        else:
            # Multiple queries - synthesize each and combine
            individual_responses = []
            all_sources = []
            
            for result in all_results:
                individual_response = synthesize_response(result["query"], result["results"], analysis)
                individual_responses.append(individual_response)
                all_sources.extend(individual_response.get("sources", []))
            
            # Combine responses
            combined_response = f"I'll address each part of your question:\n\n"
            for i, resp in enumerate(individual_responses):
                combined_response += f"**Part {i+1}:** {resp['response']}\n\n"
            
            response = {
                "response": combined_response,
                "sources": all_sources[:10],
                "total_sources": len(all_sources),
                "sub_responses": individual_responses
            }
        
        # Add metadata
        processing_time = (datetime.now() - start_time).total_seconds()
        response.update({
            "query": query,
            "processing_time": processing_time,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Query processing completed in {processing_time:.2f}s")
        return response
        
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return {
            "response": "I encountered an error while processing your query. Please try again.",
            "sources": [],
            "error": str(e),
            "processing_time": (datetime.now() - start_time).total_seconds()
        }

@production_error_handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for intelligent query processing with production error handling"""
    logger.info("=== AGENT QUERY HANDLER STARTED ===")
    
    try:
        # Extract query from event
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        query = body.get('message', body.get('user_query', body.get('query', '')))
        conversation_history = body.get('conversation_history', [])
        
        if not query:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "Query is required",
                    "error_category": "missing_query"
                })
            }
        
        # Process query
        result = asyncio.run(process_query_intelligently(query, conversation_history))
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error in Lambda handler: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "I apologize, but I encountered an error while processing your request. Please try again.",
                "error_category": "internal_error",
                "error_type": type(e).__name__
            })
        }
