# API JWT Authentication Solution

## Problem Resolved
The DevDocAI application was experiencing API connectivity failures (404 errors) after implementing JWT authentication. The issue was caused by the authentication decorator blocking requests even in development mode.

## Root Cause
The original `production_api_server_jwt.py` had a JWT authentication decorator (`@require_auth`) that was incorrectly handling development mode, causing all API requests to fail with 401/404 errors even though it was supposed to bypass authentication with the default JWT secret.

## Solution Implemented

### 1. Created Development-Friendly Server
**File**: `production_api_server_dev.py`

Key improvements:
- **Optional Authentication**: Uses `@optional_auth` decorator that completely bypasses authentication in development mode
- **DEV_MODE Flag**: Controlled by environment variable (`DEV_MODE=true` by default)
- **Automatic User Context**: Sets default user (`dev-user`) for all requests in dev mode
- **Enhanced CORS**: More permissive CORS settings for development
- **Better Error Handling**: Clear error messages and proper status codes
- **Test Endpoints**: Added `/api/test` endpoint for connectivity verification

### 2. API Endpoints Available

All endpoints work without authentication in development mode:

- `GET /api/health` - Health check endpoint
- `GET /api/test` - Simple connectivity test
- `POST /api/generate` - Document generation (AI or mock)
- `POST /api/analyze` - Quality analysis
- `POST /api/auth/login` - Get JWT token (for production readiness)
- `GET /api/auth/verify` - Verify JWT token

### 3. How to Use

#### Start the Development Server
```bash
# Start the development-friendly API server
python production_api_server_dev.py

# Or if you want to enforce authentication (production mode)
DEV_MODE=false python production_api_server_dev.py
```

#### Start the Frontend
```bash
# Start the React application with webpack proxy
npm run dev:react
```

The webpack proxy is configured to forward all `/api/*` requests from port 3000 to port 5000.

#### Test API Connectivity
```bash
# Direct API test (port 5000)
curl http://localhost:5000/api/health

# Through webpack proxy (port 3000)
curl http://localhost:3000/api/health

# Test document generation
curl -X POST http://localhost:3000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"template":"readme","project_name":"MyProject"}'

# Test quality analysis
curl -X POST http://localhost:3000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"content":"# My Document","file_name":"doc.md"}'
```

## Production Deployment

When ready for production:

1. **Set Environment Variables**:
```bash
export DEV_MODE=false
export JWT_SECRET_KEY="your-secure-secret-key"
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"
export GOOGLE_API_KEY="your-api-key"
```

2. **Obtain JWT Token**:
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'
```

3. **Use Token in Requests**:
```bash
curl http://localhost:5000/api/analyze \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Test","file_name":"test.md"}'
```

## Frontend JWT Integration (Future)

To add JWT authentication to the frontend:

1. **Login Component**: Create a login form that calls `/api/auth/login`
2. **Token Storage**: Store JWT token in localStorage or sessionStorage
3. **API Service**: Add Authorization header to all API requests
4. **Token Refresh**: Implement token refresh logic before expiration

Example API service with JWT:
```javascript
class APIService {
  constructor() {
    this.token = localStorage.getItem('jwt_token');
  }

  async request(url, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    if (response.status === 401) {
      // Token expired or invalid
      this.handleAuthError();
    }

    return response;
  }

  async login(email, password) {
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    if (data.success && data.token) {
      this.token = data.token;
      localStorage.setItem('jwt_token', data.token);
    }
    return data;
  }
}
```

## Server Features

### Development Mode (Default)
- No authentication required
- Automatic user context injection
- Mock data for testing
- Debug logging enabled
- CORS fully open for localhost

### Production Mode
- JWT authentication required
- Token expiration (24 hours default)
- Secure CORS configuration
- Rate limiting ready
- Circuit breakers for resilience

## Monitoring

The server logs all requests with:
- Correlation IDs for tracking
- User identification
- Response times
- Error details

Example log output:
```
INFO: Quality analysis request from user dev-user: document.md
INFO: Quality analysis completed: 5ms
INFO: Document generation request from user dev-user: template=readme, project=MyProject
INFO: Document generated successfully: 1200 chars
```

## Troubleshooting

### Issue: Still getting 404 errors
- Ensure the dev server is running: `python production_api_server_dev.py`
- Check the port: API should be on 5000, frontend on 3000
- Verify webpack proxy is working: `curl http://localhost:3000/api/health`

### Issue: Authentication errors in dev mode
- Ensure `DEV_MODE=true` (default)
- Check server logs for the mode: "Development Mode: True"
- Clear browser cache and cookies

### Issue: CORS errors
- The dev server has permissive CORS settings
- Ensure you're accessing via `localhost`, not `127.0.0.1`
- Check browser console for specific CORS error details

## Summary

The solution provides a smooth development experience while maintaining production-ready JWT authentication capabilities. In development mode, authentication is completely bypassed for ease of testing. In production mode, full JWT authentication with proper security is enforced.

The key insight was that the decorator order and implementation in the original JWT server was preventing the development bypass from working correctly. The new implementation clearly separates development and production modes, making the system more maintainable and developer-friendly.