---
metadata:
  id: api_reference_standard
  name: API Reference Template
  description: Comprehensive API documentation template with endpoints and examples
  category: api
  type: api_reference
  version: 1.0.0
  author: DevDocAI
  tags: [api, documentation, reference, endpoints, rest]
  is_custom: false
  is_active: true
variables:
  - name: api_name
    description: Name of the API
    required: true
    type: string
  - name: api_version
    description: API version
    required: true
    type: string
  - name: base_url
    description: Base URL of the API
    required: true
    type: string
  - name: authentication_type
    description: Authentication method
    required: false
    type: string
    default: "Bearer Token"
  - name: contact_email
    description: Contact email for support
    required: false
    type: string
  - name: rate_limit
    description: Rate limiting information
    required: false
    type: string
    default: "1000 requests per hour"
---

# {{api_name}} API Reference

Version: {{api_version}}

Base URL: `{{base_url}}`

## Overview

This document provides a comprehensive reference for the {{api_name}} API. The API follows REST principles and uses JSON for request and response bodies.

## Authentication

<!-- IF authentication_type -->
This API uses **{{authentication_type}}** for authentication.

```http
Authorization: Bearer YOUR_API_TOKEN
```

To obtain an API token, please contact our support team<!-- IF contact_email --> at [{{contact_email}}](mailto:{{contact_email}})<!-- END IF -->.
<!-- END IF -->

## Rate Limiting

<!-- IF rate_limit -->
API requests are limited to {{rate_limit}}. Rate limit headers are included in all responses:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```
<!-- END IF -->

## Response Format

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": {},
  "message": "Request successful",
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## Error Handling

Error responses include detailed information:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {}
  },
  "timestamp": "2023-01-01T00:00:00Z"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `BAD_REQUEST` | Invalid request format or parameters |
| `UNAUTHORIZED` | Authentication required or invalid |
| `FORBIDDEN` | Access denied |
| `NOT_FOUND` | Resource not found |
| `VALIDATION_ERROR` | Request validation failed |
| `RATE_LIMITED` | Rate limit exceeded |
| `INTERNAL_ERROR` | Server error |

## Endpoints

### Authentication

#### POST /auth/login

Authenticate and obtain an access token.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_in": 3600,
    "user": {
      "id": "12345",
      "email": "user@example.com",
      "name": "John Doe"
    }
  }
}
```

### Users

#### GET /users

Retrieve a list of users.

**Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `limit` (integer, optional): Items per page (default: 10, max: 100)
- `sort` (string, optional): Sort field (default: created_at)
- `order` (string, optional): Sort order (asc/desc, default: desc)

**Response:**
```json
{
  "success": true,
  "data": {
    "users": [
      {
        "id": "12345",
        "email": "user@example.com",
        "name": "John Doe",
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-01-01T00:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 100,
      "pages": 10
    }
  }
}
```

#### GET /users/{id}

Retrieve a specific user by ID.

**Parameters:**
- `id` (string, required): User ID

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "12345",
      "email": "user@example.com",
      "name": "John Doe",
      "profile": {
        "avatar_url": "https://example.com/avatar.jpg",
        "bio": "Software developer"
      },
      "created_at": "2023-01-01T00:00:00Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  }
}
```

#### POST /users

Create a new user.

**Request:**
```json
{
  "email": "newuser@example.com",
  "name": "Jane Smith",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "67890",
      "email": "newuser@example.com",
      "name": "Jane Smith",
      "created_at": "2023-01-01T00:00:00Z"
    }
  },
  "message": "User created successfully"
}
```

#### PUT /users/{id}

Update an existing user.

**Parameters:**
- `id` (string, required): User ID

**Request:**
```json
{
  "name": "Jane Doe",
  "profile": {
    "bio": "Senior software developer"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "67890",
      "email": "newuser@example.com",
      "name": "Jane Doe",
      "profile": {
        "bio": "Senior software developer"
      },
      "updated_at": "2023-01-01T00:00:00Z"
    }
  },
  "message": "User updated successfully"
}
```

#### DELETE /users/{id}

Delete a user.

**Parameters:**
- `id` (string, required): User ID

**Response:**
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

## SDKs and Libraries

### JavaScript/Node.js

```bash
npm install {{api_name}}-sdk
```

```javascript
const {{api_name}} = require('{{api_name}}-sdk');

const client = new {{api_name}}({
  apiKey: 'your-api-key',
  baseUrl: '{{base_url}}'
});

// Example usage
const users = await client.users.list();
```

### Python

```bash
pip install {{api_name}}-python
```

```python
from {{api_name}} import Client

client = Client(
    api_key='your-api-key',
    base_url='{{base_url}}'
)

# Example usage
users = client.users.list()
```

## Webhooks

The API supports webhooks for real-time event notifications.

### Event Types

- `user.created` - User created
- `user.updated` - User updated
- `user.deleted` - User deleted

### Webhook Payload

```json
{
  "event": "user.created",
  "data": {
    "user": {
      "id": "12345",
      "email": "user@example.com",
      "name": "John Doe"
    }
  },
  "timestamp": "2023-01-01T00:00:00Z"
}
```

## Support

<!-- IF contact_email -->
For API support, please contact us at [{{contact_email}}](mailto:{{contact_email}}).
<!-- END IF -->

## Changelog

### v{{api_version}}
- Initial API release
- User management endpoints
- Authentication system
- Rate limiting implementation