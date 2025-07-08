# Zamaz Debate System

A self-improving AI debate system that uses Claude Opus 4 and Gemini 2.5 Pro to make architectural decisions through structured debates.

## 🎯 Core Concept

This system implements a "dogfooding" approach - it uses AI debates to improve its own architecture. Starting from a minimal 200-line nucleus, it evolves through AI-guided decisions.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- API Keys for:
    - Anthropic Claude (for Claude Opus 4)
    - Google AI (for Gemini 2.5 Pro)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/lsendel/zamaz-debate.git
cd zamaz-debate

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your API keys
cp .env.example .env
# Edit .env with your actual API keys

# Run the system
python nucleus.py
```

## 🧬 Evolution Process

The system evolves through:

1. **Self-Analysis**: The nucleus can read its own code
2. **AI Debates**: Claude and Gemini debate improvements
3. **Implementation**: Agreed changes are implemented
4. **Versioning**: Each evolution is tracked

## 📁 Project Structure

```
zamaz-debate/
├── nucleus.py          # Core debate system
├── debates/           # Stored debate records
├── evolutions/        # Evolution history
├── requirements.txt   # Python dependencies
├── .env.example      # API key template
└── README.md         # This file
```

## 🔑 Environment Variables

Create a `.env` file with:

```
ANTHROPIC_API_KEY=your-anthropic-api-key
GOOGLE_API_KEY=your-google-api-key
```

## 🧪 Testing

Run the built-in tests:

```bash
python nucleus.py
```

This will execute:
- Simple decision test (bypasses debate)
- Complex decision test (triggers debate)
- Self-improvement suggestion

## 📝 License

MIT License - See LICENSE file for details.
