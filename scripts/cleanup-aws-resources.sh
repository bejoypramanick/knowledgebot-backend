#!/bin/bash

# Cleanup AWS Resources Script
# This script removes redundant AWS resources that are no longer needed

set -e

AWS_REGION=${AWS_REGION:-ap-south-1}

echo "🧹 Starting cleanup of redundant AWS resources..."

# Function to delete Lambda functions
delete_lambda_functions() {
    echo "🗑️  Deleting redundant Lambda functions..."
    
    REDUNDANT_FUNCTIONS=(
        "openai-agents-handler"
        "dynamodb-mcp-handler"
        "chat-orchestrator-websocket"
        "document-processor-business-logic"
        "s3-unified-handler"
        "error-logger-handler"
        "error-query-handler"
        "docling-library-handler"
        "pinecone-library-handler"
        "neo4j-library-handler"
        "dynamodb-crud-handler"
        "neo4j-mcp-server"
    )
    
    for function_name in "${REDUNDANT_FUNCTIONS[@]}"; do
        echo "  Deleting Lambda function: $function_name"
        aws lambda delete-function \
            --function-name "$function_name" \
            --region "$AWS_REGION" 2>/dev/null || echo "    Function $function_name not found or already deleted"
    done
}

# Function to delete DynamoDB tables
delete_dynamodb_tables() {
    echo "🗑️  Deleting redundant DynamoDB tables..."
    
    REDUNDANT_TABLES=(
        "document-chunks-staging"
        "document-chunks-production"
        "knowledgebot-error-logs-staging"
        "knowledgebot-error-logs-production"
    )
    
    for table_name in "${REDUNDANT_TABLES[@]}"; do
        echo "  Deleting DynamoDB table: $table_name"
        aws dynamodb delete-table \
            --table-name "$table_name" \
            --region "$AWS_REGION" 2>/dev/null || echo "    Table $table_name not found or already deleted"
    done
}

# Function to delete S3 buckets
delete_s3_buckets() {
    echo "🗑️  Deleting redundant S3 buckets..."
    
    REDUNDANT_BUCKETS=(
        "knowledgebot-documents-staging"
        "knowledgebot-documents-production"
        "processed-documents-staging"
        "processed-documents-production"
        "knowledgebot-error-logs-staging"
        "knowledgebot-error-logs-production"
    )
    
    for bucket_name in "${REDUNDANT_BUCKETS[@]}"; do
        echo "  Deleting S3 bucket: $bucket_name"
        # First, empty the bucket
        aws s3 rm "s3://$bucket_name" --recursive 2>/dev/null || echo "    Bucket $bucket_name is empty or doesn't exist"
        # Then delete the bucket
        aws s3 rb "s3://$bucket_name" --region "$AWS_REGION" 2>/dev/null || echo "    Bucket $bucket_name not found or already deleted"
    done
}

# Function to delete IAM roles
delete_iam_roles() {
    echo "🗑️  Deleting redundant IAM roles..."
    
    REDUNDANT_ROLES=(
        "lambda-execution-role"
    )
    
    for role_name in "${REDUNDANT_ROLES[@]}"; do
        echo "  Deleting IAM role: $role_name"
        # First, detach all policies
        aws iam list-attached-role-policies --role-name "$role_name" --query 'AttachedPolicies[].PolicyArn' --output text 2>/dev/null | \
        xargs -I {} aws iam detach-role-policy --role-name "$role_name" --policy-arn {} 2>/dev/null || echo "    No policies attached to $role_name"
        # Then delete the role
        aws iam delete-role --role-name "$role_name" 2>/dev/null || echo "    Role $role_name not found or already deleted"
    done
}

# Function to list remaining MCP servers
list_mcp_servers() {
    echo "✅ Remaining MCP servers:"
    
    MCP_SERVERS=(
        "docling-mcp-server"
        "pinecone-mcp-server"
        "dynamodb-mcp-server"
        "neo4j-cypher-mcp-server"
        "neo4j-modeling-mcp-server"
    )
    
    for function_name in "${MCP_SERVERS[@]}"; do
        if aws lambda get-function --function-name "$function_name" --region "$AWS_REGION" >/dev/null 2>&1; then
            echo "  ✅ $function_name"
        else
            echo "  ❌ $function_name (not found)"
        fi
    done
}

# Main execution
main() {
    echo "🚀 AWS Resource Cleanup Script"
    echo "Region: $AWS_REGION"
    echo ""
    
    # Check if AWS CLI is configured
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "❌ AWS CLI not configured. Please run 'aws configure' first."
        exit 1
    fi
    
    # Confirm before proceeding
    read -p "⚠️  This will delete redundant AWS resources. Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cleanup cancelled."
        exit 0
    fi
    
    # Execute cleanup functions
    delete_lambda_functions
    echo ""
    delete_dynamodb_tables
    echo ""
    delete_s3_buckets
    echo ""
    delete_iam_roles
    echo ""
    
    # List remaining MCP servers
    list_mcp_servers
    echo ""
    
    echo "🎉 Cleanup completed!"
    echo ""
    echo "Remaining resources:"
    echo "- 5 MCP server Lambda functions"
    echo "- ECR repositories for MCP server images"
    echo "- IAM role: mcp-lambda-execution-role"
    echo ""
    echo "All redundant resources have been removed."
}

# Run main function
main "$@"
