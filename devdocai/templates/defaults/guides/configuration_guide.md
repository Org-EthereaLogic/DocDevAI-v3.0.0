---
metadata:
  id: configuration_guide_standard
  name: Configuration Guide Template
  description: Application configuration guide
  category: guides
  type: configuration_guide
  version: 1.0.0
  author: DevDocAI
  tags: [configuration, setup, environment]
variables:
  - name: app_name
    required: true
    type: string
---

# {{app_name}} Configuration Guide

This guide explains how to configure {{app_name}} for different environments.

## Configuration Files

### Main Configuration

Location: `config/app.yml`

```yaml
app:
  name: {{app_name}}
  version: 1.0.0
  debug: false
  port: 3000

database:
  host: localhost
  port: 5432
  name: {{app_name}}_db
  username: app_user
  password: ${DATABASE_PASSWORD}

cache:
  enabled: true
  host: localhost
  port: 6379
  ttl: 3600

logging:
  level: info
  file: logs/app.log
  max_size: 100MB
  max_files: 10
```

### Environment Variables

```bash
# Required
DATABASE_PASSWORD=your_secure_password
JWT_SECRET=your_jwt_secret

# Optional
APP_ENV=production
LOG_LEVEL=info
CACHE_ENABLED=true
```

## Environment-Specific Configuration

### Development

```yaml
app:
  debug: true
  port: 3001

database:
  name: {{app_name}}_dev

logging:
  level: debug
```

### Production

```yaml
app:
  debug: false
  port: 80

database:
  host: prod-db-host
  ssl: true

logging:
  level: warn
```

## Security Configuration

### SSL/TLS

```yaml
ssl:
  enabled: true
  cert_file: /path/to/cert.pem
  key_file: /path/to/key.pem
```

### Authentication

```yaml
auth:
  jwt:
    secret: ${JWT_SECRET}
    expiry: 24h
  oauth:
    google:
      client_id: ${GOOGLE_CLIENT_ID}
      client_secret: ${GOOGLE_CLIENT_SECRET}
```

## Validation

Test your configuration:

```bash
{{app_name}} config validate
```
