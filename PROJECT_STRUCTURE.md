# Zamaz Debate System - Project Structure

## New Directory Organization

```
zamaz-debate/
├── src/                      # Source code
│   ├── core/                 # Core business logic
│   │   ├── __init__.py
│   │   ├── nucleus.py        # Main debate engine
│   │   └── evolution_tracker.py
│   ├── domain/               # Domain models (already exists)
│   │   ├── __init__.py
│   │   └── models.py
│   ├── services/             # Services (already exists)
│   │   ├── __init__.py
│   │   ├── ai_client_factory.py
│   │   ├── delegation_service.py
│   │   └── pr_service.py
│   ├── web/                  # Web interface
│   │   ├── __init__.py
│   │   ├── app.py            # FastAPI application
│   │   └── static/           # Static files
│   └── utils/                # Utilities
│       ├── __init__.py
│       ├── bootstrap.py
│       └── localhost_checker.py
├── scripts/                  # Executable scripts
│   ├── bootstrap_project.py
│   ├── check_localhost.py
│   ├── manual_debate.py
│   └── security_check.sh
├── tests/                    # Test files
│   ├── __init__.py
│   └── test_nucleus.py
├── data/                     # Data directories
│   ├── debates/              # Debate records
│   ├── evolutions/           # Evolution history
│   ├── decisions/            # Decision records
│   ├── pr_drafts/            # PR drafts
│   ├── pr_history/           # PR history
│   ├── ai_cache/             # AI response cache
│   └── localhost_checks/     # Localhost validation
├── docs/                     # Documentation
│   ├── CLAUDE.md
│   ├── CLAUDE_AI_INTEGRATION.md
│   ├── COST_SAVING_GUIDE.md
│   ├── QUICKSTART.md
│   ├── SECURITY.md
│   └── examples/
├── config/                   # Configuration files
│   ├── .env
│   └── .env.example
├── .gitignore
├── .githooks/                # Git hooks
├── Makefile
├── README.md
├── requirements.txt
└── setup.sh
```

## Benefits of New Structure

1. **Clear Separation of Concerns**
   - Core logic in `src/core/`
   - Web interface in `src/web/`
   - Utilities in `src/utils/`

2. **Better Organization**
   - All source code under `src/`
   - All data under `data/`
   - All documentation under `docs/`
   - All configuration under `config/`

3. **Easier Navigation**
   - Related files grouped together
   - Clear purpose for each directory
   - Standard Python project layout

4. **Improved Maintainability**
   - Easier to find files
   - Clear boundaries between modules
   - Better for team collaboration