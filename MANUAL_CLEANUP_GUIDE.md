# 🧹 AWS Cleanup Manual Guide

## ⚠️ **Permission Issue Detected**

The current AWS user (`aws_mcp_api_user`) has limited permissions and cannot perform ECR and Lambda deletion operations.

## 📋 **Manual Cleanup Required**

### **Step 1: ECR Repository Cleanup (24 repositories to delete)**

**Keep these 4 repositories:**
- ✅ `knowledgebot-backend`
- ✅ `knowledgebot-backend-core`
- ✅ `knowledgebot-backend-docling`
- ✅ `knowledgebot-backend-final`

**Delete these 24 repositories:**
```bash
# Run these commands with admin permissions
aws ecr delete-repository --repository-name chatbot-chat-handler --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-rag-search --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-claude-decision --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-docling-core --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-orchestrator --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-document-management --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-response-enhancement --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-embedding-service --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-document-metadata --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-response-formatter --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-docling --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-action-executor --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-vector-search --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-source-extractor --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-conversation-manager --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-presigned-url --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-combined --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-docling-ocr --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-embeddings-light --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-rag-processor --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-document-content --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-sentence-transformers --region ap-south-1 --force
aws ecr delete-repository --repository-name chatbot-base-docling-tables --region ap-south-1 --force
```

### **Step 2: Lambda Function Cleanup (18 functions to delete)**

**Keep these 2 functions:**
- ✅ `knowledgebot-chat`
- ✅ `knowledgebot-document-ingestion`

**Delete these 18 functions:**
```bash
# Run these commands with admin permissions
aws lambda delete-function --function-name chatbot-document-content --region ap-south-1
aws lambda delete-function --function-name chatbot-response-enhancement --region ap-south-1
aws lambda delete-function --function-name chatbot-action-executor --region ap-south-1
aws lambda delete-function --function-name chatbot-rag-processor --region ap-south-1
aws lambda delete-function --function-name chatbot-rag-search --region ap-south-1
aws lambda delete-function --function-name chatbot-document-management --region ap-south-1
aws lambda delete-function --function-name chatbot-claude-decision --region ap-south-1
aws lambda delete-function --function-name chatbot-response-formatter --region ap-south-1
aws lambda delete-function --function-name chatbot-vector-search --region ap-south-1
aws lambda delete-function --function-name chatbot-presigned-url --region ap-south-1
aws lambda delete-function --function-name chatbot-source-extractor --region ap-south-1
aws lambda delete-function --function-name chatbot-retrieval-agent --region ap-south-1
aws lambda delete-function --function-name chatbot-conversation-manager --region ap-south-1
aws lambda delete-function --function-name chatbot-document-ingestion-agent --region ap-south-1
aws lambda delete-function --function-name chatbot-embedding-service --region ap-south-1
aws lambda delete-function --function-name chatbot-document-metadata --region ap-south-1
aws lambda delete-function --function-name chatbot-orchestrator --region ap-south-1
aws lambda delete-function --function-name chatbot-chat-handler --region ap-south-1
```

### **Step 3: API Gateway Configuration Fix**

**Current Issue:**
- `/chat` endpoint points to `chatbot-chat-handler` (WRONG)
- Should point to `knowledgebot-chat` (CORRECT)

**Fix Commands:**
```bash
# Update chat endpoint to point to knowledgebot-chat
aws apigateway put-integration \
    --rest-api-id a1kn0j91k8 \
    --resource-id 57wl90 \
    --http-method POST \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:ap-south-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-south-1:090163643302:function:knowledgebot-chat/invocations" \
    --region ap-south-1

# Add permission for API Gateway to invoke knowledgebot-chat
aws lambda add-permission \
    --function-name knowledgebot-chat \
    --statement-id apigateway-invoke \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:ap-south-1:090163643302:a1kn0j91k8/*/*" \
    --region ap-south-1
```

## 🎯 **Expected Results After Cleanup**

### **Before Cleanup:**
- 28 ECR repositories
- 20 Lambda functions
- API Gateway pointing to wrong Lambda

### **After Cleanup:**
- 4 ECR repositories (85% reduction)
- 2 Lambda functions (90% reduction)
- API Gateway correctly configured
- ~$3.72/month cost savings

## 🔧 **Automated Script for Admin User**

If you have admin permissions, you can run this script:

```bash
#!/bin/bash
# Run with admin permissions

REGION="ap-south-1"

echo "🧹 Starting AWS Cleanup with Admin Permissions"

# Delete ECR repositories
echo "🗑️  Deleting ECR repositories..."
for repo in chatbot-chat-handler chatbot-rag-search chatbot-claude-decision chatbot-base-docling-core chatbot-orchestrator chatbot-document-management chatbot-response-enhancement chatbot-embedding-service chatbot-document-metadata chatbot-response-formatter chatbot-base-docling chatbot-action-executor chatbot-vector-search chatbot-source-extractor chatbot-conversation-manager chatbot-presigned-url chatbot-base-combined chatbot-base-docling-ocr chatbot-base-embeddings-light chatbot-rag-processor chatbot-document-content chatbot-base-sentence-transformers chatbot-base-docling-tables; do
    echo "  Deleting: $repo"
    aws ecr delete-repository --repository-name $repo --region $REGION --force
done

# Delete Lambda functions
echo "🗑️  Deleting Lambda functions..."
for func in chatbot-document-content chatbot-response-enhancement chatbot-action-executor chatbot-rag-processor chatbot-rag-search chatbot-document-management chatbot-claude-decision chatbot-response-formatter chatbot-vector-search chatbot-presigned-url chatbot-source-extractor chatbot-retrieval-agent chatbot-conversation-manager chatbot-document-ingestion-agent chatbot-embedding-service chatbot-document-metadata chatbot-orchestrator chatbot-chat-handler; do
    echo "  Deleting: $func"
    aws lambda delete-function --function-name $func --region $REGION
done

echo "🎉 Cleanup completed!"
```

## ⚠️ **Important Notes**

1. **Backup First**: Ensure you have backups of any important data
2. **Test After**: Verify that `knowledgebot-chat` and `knowledgebot-document-ingestion` work correctly
3. **Monitor**: Watch for any errors after cleanup
4. **Gradual**: Consider deleting resources gradually to avoid service disruption

---

**© 2024 Bejoy Pramanick. All rights reserved.**
