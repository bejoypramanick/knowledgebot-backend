# Docling Integration in Microservices Architecture

## Overview

This document outlines the comprehensive integration of Docling features across the microservices architecture, providing advanced document processing, visualization, and metadata capabilities.

## Docling-Enabled Lambdas

### 1. **RAG Processor Lambda** (`chatbot-rag-processor`)
- **Primary Docling User**: Document ingestion and processing
- **Features**:
  - Document conversion (PDF, DOCX, etc.)
  - Hierarchical chunking with structure awareness
  - OCR and table structure extraction
  - Metadata generation with Docling-specific information
  - Embedding generation for processed content

### 2. **Enhanced RAG Search Lambda** (`chatbot-rag-search`)
- **Enhanced with Docling**: Advanced search with visualization features
- **New Features**:
  - **Structure-based search**: Search within headings, tables, figures
  - **Visual metadata enhancement**: Bounding boxes, positioning, visual indicators
  - **Document visualization data**: Complete document structure for UI rendering
  - **Hierarchy tree building**: Document navigation structure
  - **Element type classification**: Structural, visual, tabular elements

## Enhanced RAG Search Capabilities

### **New API Endpoints:**

#### 1. **Enhanced Search** (`search`)
```json
{
  "action": "search",
  "query": "machine learning algorithms",
  "limit": 5
}
```

**Response includes:**
- Enhanced metadata with Docling features
- Visual positioning information
- Document structure classification
- Element type analysis
- Hierarchy information

#### 2. **Structure-Based Search** (`search_by_structure`)
```json
{
  "action": "search_by_structure",
  "query": "performance metrics",
  "structure_type": "tables",
  "limit": 5
}
```

**Structure Types:**
- `"headings"` - Search only in headings and titles
- `"tables"` - Search only in table content
- `"figures"` - Search only in figures and images
- `"all"` - Search in all content types

#### 3. **Document Visualization** (`get_document_visualization`)
```json
{
  "action": "get_document_visualization",
  "document_id": "doc-123"
}
```

**Response includes:**
- Complete document structure
- Visual elements with positioning
- Hierarchy tree for navigation
- Element counts by type
- Page-by-page breakdown

## Docling Features Integration

### **1. Visual Metadata Enhancement**
```python
{
  "docling_element_type": "Table",
  "visual_position": {
    "x": 100, "y": 200, "width": 300, "height": 150
  },
  "document_structure": {
    "hierarchy_level": 2,
    "is_heading": false,
    "is_table": true,
    "is_figure": false
  },
  "processing_info": {
    "processed_at": "2024-01-01T00:00:00Z",
    "source": "document.pdf",
    "page_number": 3
  }
}
```

### **2. Docling Features Extraction**
```python
{
  "docling_features": {
    "element_type": "Table",
    "is_structural": false,
    "is_visual": false,
    "is_tabular": true,
    "hierarchy_info": {
      "level": 2,
      "parent_id": "heading-1",
      "has_children": false
    },
    "visual_indicators": {
      "has_position": true,
      "has_color": false,
      "position": {"x": 100, "y": 200, "width": 300, "height": 150}
    }
  }
}
```

### **3. Document Structure Analysis**
```python
{
  "document_structure": {
    "headings": [
      {"chunk_id": "h1-1", "content": "Introduction", "hierarchy_level": 1},
      {"chunk_id": "h2-1", "content": "Background", "hierarchy_level": 2}
    ],
    "tables": [
      {"chunk_id": "t1-1", "content": "Performance Metrics Table", "hierarchy_level": 3}
    ],
    "figures": [
      {"chunk_id": "f1-1", "content": "Algorithm Flowchart", "hierarchy_level": 3}
    ],
    "text_blocks": [...]
  }
}
```

## Frontend Integration Benefits

### **1. Enhanced Source Cards**
- **Visual positioning** for highlighting in documents
- **Element type icons** (table, figure, heading)
- **Hierarchy navigation** (parent/child relationships)
- **Page-specific rendering** with bounding boxes

### **2. Document Viewer**
- **Structure-based navigation** (jump to headings, tables, figures)
- **Visual element highlighting** with exact positioning
- **Hierarchy tree** for document outline
- **Element type filtering** (show only tables, figures, etc.)

### **3. Advanced Search UI**
- **Structure type filters** (search in headings only, tables only)
- **Visual preview** of search results
- **Document structure sidebar** for navigation
- **Element type indicators** in search results

## Architecture Benefits

### **1. Centralized Docling Processing**
- **RAG Processor**: Handles all document conversion and chunking
- **Enhanced RAG Search**: Leverages Docling metadata for advanced search
- **Other Lambdas**: Work with processed Docling data

### **2. Rich Metadata Pipeline**
```
Document → RAG Processor (Docling) → Enhanced Metadata → RAG Search (Visualization) → Frontend
```

### **3. Scalable Visualization**
- **Document structure** cached in DynamoDB
- **Visual metadata** stored with embeddings
- **Hierarchy trees** built on-demand
- **Element positioning** for precise highlighting

## Performance Considerations

### **Memory Allocation:**
- **RAG Processor**: 2048MB (Docling + sentence-transformers)
- **Enhanced RAG Search**: 2048MB (Docling + sentence-transformers + visualization)
- **Other Lambdas**: 256-1024MB (lightweight operations)

### **Caching Strategy:**
- **Document structure** cached in DynamoDB
- **Visual metadata** stored with chunk data
- **Hierarchy trees** computed on-demand
- **Embeddings** cached in S3

## Deployment Notes

### **Dependencies:**
- **RAG Processor**: `docling>=1.0.0`, `sentence-transformers`, `numpy`
- **Enhanced RAG Search**: `docling>=1.0.0`, `sentence-transformers`, `numpy`
- **System Dependencies**: `gcc`, `gcc-c++` for Docling compilation

### **Environment Variables:**
- `MAIN_BUCKET`: S3 bucket for document storage
- `KNOWLEDGE_BASE_TABLE`: DynamoDB table for chunk metadata
- `DOCLING_CACHE_TTL`: Cache time-to-live for document structures

## Future Enhancements

### **1. Real-time Document Updates**
- **Live structure updates** when documents change
- **Incremental processing** for document modifications
- **Version-aware visualization** for document history

### **2. Advanced Visual Features**
- **Document thumbnails** with element highlighting
- **Interactive document maps** with clickable elements
- **Multi-document comparison** with structure analysis
- **Collaborative annotations** with Docling positioning

### **3. AI-Powered Insights**
- **Document summarization** using structure awareness
- **Content relationship mapping** between elements
- **Automatic tagging** based on Docling element types
- **Smart search suggestions** using document structure

This comprehensive Docling integration provides a rich, visual, and structured approach to document processing and search, enabling advanced UI features and better user experience.
