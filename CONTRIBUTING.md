# Contributing to MaintainerOps

Thank you for your interest in contributing to **MaintainerOps**! We are committed to building an open, explainable, and respectful toolkit for open-source maintainers.

## Code of Conduct

MaintainerOps follows standard community standards: be welcoming, respectful, and open to feedback. We treat all contributors and maintainers with empathy.

## Development Setup

### Prerequisites
- Python 3.10+ (Python 3.12+ recommended)
- `pip` or virtualenv manager

### Installation
1. Clone or navigate to the repository:
   ```bash
   cd maintainerops
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install the package in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Running Tests & Checks

Run pytest to execute the full test suite with mocked offline fixtures:
```bash
pytest
```

Run linter checks:
```bash
ruff check .
```

## Core Contribution Guidelines

1. **Deterministic by Default:** Core analysis rules must produce deterministic output for identical input fixtures without requiring an external paid LLM key.
2. **Evidence-Backed Findings:** Every new rule or metric must supply clear evidence (such as line numbers, regex matches, or matching tokens).
3. **No Blind Bot Actions:** Never implement automatic closing, deletion, or offensive messaging. Maintainers must always remain in control.
