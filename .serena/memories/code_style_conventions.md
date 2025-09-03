# Code Style and Conventions

## Python Style Guidelines
Since this is a new project, these are recommended conventions to establish:

### Code Formatting
- **Formatter**: Black (recommended to add as dev dependency)
- **Line Length**: 88 characters (Black default)
- **Import Sorting**: isort (recommended to add as dev dependency)

### Code Quality
- **Linter**: Ruff (modern, fast Python linter - recommended)
- **Type Checker**: MyPy (for static type checking)

### Naming Conventions
- **Functions/Variables**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_SNAKE_CASE
- **Files/Modules**: lowercase with underscores

### Type Hints
- Use type hints for all function parameters and return values
- Import typing constructs from `typing` module
- Use modern syntax (Python 3.13+ features)

### Docstrings
- Use Google-style docstrings
- Document all public functions, classes, and modules
- Include parameter types and return types in docstrings

### Project Structure Recommendations
```
pdf-highlight-api/
├── src/                    # Source code
│   └── pdf_highlight_api/  # Main package
├── tests/                  # Test files
├── docs/                   # Documentation
├── pyproject.toml          # Project config
└── README.md               # Project documentation
```

## Current State
- No specific style is established yet (project is in very early stage)
- Only basic main.py exists with simple print statement
- Recommended to establish these conventions as development progresses