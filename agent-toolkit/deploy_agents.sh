#!/bin/bash

# Deploy Knowledge Agents
# All business logic and formatting handled by AgentBuilder model

set -e

echo "🧠 Deploying Knowledge Agents..."

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 1. Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# 2. Set up environment variables
echo "🔧 Setting up environment variables..."
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export PINECONE_API_KEY="${PINECONE_API_KEY}"
export PINECONE_ENVIRONMENT="${PINECONE_ENVIRONMENT}"
export PINECONE_INDEX_NAME="${PINECONE_INDEX_NAME}"
export NEO4J_URI="${NEO4J_URI}"
export NEO4J_USER="${NEO4J_USER}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD}"
export AWS_REGION="${AWS_REGION:-ap-south-1}"
export DOCUMENTS_BUCKET="${DOCUMENTS_BUCKET:-chatbot-documents-ap-south-1}"
export EMBEDDINGS_BUCKET="${EMBEDDINGS_BUCKET:-chatbot-embeddings-ap-south-1}"
export KNOWLEDGE_BASE_TABLE="${KNOWLEDGE_BASE_TABLE:-chatbot-knowledge-base}"
export METADATA_TABLE="${METADATA_TABLE:-chatbot-knowledge-base-metadata}"

# 3. Create deployment packages
echo "📦 Creating CRUD agent deployment packages..."

# Create chat agent package
echo "Creating chat agent package..."
zip -r chat-agent.zip \
  lambda_handlers.py \
  unified_ai_agent.py \
  crud_operations.py \
  -x "*.pyc" "*/__pycache__/*" "*.git*"

# Create document processing agent package
echo "Creating document processing agent package..."
zip -r document-agent.zip \
  lambda_handlers.py \
  unified_ai_agent.py \
  crud_operations.py \
  -x "*.pyc" "*/__pycache__/*" "*.git*"

# 4. Deploy Lambda functions
echo "🚀 Deploying Knowledge Lambda functions..."

# Deploy Chat Agent
echo "Deploying Chat Agent..."
aws lambda update-function-code \
  --function-name chatbot-chat-agent \
  --zip-file fileb://chat-agent.zip \
  --region ap-south-1 || \
aws lambda create-function \
  --function-name chatbot-chat-agent \
  --runtime python3.9 \
  --role arn:aws:iam::090163643302:role/chatbot-agent-lambda-role \
  --handler lambda_handlers.lambda_handler_knowledge_chat \
  --zip-file fileb://chat-agent.zip \
  --timeout 900 \
  --memory-size 3008 \
  --region ap-south-1

# Deploy Document Processing Agent
echo "Deploying Document Processing Agent..."
aws lambda update-function-code \
  --function-name chatbot-document-agent \
  --zip-file fileb://document-agent.zip \
  --region ap-south-1 || \
aws lambda create-function \
  --function-name chatbot-document-agent \
  --runtime python3.9 \
  --role arn:aws:iam::090163643302:role/chatbot-agent-lambda-role \
  --handler lambda_handlers.lambda_handler_knowledge_document_ingestion \
  --zip-file fileb://document-agent.zip \
  --timeout 900 \
  --memory-size 3008 \
  --region ap-south-1

# 5. Update Lambda environment variables
echo "🔧 Updating Lambda environment variables..."

# Update Chat Agent environment
aws lambda update-function-configuration \
  --function-name chatbot-chat-agent \
  --environment Variables="{
    OPENAI_API_KEY=${OPENAI_API_KEY},
    PINECONE_API_KEY=${PINECONE_API_KEY},
    PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT},
    PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME},
    NEO4J_URI=${NEO4J_URI},
    NEO4J_USER=${NEO4J_USER},
    NEO4J_PASSWORD=${NEO4J_PASSWORD},
    AWS_REGION=${AWS_REGION},
    DOCUMENTS_BUCKET=${DOCUMENTS_BUCKET},
    EMBEDDINGS_BUCKET=${EMBEDDINGS_BUCKET},
    KNOWLEDGE_BASE_TABLE=${KNOWLEDGE_BASE_TABLE},
    METADATA_TABLE=${METADATA_TABLE}
  }" \
  --region ap-south-1

