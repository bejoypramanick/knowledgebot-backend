#!/bin/bash

# Script to populate the knowledge_base_metadata table with existing documents from S3

REGION="ap-south-1"
BUCKET="chatbot-storage-ap-south-1"
TABLE="chatbot-knowledge-base-metadata"

echo "🚀 Populating metadata table with existing documents..."

# Function to add a document to the metadata table
add_document() {
    local s3_key="$1"
    local filename="$2"
    local content_type="$3"
    local file_size="$4"
    local last_modified="$5"
    
    # Generate a document ID (use the filename without extension as base)
    local base_name=$(echo "$filename" | sed 's/\.[^.]*$//')
    local document_id="$base_name"
    
    # Generate download URL (simplified - will be refreshed by the service)
    local download_url="https://${BUCKET}.s3.${REGION}.amazonaws.com/${s3_key}"
    
    echo "📄 Adding: $filename"
    
    # Create the item JSON
    local item_json=$(cat << EOF
{
    "document_id": {"S": "$document_id"},
    "original_filename": {"S": "$filename"},
    "s3_key": {"S": "$s3_key"},
    "s3_bucket": {"S": "$BUCKET"},
    "s3_download_url": {"S": "$download_url"},
    "content_type": {"S": "$content_type"},
    "status": {"S": "uploaded"},
    "uploaded_at": {"S": "$last_modified"},
    "metadata": {
        "M": {
            "title": {"S": "$base_name"},
            "category": {"S": "general"},
            "tags": {"L": []},
            "author": {"S": "unknown"}
        }
    },
    "file_size": {"N": "$file_size"},
    "chunks_count": {"N": "0"},
    "processed_at": {"NULL": true}
}
EOF
)
    
    # Add to DynamoDB
    aws dynamodb put-item \
        --table-name "$TABLE" \
        --item "$item_json" \
        --region "$REGION"
    
    if [ $? -eq 0 ]; then
        echo "✅ Successfully added: $filename"
    else
        echo "❌ Failed to add: $filename"
    fi
}

# Add each existing document
echo "📄 Adding 2f0fdb91-83ba-4802-8935-708803cc73b7.docx..."
add_document "documents/2f0fdb91-83ba-4802-8935-708803cc73b7.docx" "2f0fdb91-83ba-4802-8935-708803cc73b7.docx" "application/vnd.openxmlformats-officedocument.wordprocessingml.document" "11520" "2025-10-06T14:03:07.000Z"

echo "📄 Adding test-1759633998.md..."
add_document "documents/test-1759633998.md" "test-1759633998.md" "text/markdown" "472" "2025-10-05T05:13:20.000Z"

echo "📄 Adding test-1759634081.md..."
add_document "documents/test-1759634081.md" "test-1759634081.md" "text/markdown" "472" "2025-10-05T05:14:43.000Z"

echo "📄 Adding test-1759762892.txt..."
add_document "documents/test-1759762892.txt" "test-1759762892.txt" "text/plain" "290" "2025-10-06T17:01:34.000Z"

echo ""
echo "🎉 Metadata table population complete!"
echo "📋 You can now view these documents in the Knowledge Base Management screen!"
