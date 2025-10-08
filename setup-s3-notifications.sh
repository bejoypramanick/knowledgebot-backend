#!/bin/bash

# Setup S3 bucket notifications to trigger Lambda functions
set -e

REGION="ap-south-1"
ACCOUNT_ID="090163643302"
BUCKET_NAME="chatbot-storage-ap-south-1"
RAG_PROCESSOR_LAMBDA="chatbot-rag-processor"

echo "🔔 Setting up S3 bucket notifications for document processing..."

# Check if bucket exists
if ! aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION 2>/dev/null; then
    echo "❌ Bucket $BUCKET_NAME does not exist. Please run setup-aws-resources.sh first."
    exit 1
fi

# Check if RAG processor lambda exists
if ! aws lambda get-function --function-name $RAG_PROCESSOR_LAMBDA --region $REGION >/dev/null 2>&1; then
    echo "❌ Lambda function $RAG_PROCESSOR_LAMBDA does not exist. Please deploy the microservices first."
    exit 1
fi

# Get the Lambda function ARN
LAMBDA_ARN=$(aws lambda get-function --function-name $RAG_PROCESSOR_LAMBDA --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "📋 Lambda ARN: $LAMBDA_ARN"

# Add permission for S3 to invoke the Lambda function
echo "🔐 Adding S3 permission to invoke Lambda function..."
aws lambda add-permission \
    --function-name $RAG_PROCESSOR_LAMBDA \
    --statement-id s3-invoke-$(date +%s) \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn "arn:aws:s3:::$BUCKET_NAME" \
    --region $REGION || echo "Permission may already exist"

# Create S3 bucket notification configuration
echo "📝 Creating S3 bucket notification configuration..."
cat > s3-notification-config.json << EOF
{
    "LambdaFunctionConfigurations": [
        {
            "Id": "DocumentProcessingTrigger",
            "LambdaFunctionArn": "$LAMBDA_ARN",
            "Events": ["s3:ObjectCreated:Put"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "documents/"
                        }
                    ]
                }
            }
        }
    ]
}
EOF

# Apply the notification configuration
echo "🚀 Applying S3 bucket notification configuration..."
aws s3api put-bucket-notification-configuration \
    --bucket $BUCKET_NAME \
    --notification-configuration file://s3-notification-config.json \
    --region $REGION

# Verify the configuration
echo "✅ Verifying S3 bucket notification configuration..."
aws s3api get-bucket-notification-configuration --bucket $BUCKET_NAME --region $REGION

# Clean up
rm -f s3-notification-config.json

echo ""
echo "🎉 S3 bucket notifications configured successfully!"
echo ""
echo "📋 Configuration Summary:"
echo "  - Bucket: $BUCKET_NAME"
echo "  - Lambda: $RAG_PROCESSOR_LAMBDA"
echo "  - Trigger: s3:ObjectCreated:Put"
echo "  - Filter: documents/ prefix"
echo ""
echo "🧪 Test the setup:"
echo "  1. Upload a document to s3://$BUCKET_NAME/documents/"
echo "  2. Check CloudWatch logs for $RAG_PROCESSOR_LAMBDA"
echo "  3. Verify document appears in DynamoDB knowledge base"
