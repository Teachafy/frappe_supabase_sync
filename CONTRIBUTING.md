# Contributing to Frappe-Supabase Sync

Thank you for your interest in contributing to the Frappe-Supabase Sync project! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- Docker and Docker Compose
- Git
- A Frappe instance for testing
- A Supabase project for testing

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/your-username/frappe_supabase_sync.git
   cd frappe_supabase_sync
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Setup Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run Tests**
   ```bash
   pytest tests/
   ```

## 📋 Development Guidelines

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write comprehensive docstrings for all functions and classes
- Keep functions small and focused on a single responsibility

### Testing
- Write unit tests for all new functionality
- Write integration tests for webhook handlers and sync operations
- Aim for at least 80% code coverage
- Use descriptive test names that explain what is being tested

### Documentation
- Update README.md for user-facing changes
- Add docstrings for new functions and classes
- Update API documentation for new endpoints
- Include examples in docstrings where helpful

## 🔧 Development Workflow

### 1. Create a Feature Branch
```bash
git checkout -b feature/your-feature-name
```

### 2. Make Your Changes
- Write your code following the guidelines above
- Add tests for your changes
- Update documentation as needed

### 3. Test Your Changes
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_sync_engine.py

# Run with coverage
pytest --cov=src tests/

# Run linting
flake8 src/
black src/
```

### 4. Commit Your Changes
```bash
git add .
git commit -m "feat: add new feature description"
```

Use conventional commit messages:
- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation changes
- `test:` for test additions/changes
- `refactor:` for code refactoring
- `perf:` for performance improvements
- `chore:` for maintenance tasks

### 5. Push and Create Pull Request
```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## 🧪 Testing Guidelines

### Unit Tests
- Test individual functions and methods in isolation
- Mock external dependencies (Frappe API, Supabase API, Redis)
- Test both success and failure scenarios
- Test edge cases and error conditions

### Integration Tests
- Test complete workflows end-to-end
- Use test databases and services
- Test webhook processing with real payloads
- Test sync operations with actual data

### Test Structure
```
tests/
├── conftest.py              # Common fixtures
├── test_sync_engine.py      # Sync engine tests
├── test_webhook_handlers.py # Webhook handler tests
├── test_field_mapping.py    # Field mapping tests
├── test_schema_discovery.py # Schema discovery tests
└── test_integration.py      # Integration tests
```

## 📝 Pull Request Guidelines

### Before Submitting
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] No merge conflicts
- [ ] Commit messages are clear and descriptive

### Pull Request Template
When creating a pull request, please include:

1. **Description**: What changes were made and why
2. **Type of Change**: Bug fix, feature, documentation, etc.
3. **Testing**: How the changes were tested
4. **Breaking Changes**: Any breaking changes and migration steps
5. **Screenshots**: If applicable, include screenshots of UI changes

### Review Process
- All pull requests require at least one review
- Address review feedback promptly
- Keep pull requests focused and reasonably sized
- Update your branch if the main branch has moved forward

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: OS, Python version, Docker version, etc.
6. **Logs**: Relevant log output
7. **Screenshots**: If applicable

## 💡 Feature Requests

When requesting features, please include:

1. **Description**: Clear description of the feature
2. **Use Case**: Why this feature would be useful
3. **Proposed Solution**: How you think it should work
4. **Alternatives**: Other solutions you've considered
5. **Additional Context**: Any other relevant information

## 🔍 Code Review Guidelines

### As a Reviewer
- Be constructive and helpful in feedback
- Focus on code quality, not personal preferences
- Test the changes locally if possible
- Ask questions if something is unclear
- Approve when you're satisfied with the changes

### As an Author
- Respond to feedback promptly and professionally
- Ask questions if feedback is unclear
- Make requested changes or explain why you disagree
- Thank reviewers for their time and feedback

## 📚 Resources

### Documentation
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Docker Documentation](https://docs.docker.com/)
- [Frappe API Documentation](https://frappeframework.com/docs/user/en/api)
- [Supabase Documentation](https://supabase.com/docs)

### Tools
- **Code Editor**: VS Code with Python extension
- **Linting**: flake8, black, isort
- **Testing**: pytest, pytest-cov, pytest-asyncio
- **API Testing**: Postman or curl
- **Database**: PostgreSQL, Redis

## 🤝 Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on what's best for the community
- Show empathy towards other community members
- Accept constructive criticism gracefully
- Help others learn and grow

### Getting Help
- Check existing issues and discussions first
- Use GitHub Discussions for questions
- Join our Discord server for real-time chat
- Be specific when asking for help

## 📈 Performance Considerations

When contributing, consider:

- **Memory Usage**: Avoid memory leaks and excessive memory consumption
- **Database Queries**: Optimize database queries and use connection pooling
- **API Calls**: Minimize external API calls and implement proper caching
- **Concurrency**: Ensure thread safety and proper async handling
- **Error Handling**: Implement proper error handling and recovery

## 🔒 Security Considerations

- Never commit secrets or credentials
- Validate all input data
- Use proper authentication and authorization
- Follow security best practices for webhooks
- Keep dependencies updated

## 📊 Metrics and Monitoring

When adding new features, consider:

- Adding relevant metrics
- Including health checks
- Adding logging for debugging
- Considering alerting for critical failures
- Documenting monitoring requirements

## 🎯 Roadmap

Current priorities:
- [ ] Enhanced conflict resolution strategies
- [ ] Real-time dashboard
- [ ] Multi-tenant support
- [ ] Advanced field mapping
- [ ] Performance optimizations

## 📞 Contact

- **GitHub Issues**: For bug reports and feature requests
- **Discord**: For community discussions
- **Email**: For security issues or private matters

Thank you for contributing to Frappe-Supabase Sync! 🎉
