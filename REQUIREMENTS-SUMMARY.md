# Requirements Files Summary

## Current Architecture Requirements

### ✅ **Active Requirements Files**

#### `requirements-docker-lambdas.txt`
- **Purpose**: Heavy library installations for Docker Lambdas
- **Contains**: docling, pinecone-client, neo4j, openai, sentence-transformers, torch, transformers
- **Used by**: All Docker-based Lambda functions (library handlers)

#### `requirements-zip-lambdas.txt`  
- **Purpose**: Minimal dependencies for Zip Lambdas
- **Contains**: Only boto3, botocore (AWS SDK)
- **Used by**: All Zip-based Lambda functions (business logic)

### 📁 **Legacy Requirements Files** (Can be archived/removed)

These files are from the old architecture and are no longer needed:

- `requirements-base-layer.txt` - Old layered architecture
- `requirements-chat-generator.txt` - Old chat generator
- `requirements-core-layer.txt` - Old core layer
- `requirements-database-layer.txt` - Old database layer
- `requirements-docling-unified.txt` - Old unified docling
- `requirements-dynamodb-crud.txt` - Old DynamoDB CRUD
- `requirements-easyocr-layer.txt` - Old EasyOCR layer
- `requirements-embedding-generator.txt` - Old embedding generator
- `requirements-intelligent-agent.txt` - Old intelligent agent
- `requirements-ml-layer.txt` - Old ML layer
- `requirements-neo4j-unified.txt` - Old unified Neo4j
- `requirements-pdf-processor-layer.txt` - Old PDF processor layer
- `requirements-pinecone-unified.txt` - Old unified Pinecone
- `requirements-s3-unified.txt` - Old unified S3
- `requirements-table-detector-layer.txt` - Old table detector layer

## Architecture Benefits

✅ **Clean Separation**: Docker Lambdas handle heavy libraries, Zip Lambdas handle business logic  
✅ **Minimal Dependencies**: Zip Lambdas only need AWS SDK  
✅ **Efficient Deployment**: No dependency conflicts between functions  
✅ **Easy Maintenance**: Clear distinction between library and business logic requirements  

## Usage

- **Docker Lambdas**: Use `requirements-docker-lambdas.txt` for library installations
- **Zip Lambdas**: Use `requirements-zip-lambdas.txt` for business logic
- **GitHub Actions**: Automatically uses correct requirements file for each deployment type
