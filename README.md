# KnowledgeBot Backend

Serverless chatbot backend with AI agents and CRUD operations.

## Quick Start

1. **Configure GitHub Secrets:**
   - `AWS_ACCESS_KEY_ID` - Your AWS Access Key ID
   - `AWS_SECRET_ACCESS_KEY` - Your AWS Secret Access Key
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `CLAUDE_API_KEY` - Your Anthropic Claude API key

2. **Deploy:**
   - Push to `main` branch triggers automatic deployment
   - Manual trigger available in GitHub Actions

## Architecture

- **Lambda Functions:** `chatbot-chat-agent`, `chatbot-document-agent`
- **Storage:** S3 + DynamoDB
- **AI:** OpenAI + Anthropic Claude
- **Deployment:** GitHub Actions + ECR
