# GitHub App Integration for Zamaz

This directory contains the GitHub App integration that allows Claude to automatically respond to GitHub events.

## 🚀 Quick Setup

### 1. Create a GitHub App

1. Go to GitHub Settings > Developer settings > GitHub Apps > New GitHub App
2. Fill in the following:
   - **App name**: Zamaz AI Assistant
   - **Homepage URL**: https://github.com/lsendel/zamaz-debate
   - **Webhook URL**: Your server URL + `/webhooks/github` (e.g., `https://your-domain.com/webhooks/github`)
   - **Webhook secret**: Generate a secure random string
   - **Permissions**: 
     - Issues: Read & Write
     - Pull requests: Read & Write
     - Contents: Read & Write
     - Actions: Write
   - **Subscribe to events**:
     - Issues
     - Issue comments
     - Pull requests
     - Pull request reviews
     - Pull request review comments

3. Click "Create GitHub App"

### 2. Configure the App

After creation:
1. Note down the **App ID**
2. Generate a **Private Key** (will download a .pem file)
3. Install the app on your repository

### 3. Set Environment Variables

Create a `.env` file in the github-app directory:

```bash
# GitHub App Configuration
GITHUB_APP_ID=your_app_id
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
your_private_key_content
-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# Claude API (for AI processing)
ANTHROPIC_API_KEY=your_claude_api_key

# Server Configuration
WEBHOOK_SERVER_URL=http://localhost:8080
```

### 4. Install Dependencies

```bash
cd github-app
pip install -r requirements.txt
```

### 5. Run the Services

In separate terminals:

**Terminal 1 - Webhook Server:**
```bash
python webhook_server.py
```

**Terminal 2 - Task Processor:**
```bash
python task_processor.py
```

## 🧪 Testing the Integration

### Create a Test Issue

```bash
gh issue create \
  --title "Test: Implement a simple greeting function" \
  --body "Please implement a function that takes a name and returns a greeting message." \
  --label "ai-assigned"
```

### Expected Behavior

1. GitHub sends webhook to your server
2. Server queues the task
3. Task processor picks it up
4. Creates implementation branch
5. Generates code
6. Creates pull request
7. Comments on original issue

## 📋 How It Works

1. **Webhook Server** (`webhook_server.py`):
   - Receives GitHub webhooks
   - Verifies signatures for security
   - Queues tasks for processing

2. **Task Processor** (`task_processor.py`):
   - Polls for pending tasks
   - Uses Claude API to generate implementations
   - Creates branches and PRs
   - Updates issues with progress

## 🔒 Security Best Practices

1. **Always verify webhook signatures**
2. **Use environment variables for secrets**
3. **Implement rate limiting**
4. **Log all activities**
5. **Use HTTPS for webhook endpoint**

## 🚀 Deployment Options

### Option 1: Heroku
- Add `Procfile`
- Configure environment variables
- Deploy with Git

### Option 2: AWS Lambda
- Use API Gateway for webhook endpoint
- Store tasks in DynamoDB
- Process with Lambda functions

### Option 3: Google Cloud Run
- Containerize the application
- Deploy to Cloud Run
- Use Cloud Tasks for queue

## 🛠️ Troubleshooting

### Webhook not received
- Check webhook URL in GitHub App settings
- Verify server is accessible from internet
- Check webhook deliveries in GitHub

### Task not processed
- Check environment variables
- Verify GitHub App installation
- Check logs for errors

### Authentication errors
- Regenerate private key
- Verify App ID
- Check installation permissions