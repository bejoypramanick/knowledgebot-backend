# Configuration Setup

## Claude API Key Configuration

To use the chatbot with Claude AI, you need to:

1. **Get your Claude API key** from [Anthropic Console](https://console.anthropic.com/)

2. **Update the config file**:
   - Open `backend/config.py`
   - Replace `"sk-ant-api03-your-actual-claude-api-key-here"` with your actual API key
   - Save the file

3. **Deploy the updated Lambda functions**:
   ```bash
   cd backend
   ./deploy-lambda.sh
   ```

## Configuration Values

The `config.py` file contains:

- **CLAUDE_API_KEY**: Your Anthropic Claude API key
- **AWS_REGION**: AWS region (currently set to ap-south-1)
- **KNOWLEDGE_BASE_TABLE**: DynamoDB table for knowledge base
- **CONVERSATIONS_TABLE**: DynamoDB table for conversation history
- **DOCUMENTS_BUCKET**: S3 bucket for document storage
- **EMBEDDINGS_BUCKET**: S3 bucket for vector embeddings

## Security Note

⚠️ **Important**: The config file contains your API key in plain text. For production use, consider:
- Using AWS Systems Manager Parameter Store
- Using AWS Secrets Manager
- Using environment variables
- Using IAM roles with appropriate permissions

## Testing

After updating the config and deploying:

1. Test the chatbot in your frontend
2. Check CloudWatch logs for any errors
3. Verify that responses are coming from Claude AI (not generic responses)
