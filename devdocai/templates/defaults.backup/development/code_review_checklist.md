---
metadata:
  id: code_review_checklist_standard
  name: Code Review Checklist Template
  description: Comprehensive code review checklist
  category: development
  type: code_review
  version: 1.0.0
  author: DevDocAI
  tags: [code-review, checklist, quality-assurance]
variables:
  - name: project_name
    required: true
    type: string
---

# Code Review Checklist: {{project_name}}

## General

- [ ] Code is self-explanatory and readable
- [ ] No commented-out code
- [ ] No TODO comments in production code
- [ ] Consistent naming conventions
- [ ] Appropriate use of comments

## Functionality

- [ ] Code does what it's supposed to do
- [ ] Edge cases are handled
- [ ] Error handling is appropriate
- [ ] No hardcoded values

## Performance

- [ ] No obvious performance issues
- [ ] Efficient algorithms used
- [ ] Database queries are optimized
- [ ] Memory usage is reasonable

## Security

- [ ] Input validation implemented
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Sensitive data is protected

## Testing

- [ ] Unit tests are present
- [ ] Tests cover edge cases
- [ ] All tests pass
- [ ] Test coverage is adequate

## Documentation

- [ ] Code is documented appropriately
- [ ] API documentation updated
- [ ] README updated if necessary

## Architecture

- [ ] Follows project patterns
- [ ] Doesn't break existing functionality
- [ ] Proper separation of concerns
- [ ] Dependencies are justified
