# Suggested Commands for PDF Highlight API

## Package Management
```bash
# Install dependencies (when they exist)
uv sync

# Add a new dependency
uv add <package-name>

# Add development dependency
uv add --dev <package-name>

# Create/activate virtual environment
uv venv
source .venv/bin/activate
```

## Running the Application
```bash
# Run the main application
python main.py
# or with uv
uv run main.py
```

## Development Commands
```bash
# Install common development tools (recommended to add later)
uv add --dev pytest black isort mypy ruff

# Code formatting (when black is installed)
black .

# Code linting (when ruff is installed)
ruff check .
ruff check . --fix

# Type checking (when mypy is installed)
mypy .

# Import sorting (when isort is installed)
isort .
```

## Testing Commands
```bash
# Run tests (when pytest is installed)
pytest
pytest -v  # verbose output
pytest --cov  # with coverage (if pytest-cov installed)
```

## System Utilities (macOS/Darwin)
```bash
# File operations
ls -la          # list files with details
find . -name "*.py"  # find Python files
grep -r "pattern" .  # search for patterns

# Git operations
git status
git add .
git commit -m "message"
git log --oneline

# Directory navigation
pwd
cd <directory>
```

## Project Setup Commands
```bash
# Check Python version
python3 --version

# Check uv version
uv --version

# Initialize project (already done)
uv init

# Update project dependencies
uv lock
```