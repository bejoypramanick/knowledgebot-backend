#!/bin/bash

# Setup AWS Resources for RAG Chatbot
set -e

REGION="ap-south-1"
ACCOUNT_ID="090163643302"

echo "🚀 Setting up AWS resources for RAG Chatbot..."

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Create S3 bucket
echo "📦 Creating S3 bucket..."

# Main storage bucket
aws s3 mb s3://chatbot-storage-ap-south-1 --region $REGION || echo "Bucket already exists"

# Set CORS policy for main bucket
aws s3api put-bucket-cors \
    --bucket chatbot-storage-ap-south-1 \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                "AllowedOrigins": [
                    "http://localhost:3000",
                    "http://localhost:5173", 
                    "http://localhost:8081"
                ],
                "ExposeHeaders": [
                    "x-amz-meta-author",
                    "x-amz-meta-category", 
                    "x-amz-meta-tags",
                    "x-amz-meta-document_id",
                    "x-amz-meta-original_filename",
                    "x-amz-meta-title",
                    "x-amz-meta-upload_timestamp"
                ],
                "MaxAgeSeconds": 3600
            }
        ]
    }' \
    --region $REGION

# Create DynamoDB tables
echo "🗄️ Creating DynamoDB tables..."

# Knowledge Base table
aws dynamodb create-table \
    --table-name chatbot-knowledge-base \
    --attribute-definitions \
        AttributeName=chunk_id,AttributeType=S \
        AttributeName=document_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --key-schema \
        AttributeName=chunk_id,KeyType=HASH \
    --global-secondary-indexes \
        IndexName=DocumentIdIndex,KeySchema='[{AttributeName=document_id,KeyType=HASH},{AttributeName=created_at,KeyType=RANGE}]',Projection='{ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION || echo "Table already exists"

# Conversations table
aws dynamodb create-table \
    --table-name chatbot-conversations \
    --attribute-definitions \
        AttributeName=conversation_id,AttributeType=S \
        AttributeName=message_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=conversation_id,KeyType=HASH \
        AttributeName=message_id,KeyType=RANGE \
    --global-secondary-indexes \
        IndexName=TimestampIndex,KeySchema='[{AttributeName=conversation_id,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}]',Projection='{ProjectionType=ALL}' \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION || echo "Table already exists"

# Create IAM role for Lambda functions
echo "🔐 Creating IAM role for Lambda functions..."

# Create trust policy
cat > lambda-trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create role
aws iam create-role \
    --role-name chatbot-lambda-role \
    --assume-role-policy-document file://lambda-trust-policy.json \
    --region $REGION || echo "Role already exists"

# Attach basic execution policy
aws iam attach-role-policy \
    --role-name chatbot-lambda-role \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
    --region $REGION || echo "Policy already attached"

# Create custom policy for S3 and DynamoDB access
cat > lambda-custom-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:HeadObject"
            ],
            "Resource": [
                "arn:aws:s3:::chatbot-documents-ap-south-1",
                "arn:aws:s3:::chatbot-documents-ap-south-1/*",
                "arn:aws:s3:::chatbot-embeddings-ap-south-1",
                "arn:aws:s3:::chatbot-embeddings-ap-south-1/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/chatbot-knowledge-base",
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/chatbot-conversations"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:InvokeFunction"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create and attach custom policy
aws iam create-policy \
    --policy-name chatbot-lambda-custom-policy \
    --policy-document file://lambda-custom-policy.json \
    --region $REGION || echo "Policy already exists"

aws iam attach-role-policy \
    --role-name chatbot-lambda-role \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/chatbot-lambda-custom-policy \
    --region $REGION || echo "Policy already attached"

# Create ECR repositories
echo "🐳 Creating ECR repositories..."

aws ecr create-repository \
    --repository-name chatbot-rag-processor \
    --region $REGION || echo "Repository already exists"

aws ecr create-repository \
    --repository-name chatbot-chat-handler \
    --region $REGION || echo "Repository already exists"

# Clean up temporary files
rm -f lambda-trust-policy.json lambda-custom-policy.json

echo "✅ AWS resources setup completed!"
echo ""
echo "📋 Created resources:"
echo "  - S3 Buckets: chatbot-documents-ap-south-1, chatbot-embeddings-ap-south-1"
echo "  - DynamoDB Tables: chatbot-knowledge-base, chatbot-conversations"
echo "  - IAM Role: chatbot-lambda-role"
echo "  - ECR Repositories: chatbot-rag-processor, chatbot-chat-handler"
echo ""
echo "Next steps:"
echo "1. Push your code to GitHub to trigger the Lambda container deployment"
echo "2. Update your frontend to use the new API endpoints"
echo "3. Test document upload and chat functionality"
