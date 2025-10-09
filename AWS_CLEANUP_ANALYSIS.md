# 🧹 AWS Cleanup Analysis & Recommendations

## 📊 Current State Analysis

### 🔍 **ECR Repositories (28 total)**
**KEEP (4 repositories):**
- ✅ `knowledgebot-backend` - Main repository
- ✅ `knowledgebot-backend-core` - Core dependencies  
- ✅ `knowledgebot-backend-docling` - Document processing
- ✅ `knowledgebot-backend-final` - Complete application

**DELETE (24 redundant repositories):**
- ❌ `chatbot-chat-handler` - Old chat handler
- ❌ `chatbot-rag-search` - Redundant RAG search
- ❌ `chatbot-claude-decision` - Old decision logic
- ❌ `chatbot-base-docling-core` - Old base image
- ❌ `chatbot-orchestrator` - Old orchestrator
- ❌ `chatbot-document-management` - Old document management
- ❌ `chatbot-response-enhancement` - Old response enhancement
- ❌ `chatbot-embedding-service` - Old embedding service
- ❌ `chatbot-document-metadata` - Old metadata service
- ❌ `chatbot-response-formatter` - Old formatter
- ❌ `chatbot-base-docling` - Old base image
- ❌ `chatbot-action-executor` - Old action executor
- ❌ `chatbot-vector-search` - Old vector search
- ❌ `chatbot-source-extractor` - Old source extractor
- ❌ `chatbot-conversation-manager` - Old conversation manager
- ❌ `chatbot-presigned-url` - Old presigned URL service
- ❌ `chatbot-base-combined` - Old combined base
- ❌ `chatbot-base-docling-ocr` - Old OCR base
- ❌ `chatbot-base-embeddings-light` - Old embeddings base
- ❌ `chatbot-rag-processor` - Old RAG processor
- ❌ `chatbot-document-content` - Old document content
- ❌ `chatbot-base-sentence-transformers` - Old transformers base
- ❌ `chatbot-base-docling-tables` - Old tables base

### 🔍 **Lambda Functions (20 total)**
**KEEP (2 functions):**
- ✅ `knowledgebot-chat` - Current chat handler
- ✅ `knowledgebot-document-ingestion` - Current document processing

**DELETE (18 redundant functions):**
- ❌ `chatbot-document-content` - Old document content
- ❌ `chatbot-response-enhancement` - Old response enhancement
- ❌ `chatbot-action-executor` - Old action executor
- ❌ `chatbot-rag-processor` - Old RAG processor
- ❌ `chatbot-rag-search` - Old RAG search
- ❌ `chatbot-document-management` - Old document management
- ❌ `chatbot-claude-decision` - Old decision logic
- ❌ `chatbot-response-formatter` - Old formatter
- ❌ `chatbot-vector-search` - Old vector search
- ❌ `chatbot-presigned-url` - Old presigned URL
- ❌ `chatbot-source-extractor` - Old source extractor
- ❌ `chatbot-retrieval-agent` - Old retrieval agent
- ❌ `chatbot-conversation-manager` - Old conversation manager
- ❌ `chatbot-document-ingestion-agent` - Old ingestion agent
- ❌ `chatbot-embedding-service` - Old embedding service
- ❌ `chatbot-document-metadata` - Old metadata service
- ❌ `chatbot-orchestrator` - Old orchestrator
- ❌ `chatbot-chat-handler` - Old chat handler

### 🔍 **API Gateway Configuration Issues**
**Current State:**
- ❌ `/chat` endpoint → `chatbot-chat-handler` (WRONG)
- ❌ `/knowledge-base` endpoint → (unknown)
- ❌ `/orders` endpoint → (unknown)

**Required Fixes:**
- ✅ `/chat` endpoint → `knowledgebot-chat` (CORRECT)
- ✅ Remove unused endpoints
- ✅ Update permissions

## 🚀 Cleanup Actions Required

### 1. **ECR Repository Cleanup**
```bash
# Delete 24 redundant repositories
# Keep only: knowledgebot-backend, knowledgebot-backend-core, 
#           knowledgebot-backend-docling, knowledgebot-backend-final
```

### 2. **Lambda Function Cleanup**
```bash
# Delete 18 redundant functions
# Keep only: knowledgebot-chat, knowledgebot-document-ingestion
```

### 3. **API Gateway Fixes**
```bash
# Update /chat endpoint to point to knowledgebot-chat
# Remove unused endpoints (/knowledge-base, /orders)
# Add proper permissions
```

## 💰 Cost Savings Estimate

### **ECR Storage Costs:**
- **Before**: 28 repositories × ~500MB each = ~14GB storage
- **After**: 4 repositories × ~500MB each = ~2GB storage
- **Savings**: ~12GB storage reduction

### **Lambda Function Costs:**
- **Before**: 20 functions × ~$0.20/month = ~$4/month
- **After**: 2 functions × ~$0.20/month = ~$0.40/month  
- **Savings**: ~$3.60/month

### **Total Monthly Savings:**
- **Storage**: ~$0.12/month (ECR)
- **Compute**: ~$3.60/month (Lambda)
- **Total**: ~$3.72/month

## 🛠️ How to Execute Cleanup

### **Option 1: Automated Cleanup**
```bash
# Run the cleanup script
./cleanup_aws.sh
```

### **Option 2: Manual Cleanup**
```bash
# Delete redundant ECR repositories
aws ecr delete-repository --repository-name chatbot-chat-handler --region ap-south-1 --force
# ... (repeat for all 24 redundant repositories)

# Delete redundant Lambda functions  
aws lambda delete-function --function-name chatbot-chat-handler --region ap-south-1
# ... (repeat for all 18 redundant functions)

# Fix API Gateway
aws apigateway put-integration --rest-api-id a1kn0j91k8 --resource-id 57wl90 --http-method POST --type AWS_PROXY --integration-http-method POST --uri "arn:aws:apigateway:ap-south-1:lambda:path/2015-03-31/functions/arn:aws:lambda:ap-south-1:090163643302:function:knowledgebot-chat/invocations" --region ap-south-1
```

## ⚠️ Important Notes

1. **Backup First**: Ensure you have backups of any important data
2. **Test After**: Verify that `knowledgebot-chat` and `knowledgebot-document-ingestion` work correctly
3. **Monitor**: Watch for any errors after cleanup
4. **Gradual**: Consider deleting resources gradually to avoid service disruption

## 🎯 Expected Outcome

After cleanup:
- ✅ **4 ECR repositories** (down from 28)
- ✅ **2 Lambda functions** (down from 20)  
- ✅ **Correct API Gateway configuration**
- ✅ **~$3.72/month cost savings**
- ✅ **Cleaner, more maintainable infrastructure**

---

**© 2024 Bejoy Pramanick. All rights reserved.**
