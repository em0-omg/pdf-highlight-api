# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a PDF highlight API project built with Python 3.13, currently in early development stage. The project uses `uv` for modern Python package management and is configured to provide API functionality for handling PDF highlights.

## Essential Commands

### Package Management
```bash
# Install/sync dependencies
uv sync

# Add new dependency
uv add <package-name>

# Add development dependency  
uv add --dev <package-name>

# Run application
uv run main.py
```

### Development Workflow
```bash
# Format code (when black is available)
black .

# Lint code (when ruff is available) 
ruff check . --fix

# Type check (when mypy is available)
mypy .

# Run tests (when pytest is available)
pytest
```

## Architecture Notes

- **Python Version**: 3.13 (specified in .python-version)
- **Package Manager**: uv (modern alternative to pip/poetry)
- **Entry Point**: main.py contains basic application structure
- **Configuration**: pyproject.toml follows PEP 518 standards

## Development Setup

The project currently has minimal dependencies defined in pyproject.toml. When adding functionality, common development tools to consider:

```bash
uv add --dev pytest black isort mypy ruff
```

## Project Structure

```
pdf-highlight-api/
├── main.py            # Application entry point
├── pyproject.toml     # Project configuration
└── .python-version    # Python version specification
```

As the project grows, consider organizing code into a proper package structure under `src/pdf_highlight_api/`.