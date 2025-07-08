# Zamaz Debate System - Quick Start Guide

## 🚀 Getting Started in 3 Minutes

### 1. Initial Setup (One Time)
```bash
# Clone the repository
git clone https://github.com/lsendel/zamaz-debate.git
cd zamaz-debate

# Run setup
make setup

# Edit .env file and add your API keys
# - ANTHROPIC_API_KEY (for Claude)
# - GOOGLE_API_KEY (for Gemini)
```

### 2. Start the System
```bash
# Start the web interface
make run

# Open in browser
make web
```

### 3. Make Your First Decision
```bash
# Via command line
make test-decision

# Or visit http://localhost:8000 in your browser
```

## 📋 Common Commands

| Command | Description |
|---------|-------------|
| `make run` | Start the system |
| `make stop` | Stop the system |
| `make status` | Check system status |
| `make logs` | View live logs |
| `make debate` | Run a test debate |
| `make evolve` | Trigger self-improvement |
| `make help` | Show all commands |

## 🎯 Example Usage

### Ask a Technical Question
```bash
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Should we use TypeScript for our frontend?",
    "context": "Team has mixed JavaScript experience"
  }'
```

### Trigger Evolution
```bash
make evolve
```

## 🤖 How Delegation Works

The system automatically assigns implementation tasks:

- **Simple tasks** (rename, format, docs) → Gemini
- **Moderate tasks** (features, APIs, tests) → Gemini (if capable)
- **Complex tasks** (architecture, security) → Claude
- **Critical tasks** (auth, data models) → Human

## 🔧 Configuration

Edit `.env` to customize:

```env
# Enable PR creation
CREATE_PR_FOR_DECISIONS=true

# Auto-push to GitHub
AUTO_PUSH_PR=false

# Set GitHub usernames
GEMINI_GITHUB_USERNAME=gemini-bot
CLAUDE_GITHUB_USERNAME=claude
HUMAN_GITHUB_USERNAME=your-username
```

## 📊 Monitor Progress

```bash
# Check stats
make status

# View recent debates
ls -la debates/

# View PR drafts
make pr-drafts
```

## 🛠️ Development Mode

```bash
# Run with live logs
make dev

# Run tests
make test

# Format code
make format
```

## 🆘 Troubleshooting

If the system won't start:
1. Check API keys: `make check-env`
2. Check logs: `make logs`
3. Restart: `make stop && make run`

## 📚 Next Steps

1. Read the full documentation in `README.md`
2. Review architectural decisions in `TECHNICAL_ROADMAP.md`
3. Check implementation details in `CLAUDE.md`
4. Explore the web interface at http://localhost:8000

Happy debating! 🎉