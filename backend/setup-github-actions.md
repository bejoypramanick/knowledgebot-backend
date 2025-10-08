# GitHub Actions Setup for Lambda Container

## Prerequisites

1. **GitHub Repository**: Push your code to a GitHub repository
2. **AWS Credentials**: You'll need AWS access keys with the permissions we set up

## Setup Steps

### 1. Create GitHub Repository
```bash
git init
git add .
git commit -m "Initial commit with Lambda container setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. Add GitHub Secrets
Go to your GitHub repository → Settings → Secrets and variables → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`: Your AWS access key ID
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key

### 3. Update the Workflow (if needed)
The workflow is configured for:
- **AWS Region**: `ap-south-1`
- **ECR Repository**: `chatbot-lambda`
- **Lambda Function**: `chatbot-container`
- **IAM Role**: `arn:aws:iam::090163643302:role/chatbot-lambda-role`

If any of these need to be changed, edit `.github/workflows/build-lambda-container.yml`

### 4. Trigger the Build
The workflow will automatically run when you push to the `main` branch, or you can trigger it manually:

1. Go to Actions tab in your GitHub repository
2. Click "Build and Deploy Lambda Container"
3. Click "Run workflow"

## What the Workflow Does

1. **Builds Docker Image**: Creates a Linux x86_64 compatible image with Pydantic
2. **Pushes to ECR**: Uploads the image to your ECR repository
3. **Creates/Updates Lambda**: Deploys the container as a Lambda function
4. **Sets Permissions**: Adds API Gateway invoke permissions

## Monitoring

- Check the Actions tab for build progress
- Check AWS Lambda console for the deployed function
- Check CloudWatch logs for any runtime issues

## Testing

Once deployed, test the function:
```bash
curl -X POST https://a1kn0j91k8.execute-api.ap-south-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What documents do you have?", "session_id": "test-123", "user_id": "test-user"}'
```
