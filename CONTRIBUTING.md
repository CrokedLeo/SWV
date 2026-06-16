# Contributing to SWV

Thank you for your interest in contributing to SWV!

## How to Contribute

### Report Bugs
- Check if bug is already reported
- Include detailed reproduction steps
- Provide environment information
- Attach error logs

### Suggest Features
- Clearly describe the feature
- Provide use case examples
- Consider implementation approach
- Link related issues

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make changes**
   - Follow code style
   - Add tests for new features
   - Update documentation

4. **Test thoroughly**
   ```bash
   # Backend
   python -m pytest tests/
   
   # Android
   ./gradlew test
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "feat: add new feature description"
   ```

6. **Push and open PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Document with docstrings
- Format with Black: `black backend/`

### Kotlin/Android
- Follow Google Android style guide
- Use meaningful variable names
- Add comments for complex logic
- Run linter: `./gradlew lint`

## Testing Requirements

- All tests must pass
- New features need tests
- Maintain or improve coverage

## Questions?

Open an issue with the question label.

---

Looking forward to your contributions! 🚀
