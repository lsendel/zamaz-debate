# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the Zamaz Debate System - a self-improving AI debate framework that uses Claude Opus 4 and Gemini 2.5 Pro to make architectural decisions through structured debates. The system follows a "dogfooding" approach where it uses AI debates to improve its own architecture.

## Build and Development Commands

### Initial Setup
```bash
# Execute the bootstrap script to create initial files
./bootstrap.py  # This is a bash script despite the .py extension

# After bootstrap, install dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up API keys
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY and GOOGLE_API_KEY
```

### Running the System
```bash
# Run the main nucleus
python nucleus.py

# Run tests
pytest
pytest -v  # verbose output
pytest tests/test_nucleus.py::test_specific  # run specific test
```

## Architecture

The system starts with a minimal bootstrap that creates:

1. **nucleus.py** - Core debate system implementation (~250 lines)
   - `DebateNucleus` class: Main orchestrator
   - Complexity assessment for routing decisions
   - AI client integration (Claude and Gemini)
   - Debate persistence in JSON format

2. **Directory Structure** (created on first run):
   - `/debates/` - Stores debate records as JSON files
   - `/evolutions/` - Tracks system evolution history

## Key Design Patterns

1. **Lazy Initialization**: AI clients are initialized only when needed
2. **Complexity-Based Routing**: Simple decisions bypass debates, complex ones trigger full debate rounds
3. **Self-Evolution**: The system can analyze and suggest improvements to itself via `evolve_self()`

## API Keys Required

- `ANTHROPIC_API_KEY` - For Claude Opus 4 access
- `GOOGLE_API_KEY` - For Gemini 2.5 Pro access

Both should be set in the `.env` file (create from `.env.example`).

## Testing Strategy

The project uses pytest with asyncio support. The nucleus includes built-in test cases in its main() function for:
1. Simple decisions (direct routing)
2. Complex decisions (debate routing)
3. Self-improvement suggestions

## Localhost Validation Rule

**IMPORTANT**: When checking localhost URLs, use the check_localhost.py script to capture screenshots and content:

```bash
# Check the web interface
python check_localhost.py http://localhost:8000

# Results will be saved in localhost_checks/ directory
ls localhost_checks/
```

This script uses Puppeteer to:
- Capture screenshots
- Save HTML content
- Extract text content
- Check for specific page elements
- Report status codes and errors

Use this whenever you need to validate what's running on localhost.