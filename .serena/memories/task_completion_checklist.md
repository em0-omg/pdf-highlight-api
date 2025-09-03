# Task Completion Checklist

## Before Completing Any Development Task

### 1. Code Quality Checks
```bash
# Format code (when black is installed)
black .

# Sort imports (when isort is installed)  
isort .

# Lint code (when ruff is installed)
ruff check .
ruff check . --fix  # auto-fix issues

# Type checking (when mypy is installed)
mypy .
```

### 2. Testing
```bash
# Run all tests (when pytest is installed)
pytest

# Run tests with coverage (when pytest-cov is installed)
pytest --cov

# Run specific test file
pytest tests/test_<module>.py
```

### 3. Dependency Management
```bash
# Update lock file if dependencies changed
uv lock

# Verify all dependencies are properly installed
uv sync
```

### 4. Git Operations
```bash
# Check status
git status

# Add changes
git add .

# Commit with descriptive message
git commit -m "descriptive commit message"

# Push changes (if working with remote)
git push
```

### 5. Documentation
- Update README.md if public API changes
- Update docstrings for any modified functions
- Add/update type hints

## Development Tools to Install (Recommended)
```bash
uv add --dev pytest black isort mypy ruff pytest-cov
```

## Current State
- Since this is a new project, most development tools are not yet installed
- The checklist will become more relevant as the project grows and tools are added
- Currently, only basic git operations and Python execution are available