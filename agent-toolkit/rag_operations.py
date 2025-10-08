"""
Production RAG Operations
Complete RAG pipeline for document ingestion and retrieval
"""

import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from crud_operations import (
    generate_embedding_crud,
    search_pinecone_crud,
    upsert_pinecone_crud,
    search_neo4j_crud,
    execute_neo4j_write_crud,
    read_dynamodb_crud,
    write_dynamodb_crud,
    NEO4J_AVAILABLE
)

logger = logging.getLogger(__name__)

def rag_search_crud(query: str, limit: int = 5, filter_dict: Dict[str, Any] = None, namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Complete RAG search pipeline
    
    Args:
        query: User query text
        limit: Maximum number of results
        filter_dict: Pinecone metadata filter
        namespace: Pinecone namespace
        
    Returns:
        RAG search results with context
    """
    try:
        # Step 1: Generate embedding
        embedding_result = generate_embedding_crud(query)
        if not embedding_result['success']:
            return embedding_result
        
        # Step 2: Search Pinecone
        search_result = search_pinecone_crud(
            query_vector=embedding_result['embedding'],
            limit=limit,
            filter_dict=filter_dict,
            namespace=namespace
        )
        
        if not search_result['success']:
            return search_result
        
        # Step 3: Get additional context from Neo4j
        neo4j_context = []
        if search_result['matches']:
            # Extract document IDs from Pinecone results
            doc_ids = [match['document_id'] for match in search_result['matches'] if match.get('document_id')]
            
            if doc_ids:
                # Query Neo4j for relationships
                cypher_query = """
                MATCH (d:Document)-[r]-(related)
                WHERE d.id IN $doc_ids
                RETURN d.id as document_id, 
                       type(r) as relationship_type, 
                       related.id as related_id,
                       related.title as related_title,
                       related.type as related_type
                LIMIT 20
                """
                
                neo4j_result = search_neo4j_crud(cypher_query, {'doc_ids': doc_ids})
                if neo4j_result['success']:
                    neo4j_context = neo4j_result['data']
        
        # Step 4: Get detailed metadata from DynamoDB
        dynamodb_context = []
        if search_result['matches']:
            # Get document metadata for each match
            for match in search_result['matches']:
                if match.get('document_id'):
                    doc_result = read_dynamodb_crud(
                        table_name=os.environ.get('DYNAMODB_TABLE', 'chatbot-knowledge-base-metadata'),
                        key={'document_id': match['document_id']}
                    )
                    if doc_result['success']:
                        dynamodb_context.append(doc_result['data'])
        
        return {
            'success': True,
            'query': query,
            'matches': search_result['matches'],
            'neo4j_context': neo4j_context,
            'dynamodb_context': dynamodb_context,
            'total_matches': search_result['total_matches'],
            'namespace': search_result['namespace']
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'query': query
        }

def rag_upsert_document_crud(document_id: str, chunks: List[Dict[str, Any]], metadata: Dict[str, Any], namespace: str = None) -> Dict[str, Any]:
    """
    CRUD: Complete RAG document ingestion pipeline
    
    Args:
        document_id: Unique document identifier
        chunks: List of text chunks with metadata
        metadata: Document metadata
        namespace: Pinecone namespace
        
    Returns:
        Upsert result
    """
    try:
        results = {
            'success': True,
            'document_id': document_id,
            'chunks_processed': 0,
            'pinecone_upserted': 0,
            'dynamodb_stored': 0,
            'neo4j_created': 0,
            'errors': []
        }
        
        # Step 1: Process each chunk
        vectors_to_upsert = []
        for i, chunk in enumerate(chunks):
            try:
                # Generate embedding
                embedding_result = generate_embedding_crud(chunk['text'])
                if not embedding_result['success']:
                    results['errors'].append(f"Chunk {i}: {embedding_result['error']}")
                    continue
                
                # Prepare vector for Pinecone
                chunk_id = f"{document_id}_chunk_{i}"
                vector_data = {
                    'id': chunk_id,
                    'values': embedding_result['embedding'],
                    'metadata': {
                        'text': chunk['text'],
                        'document_id': document_id,
                        'chunk_id': chunk_id,
                        'chunk_index': i,
                        'source': metadata.get('source', ''),
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', ''),
                        'created_at': datetime.now().isoformat(),
                        **chunk.get('metadata', {})
                    }
                }
                vectors_to_upsert.append(vector_data)
                results['chunks_processed'] += 1
                
            except Exception as e:
                results['errors'].append(f"Chunk {i}: {str(e)}")
        
        # Step 2: Upsert to Pinecone
        if vectors_to_upsert:
            pinecone_result = upsert_pinecone_crud(vectors_to_upsert, namespace)
            if pinecone_result['success']:
                results['pinecone_upserted'] = len(vectors_to_upsert)
            else:
                results['errors'].append(f"Pinecone upsert: {pinecone_result['error']}")
        
        # Step 3: Store metadata in DynamoDB
        dynamodb_item = {
            'document_id': document_id,
            'title': metadata.get('title', ''),
            'source': metadata.get('source', ''),
            'author': metadata.get('author', ''),
            'content_type': metadata.get('content_type', ''),
            'chunk_count': len(chunks),
            'created_at': datetime.now().isoformat(),
            'status': 'processed',
            'metadata': metadata
        }
        
        dynamodb_result = write_dynamodb_crud(
            table_name=os.environ.get('DYNAMODB_TABLE', 'chatbot-knowledge-base-metadata'),
            item=dynamodb_item
        )
        if dynamodb_result['success']:
            results['dynamodb_stored'] = 1
        else:
            results['errors'].append(f"DynamoDB write: {dynamodb_result['error']}")
        
        # Step 4: Create Neo4j relationships
        if vectors_to_upsert:
            try:
                # Create document node
                create_doc_query = """
                MERGE (d:Document {id: $document_id})
                SET d.title = $title,
                    d.source = $source,
                    d.author = $author,
                    d.created_at = $created_at
                """
                
                neo4j_result = execute_neo4j_write_crud(create_doc_query, {
                    'document_id': document_id,
                    'title': metadata.get('title', ''),
                    'source': metadata.get('source', ''),
                    'author': metadata.get('author', ''),
                    'created_at': datetime.now().isoformat()
                })
                
                if neo4j_result['success']:
                    results['neo4j_created'] += 1
                else:
                    results['errors'].append(f"Neo4j document: {neo4j_result['error']}")
                
                # Create chunk nodes and relationships
                for chunk in vectors_to_upsert:
                    chunk_query = """
                    MATCH (d:Document {id: $document_id})
                    MERGE (c:Chunk {id: $chunk_id})
                    SET c.text = $text,
                        c.chunk_index = $chunk_index,
                        c.created_at = $created_at
                    MERGE (d)-[:CONTAINS]->(c)
                    """
                    
                    execute_neo4j_write_crud(chunk_query, {
                        'document_id': document_id,
                        'chunk_id': chunk['id'],
                        'text': chunk['metadata']['text'],
                        'chunk_index': chunk['metadata']['chunk_index'],
                        'created_at': chunk['metadata']['created_at']
                    })
                
            except Exception as e:
                results['errors'].append(f"Neo4j relationships: {str(e)}")
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'document_id': document_id
        }

def rag_chunk_document_crud(document_text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict[str, Any]]:
    """
    CRUD: Chunk document text for RAG processing
    
    Args:
        document_text: Full document text
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    try:
        chunks = []
        start = 0
        
        while start < len(document_text):
            end = start + chunk_size
            chunk_text = document_text[start:end]
            
            # Try to break at sentence boundary
            if end < len(document_text):
                last_period = chunk_text.rfind('.')
                last_newline = chunk_text.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:  # Don't make chunks too small
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1
            
            chunks.append({
                'text': chunk_text.strip(),
                'start_pos': start,
                'end_pos': end,
                'chunk_size': len(chunk_text)
            })
            
            start = end - chunk_overlap
            if start >= len(document_text):
                break
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking document: {e}")
        return [{'text': document_text, 'start_pos': 0, 'end_pos': len(document_text), 'chunk_size': len(document_text)}]