# Update Document Processing Agent environment
aws lambda update-function-configuration \
  --function-name chatbot-document-agent \
  --environment Variables="{
    OPENAI_API_KEY=${OPENAI_API_KEY},
    PINECONE_API_KEY=${PINECONE_API_KEY},
    PINECONE_ENVIRONMENT=${PINECONE_ENVIRONMENT},
    PINECONE_INDEX_NAME=${PINECONE_INDEX_NAME},
    NEO4J_URI=${NEO4J_URI},
    NEO4J_USER=${NEO4J_USER},
    NEO4J_PASSWORD=${NEO4J_PASSWORD},
    AWS_REGION=${AWS_REGION},
    DOCUMENTS_BUCKET=${DOCUMENTS_BUCKET},
    EMBEDDINGS_BUCKET=${EMBEDDINGS_BUCKET},
    KNOWLEDGE_BASE_TABLE=${KNOWLEDGE_BASE_TABLE},
    METADATA_TABLE=${METADATA_TABLE}
  }" \
  --region ap-south-1

# 6. Update Lambda handler configuration
echo "🔧 Updating Lambda handler configuration..."

# Update Chat Agent handler
aws lambda update-function-configuration \
  --function-name chatbot-chat-agent \
  --handler lambda_handlers.lambda_handler_knowledge_chat \
  --region ap-south-1

# Update Document Processing Agent handler
aws lambda update-function-configuration \
  --function-name chatbot-document-agent \
  --handler lambda_handlers.lambda_handler_knowledge_document_ingestion \
  --region ap-south-1

echo "✅ Chatbot Agents deployment completed successfully!"
echo ""
echo "🎉 Architecture: CRUD Tools + AI Intelligence"
echo "  🔧 CRUD Tools: Pure data operations only"
echo "  🧠 AI Model: All business logic and formatting"
echo "  📊 Lambda Functions: 2 (chat + document processing)"
echo ""
echo "🚀 Deployed Lambda Functions:"
echo "  💬 chatbot-chat-agent - Handles all chat interactions"
echo "  📄 chatbot-document-agent - Processes document uploads"
echo ""
echo "🔧 CRUD Tools Available:"
echo "  📁 S3: read_s3_data_tool"
echo "  🔍 Pinecone: search_pinecone_tool, upsert_pinecone_tool, delete_pinecone_tool"
echo "  🕸️ Neo4j: search_neo4j_tool, execute_neo4j_write_tool"
echo "  🗄️ DynamoDB: read_dynamodb_tool, batch_read_dynamodb_tool, write_dynamodb_tool, update_dynamodb_tool, delete_dynamodb_tool"
echo "  🧮 Embeddings: generate_embedding_tool"
echo ""
echo "🧠 AI Handles:"
echo "  ✅ Business logic and decision making"
echo "  ✅ Query understanding and intent analysis"
echo "  ✅ Data processing and synthesis"
echo "  ✅ Response generation and formatting"
echo "  ✅ Error handling and user guidance"
echo "  ✅ Multi-question processing"
echo "  ✅ Context awareness and conversation flow"
echo ""
echo "📋 Next steps:"
echo "1. Test the chat endpoint:"
echo "   curl -X POST 'https://your-api-gateway-url/chat' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"test query\"}'"
echo ""
echo "2. Upload a test document to S3:"
echo "   aws s3 cp test-document.pdf s3://${DOCUMENTS_BUCKET}/documents/"
echo ""
echo "3. Check CloudWatch logs for processing status"
echo ""
echo "🎯 Perfect separation: CRUD tools for data, AI for intelligence! 🧠✨"
