# Development Environment Details

## System Information
- **OS**: macOS (Darwin 24.6.0)
- **Python**: 3.13.1 (installed via Homebrew at `/opt/homebrew/bin/python3`)
- **Package Manager**: uv 0.7.8 (modern Python package manager)
- **Python Version Manager**: Indicated by `.python-version` file (likely pyenv)

## Development Tools Available
- **uv**: Modern Python package and project manager
- **git**: Version control system
- **Python 3.13**: Latest Python version

## Project Configuration Files
- **pyproject.toml**: Modern Python project configuration (PEP 518)
- **.python-version**: Specifies Python 3.13 for the project
- **.gitignore**: Python-specific ignore patterns
- **README.md**: Currently empty, ready for documentation

## MCP Integration
- **Serena**: Configured for this project (`.serena/project.yml`)
- **Claude Code**: Local settings available (`.claude/settings.local.json`)

## Recommended Next Steps for Development Setup
1. Add development dependencies:
   ```bash
   uv add --dev pytest black isort mypy ruff pytest-cov
   ```

2. Create proper source structure:
   ```bash
   mkdir -p src/pdf_highlight_api tests docs
   ```

3. Set up pre-commit hooks (optional):
   ```bash
   uv add --dev pre-commit
   ```

4. Initialize proper project structure and move main.py to appropriate location

## macOS-Specific Considerations
- Uses Homebrew Python installation
- Standard Unix-like commands available (ls, grep, find, etc.)
- File system is case-insensitive by default
- Permissions may need attention for certain operations