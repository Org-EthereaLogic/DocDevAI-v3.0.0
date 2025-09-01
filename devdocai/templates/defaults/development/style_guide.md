---
metadata:
  id: style_guide_standard
  name: Style Guide Template
  description: Code style guide and conventions
  category: development
  type: style_guide
  version: 1.0.0
  author: DevDocAI
  tags: [style-guide, conventions, coding-standards]
variables:
  - name: project_name
    required: true
    type: string
  - name: language
    required: false
    type: string
    default: "JavaScript"
---

# {{project_name}} Style Guide

This style guide establishes conventions for {{language}} code in {{project_name}}.

## General Principles

- **Consistency** - Follow established patterns
- **Readability** - Code should be self-documenting
- **Simplicity** - Prefer simple solutions
- **Performance** - Consider performance implications

## Code Formatting

### Indentation

- Use 2 spaces for indentation
- No hard tabs

### Line Length

- Maximum 100 characters per line
- Break long lines appropriately

### Naming Conventions

- Variables: camelCase
- Functions: camelCase
- Classes: PascalCase
- Constants: UPPER_SNAKE_CASE

## Examples

```javascript
// Good
const userAccount = new UserAccount();
const MAX_RETRY_COUNT = 3;

function calculateTotal(items) {
  return items.reduce((sum, item) => sum + item.price, 0);
}

// Bad
const user_account = new userAccount();
const maxretrycount = 3;

function calculate_total(items){
    return items.reduce((sum,item)=>sum+item.price,0);
}
```
