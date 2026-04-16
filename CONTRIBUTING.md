# 🤝 Contributing to Smart Model Selector

Thank you for your interest in contributing! This project follows standard open source best practices.

## 🚀 Quick Start

```bash
# Fork and clone the repo
git clone https://github.com/wuleiyuan/smart-model-selector.git
cd smart-model-selector

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Install in editable mode
```

## 🧪 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run linting
flake8 . --select=E9,F63,F7,F82
```

## 🐛 Reporting Bugs

Please include:
- Python version (`python --version`)
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## 💡 Suggesting Features

Open an Issue with:
- Clear use case description
- Proposed solution (if any)
- Alternative solutions considered

## 🔄 Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Write** your code with proper type hints and docstrings
4. **Test** your changes: `pytest`
5. **Lint** your code: `flake8 . --select=E9,F63,F7,F82`
6. **Commit** with clear message: `git commit -m "feat: add new routing strategy"`
7. **Push** to your fork: `git push origin feature/my-feature`
8. **Open** a Pull Request

## 📝 Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example:
```
feat(dispatcher): add weighted random routing strategy

- Implement weighted provider selection
- Add tests for edge cases
- Update README with new strategy docs

Closes #123
```

## 📐 Code Style

- Follow PEP 8
- Max line length: 100 characters
- Use type hints where possible
- Add docstrings for public functions

## ❓ Questions?

Open an Issue or check the [Wiki](https://github.com/wuleiyuan/smart-model-selector/wiki)

---

**⭐ Thank you for making this project better!**
