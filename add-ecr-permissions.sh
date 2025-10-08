#!/bin/bash

# Add ECR permissions to Lambda role
set -e

REGION="ap-south-1"
ACCOUNT_ID="090163643302"
ROLE_NAME="chatbot-lambda-role"

echo "🔐 Adding ECR permissions to Lambda role..."

# Create ECR policy
cat > ecr-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
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

# Create and attach ECR policy
aws iam create-policy \
    --policy-name chatbot-lambda-ecr-policy \
    --policy-document file://ecr-policy.json \
    --region $REGION || echo "Policy already exists"

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/chatbot-lambda-ecr-policy \
    --region $REGION || echo "Policy already attached"

# Clean up temporary file
rm -f ecr-policy.json

echo "✅ ECR permissions added to Lambda role successfully!"
