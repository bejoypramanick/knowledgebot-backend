#!/bin/bash

# Add S3 notification permission to IAM policy
set -e

REGION="ap-south-1"
ACCOUNT_ID="090163643302"
POLICY_NAME="chatbot-lambda-custom-policy"

echo "🔐 Adding S3 notification permission to IAM policy..."

# Create updated policy with S3 notification permission
cat > s3-notification-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutLifecycleConfiguration",
                "s3:CreateBucket",
                "s3:DeleteBucket",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetBucketVersioning",
                "s3:PutBucketVersioning",
                "s3:PutBucketPublicAccessBlock",
                "s3:GetBucketPublicAccessBlock",
                "s3:GetBucketCORS",
                "s3:PutBucketCORS",
                "s3:PutBucketNotification",
                "s3:GetBucketNotification"
            ],
            "Resource": [
                "arn:aws:s3:::insurance-ai-rag-*",
                "arn:aws:s3:::insurance-ai-rag-*/*",
                "arn:aws:s3:::chatbot-*",
                "arn:aws:s3:::chatbot-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:CreateTable",
                "dynamodb:DeleteTable",
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:UpdateItem",
                "dynamodb:Query",
                "dynamodb:Scan",
                "dynamodb:DescribeTable",
                "dynamodb:ListTables",
                "dynamodb:UpdateTable",
                "dynamodb:TagResource",
                "dynamodb:UntagResource",
                "dynamodb:ListTagsOfResource",
                "dynamodb:UpdateTimeToLive",
                "dynamodb:DescribeTimeToLive"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/insurance-ai-rag-*",
                "arn:aws:dynamodb:*:*:table/chatbot-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:ListFunctions",
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:DeleteFunction",
                "lambda:InvokeFunction",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration",
                "lambda:AddPermission",
                "lambda:RemovePermission",
                "lambda:GetPolicy",
                "lambda:TagResource",
                "lambda:UntagResource",
                "lambda:ListTags",
                "lambda:PublishVersion",
                "lambda:CreateAlias",
                "lambda:UpdateAlias",
                "lambda:DeleteAlias",
                "lambda:GetAlias",
                "lambda:ListAliases",
                "lambda:GetLayerVersion",
                "lambda:ListLayerVersions",
                "lambda:ListLayers",
                "lambda:GetFunctionCodeSigningConfig",
                "lambda:PutFunctionCodeSigningConfig",
                "lambda:DeleteFunctionCodeSigningConfig",
                "lambda:GetCodeSigningConfig",
                "lambda:CreateCodeSigningConfig",
                "lambda:UpdateCodeSigningConfig",
                "lambda:DeleteCodeSigningConfig",
                "lambda:ListCodeSigningConfigs"
            ],
            "Resource": [
                "arn:aws:lambda:*:*:function:insurance-ai-rag-*",
                "arn:aws:lambda:*:*:function:chatbot-*",
                "arn:aws:lambda:*:*:function:simple-docling-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:CreateServiceLinkedRole",
                "iam:DeleteServiceLinkedRole",
                "iam:GetServiceLinkedRoleDeletionStatus"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "apigateway:POST",
                "apigateway:PUT",
                "apigateway:PATCH",
                "apigateway:DELETE",
                "apigateway:GET"
            ],
            "Resource": [
                "arn:aws:apigateway:*::/apis*",
                "arn:aws:apigateway:*::/restapis*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents",
                "logs:PutRetentionPolicy",
                "logs:DeleteLogGroup",
                "logs:DeleteLogStream",
                "logs:TagLogGroup",
                "logs:UntagLogGroup"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole",
                "iam:CreateRole",
                "iam:DeleteRole",
                "iam:GetRole",
                "iam:ListRoles",
                "iam:AttachRolePolicy",
                "iam:DetachRolePolicy",
                "iam:ListAttachedRolePolicies",
                "iam:PutRolePolicy",
                "iam:DeleteRolePolicy",
                "iam:GetRolePolicy",
                "iam:ListRolePolicies",
                "iam:TagRole",
                "iam:UntagRole"
            ],
            "Resource": [
                "arn:aws:iam::*:role/insurance-ai-rag-*",
                "arn:aws:iam::*:role/chatbot-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sts:GetCallerIdentity",
                "sts:AssumeRole"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken",
                "ecr:CreateRepository",
                "ecr:DeleteRepository",
                "ecr:DescribeRepositories",
                "ecr:GetRepositoryPolicy",
                "ecr:SetRepositoryPolicy",
                "ecr:DeleteRepositoryPolicy",
                "ecr:GetLifecyclePolicy",
                "ecr:PutLifecyclePolicy",
                "ecr:DeleteLifecyclePolicy",
                "ecr:GetLifecyclePolicyPreview",
                "ecr:StartLifecyclePolicyPreview",
                "ecr:PutImage",
                "ecr:DescribeImages",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:GetDownloadUrlForLayer",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload",
                "ecr:PutImageScanningConfiguration",
                "ecr:StartImageScan",
                "ecr:DescribeImageScanFindings",
                "ecr:BatchDeleteImage",
                "ecr:TagResource",
                "ecr:UntagResource",
                "ecr:ListTagsForResource"
            ],
            "Resource": [
                "arn:aws:ecr:*:*:repository/chatbot-*",
                "arn:aws:ecr:*:*:repository/insurance-ai-rag-*"
            ]
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
        },
        {
            "Effect": "Allow",
            "Action": [
                "lambda:CreateFunction",
                "lambda:UpdateFunctionCode",
                "lambda:UpdateFunctionConfiguration",
                "lambda:GetFunction",
                "lambda:GetFunctionConfiguration"
            ],
            "Resource": [
                "arn:aws:lambda:*:*:function:insurance-ai-rag-*",
                "arn:aws:lambda:*:*:function:chatbot-*",
                "arn:aws:lambda:*:*:function:simple-docling-*"
            ]
        }
    ]
}
EOF

# Create and attach S3 notification policy
aws iam create-policy \
    --policy-name chatbot-s3-notification-policy \
    --policy-document file://s3-notification-policy.json \
    --region $REGION || echo "Policy already exists"

aws iam attach-role-policy \
    --role-name chatbot-lambda-role \
    --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/chatbot-s3-notification-policy \
    --region $REGION || echo "Policy already attached"

# Clean up temporary file
rm -f s3-notification-policy.json

echo "✅ S3 notification permission added successfully!"
