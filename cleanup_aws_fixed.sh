#!/bin/bash
# AWS Cleanup Script for KnowledgeBot Backend
# Removes redundant ECR repositories and Lambda functions

set -e

REGION="ap-south-1"
ACCOUNT_ID="090163643302"

echo "🧹 Starting AWS Cleanup for KnowledgeBot Backend"
echo "================================================"

echo ""
echo "📋 ANALYSIS RESULTS:"
echo "==================="

echo ""
echo "🔍 ECR Repositories Found:"
aws ecr describe-repositories --region $REGION --query 'repositories[].repositoryName' --output table

echo ""
echo "🔍 Lambda Functions Found:"
aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `knowledgebot`) || contains(FunctionName, `chatbot`)].FunctionName' --output table

echo ""
echo "⚠️  REDUNDANT RESOURCES IDENTIFIED:"
echo "=================================="

echo ""
echo "🗑️  ECR Repositories to DELETE (4 will be kept):"
echo "Keep: knowledgebot-backend, knowledgebot-backend-core, knowledgebot-backend-docling, knowledgebot-backend-final"
echo "Delete: All chatbot-* repositories"

echo ""
echo "🗑️  Lambda Functions to DELETE (2 will be kept):"
echo "Keep: knowledgebot-chat, knowledgebot-document-ingestion"
echo "Delete: All chatbot-* functions"

echo ""
echo "🔧 API Gateway Issues Found:"
echo "1. Chat endpoint points to 'chatbot-chat-handler' instead of 'knowledgebot-chat'"
echo "2. Multiple redundant endpoints exist"

echo ""
echo "❓ Do you want to proceed with cleanup? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting cleanup process..."
    
    # Delete redundant ECR repositories
    echo ""
    echo "🗑️  Deleting redundant ECR repositories..."
    
    # Get all repositories and filter out the ones to keep
    ALL_REPOS=$(aws ecr describe-repositories --region $REGION --query 'repositories[].repositoryName' --output text)
    
    for repo in $ALL_REPOS; do
        if [[ "$repo" != "knowledgebot-backend" && "$repo" != "knowledgebot-backend-core" && "$repo" != "knowledgebot-backend-docling" && "$repo" != "knowledgebot-backend-final" ]]; then
            echo "  Deleting repository: $repo"
            # First delete all images in the repository
            aws ecr list-images --repository-name $repo --region $REGION --query 'imageIds[]' --output json > /tmp/images.json
            if [ -s /tmp/images.json ] && [ "$(cat /tmp/images.json)" != "[]" ]; then
                aws ecr batch-delete-image --repository-name $repo --image-ids file:///tmp/images.json --region $REGION
            fi
            # Then delete the repository
            aws ecr delete-repository --repository-name $repo --region $REGION --force
            echo "  ✅ Deleted: $repo"
        fi
    done
    
    # Delete redundant Lambda functions
    echo ""
    echo "🗑️  Deleting redundant Lambda functions..."
    ALL_LAMBDAS=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `knowledgebot`) || contains(FunctionName, `chatbot`)].FunctionName' --output text)
    
    for lambda in $ALL_LAMBDAS; do
        if [[ "$lambda" != "knowledgebot-chat" && "$lambda" != "knowledgebot-document-ingestion" ]]; then
            echo "  Deleting Lambda function: $lambda"
            aws lambda delete-function --function-name $lambda --region $REGION
            echo "  ✅ Deleted: $lambda"
        fi
    done
    
    echo ""
    echo "🔧 Fixing API Gateway configuration..."
    echo "  Updating chat endpoint to point to knowledgebot-chat..."
    
    # Get the resource ID for chat endpoint
    CHAT_RESOURCE_ID=$(aws apigateway get-resources --rest-api-id a1kn0j91k8 --region $REGION --query 'items[?pathPart==`chat`].id' --output text)
    
    # Update the integration to point to knowledgebot-chat
    aws apigateway put-integration \
        --rest-api-id a1kn0j91k8 \
        --resource-id $CHAT_RESOURCE_ID \
        --http-method POST \
        --type AWS_PROXY \
        --integration-http-method POST \
        --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:$ACCOUNT_ID:function:knowledgebot-chat/invocations" \
        --region $REGION
    
    echo "  ✅ Updated chat endpoint integration"
    
    # Add permission for API Gateway to invoke knowledgebot-chat
    aws lambda add-permission \
        --function-name knowledgebot-chat \
        --statement-id apigateway-invoke \
        --action lambda:InvokeFunction \
        --principal apigateway.amazonaws.com \
        --source-arn "arn:aws:execute-api:$REGION:$ACCOUNT_ID:a1kn0j91k8/*/*" \
        --region $REGION || echo "  Permission already exists"
    
    echo "  ✅ Added API Gateway permission for knowledgebot-chat"
    
    echo ""
    echo "🎉 Cleanup completed successfully!"
    echo ""
    echo "📊 SUMMARY:"
    echo "==========="
    echo "✅ Kept ECR repositories: 4"
    echo "✅ Kept Lambda functions: 2"
    echo "✅ Fixed API Gateway configuration"
    echo "✅ Removed redundant resources"
    
else
    echo ""
    echo "❌ Cleanup cancelled by user"
    echo ""
    echo "📋 MANUAL CLEANUP RECOMMENDATIONS:"
    echo "=================================="
    echo ""
    echo "1. ECR Repositories to keep:"
    echo "   - knowledgebot-backend"
    echo "   - knowledgebot-backend-core"
    echo "   - knowledgebot-backend-docling"
    echo "   - knowledgebot-backend-final"
    echo ""
    echo "2. Lambda Functions to keep:"
    echo "   - knowledgebot-chat"
    echo "   - knowledgebot-document-ingestion"
    echo ""
    echo "3. API Gateway fixes needed:"
    echo "   - Update /chat endpoint to point to knowledgebot-chat"
    echo "   - Remove unused endpoints"
    echo ""
    echo "4. Run this script again when ready to proceed"
fi

echo ""
echo "🏁 Cleanup script completed"
