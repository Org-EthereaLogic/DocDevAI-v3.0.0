"""
Marketplace API Client
Handles HTTP communication with the DevDocAI Template Marketplace API.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urljoin
import urllib.request
import urllib.error
import ssl

logger = logging.getLogger(__name__)


class MarketplaceAPIClient:
    """
    API client for communicating with the DevDocAI Template Marketplace.
    
    Handles all HTTP requests, authentication, rate limiting, and error handling
    for marketplace operations.
    """
    
    def __init__(
        self,
        base_url: str = "https://marketplace.devdocai.org",
        api_key: Optional[str] = None,
        timeout: int = 30,
        offline_mode: bool = False
    ):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the marketplace API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            offline_mode: Enable offline/demo mode
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.offline_mode = offline_mode
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # Statistics
        self.request_count = 0
        self.error_count = 0
        
        # SSL context for HTTPS
        self.ssl_context = ssl.create_default_context()
        
        if offline_mode:
            logger.info("API client initialized in offline/demo mode")
    
    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the marketplace API.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            data: Request data for POST/PUT
            headers: Additional headers
            
        Returns:
            Response data as dictionary
        """
        if self.offline_mode:
            return self._get_demo_response(endpoint, method)
        
        # Rate limiting
        self._enforce_rate_limit()
        
        url = urljoin(self.base_url, endpoint)
        
        # Prepare headers
        request_headers = {
            "User-Agent": "DevDocAI-Marketplace-Client/3.0.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            request_headers["Authorization"] = f"Bearer {self.api_key}"
        
        if headers:
            request_headers.update(headers)
        
        # Prepare data
        request_data = None
        if data and method in ["POST", "PUT", "PATCH"]:
            request_data = json.dumps(data).encode('utf-8')
        
        try:
            # Create request
            request = urllib.request.Request(
                url,
                data=request_data,
                headers=request_headers,
                method=method
            )
            
            # Make request
            self.request_count += 1
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self.ssl_context
            ) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data
                
        except urllib.error.HTTPError as e:
            self.error_count += 1
            error_body = e.read().decode('utf-8')
            logger.error(f"HTTP {e.code} error: {error_body}")
            
            # Return error response
            return {
                "error": True,
                "status_code": e.code,
                "message": error_body
            }
            
        except urllib.error.URLError as e:
            self.error_count += 1
            logger.error(f"Network error: {e}")
            
            # Fallback to demo mode on network errors
            if not self.offline_mode:
                logger.info("Falling back to demo mode due to network error")
                return self._get_demo_response(endpoint, method)
            
            return {"error": True, "message": str(e)}
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Unexpected error: {e}")
            return {"error": True, "message": str(e)}
    
    def browse_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "popularity",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Browse templates in the marketplace.
        
        Args:
            category: Filter by category
            search: Search query
            sort_by: Sort criteria
            page: Page number
            per_page: Items per page
            
        Returns:
            Templates and pagination info
        """
        params = {
            "page": page,
            "per_page": per_page,
            "sort_by": sort_by
        }
        
        if category:
            params["category"] = category
        if search:
            params["search"] = search
        
        query_string = urlencode(params)
        endpoint = f"/api/v1/templates?{query_string}"
        
        return self._make_request(endpoint)
    
    def download_template(self, template_id: str) -> Dict[str, Any]:
        """
        Download a template from the marketplace.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data with content and signature
        """
        endpoint = f"/api/v1/templates/{template_id}/download"
        return self._make_request(endpoint)
    
    def publish_template(
        self,
        template_data: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a template to the marketplace.
        
        Args:
            template_data: Template to publish
            signature: Optional Ed25519 signature
            
        Returns:
            Response with template ID or error
        """
        data = {
            "template": template_data,
            "signature": signature
        }
        
        endpoint = "/api/v1/templates"
        return self._make_request(endpoint, method="POST", data=data)
    
    def get_template_info(self, template_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template metadata
        """
        endpoint = f"/api/v1/templates/{template_id}"
        return self._make_request(endpoint)
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _get_demo_response(self, endpoint: str, method: str) -> Dict[str, Any]:
        """
        Get demo/mock response for offline mode.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            
        Returns:
            Mock response data
        """
        # Demo templates for offline mode
        demo_templates = [
            {
                "id": "api-docs-v1.0",
                "name": "API Documentation Template",
                "version": "1.0.0",
                "description": "Comprehensive API documentation template with OpenAPI support",
                "category": "api",
                "author": "DevDocAI Team",
                "rating": 4.8,
                "downloads": 1523,
                "tags": ["api", "openapi", "swagger", "rest"],
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-12-01T15:30:00Z"
            },
            {
                "id": "readme-pro-v2.1",
                "name": "Professional README",
                "version": "2.1.0",
                "description": "Professional README template with badges and sections",
                "category": "readme",
                "author": "Community",
                "rating": 4.9,
                "downloads": 3421,
                "tags": ["readme", "markdown", "documentation"],
                "created_at": "2024-02-20T09:00:00Z",
                "updated_at": "2024-11-15T12:00:00Z"
            },
            {
                "id": "arch-guide-v1.5",
                "name": "Architecture Guide",
                "version": "1.5.0",
                "description": "Software architecture documentation template",
                "category": "architecture",
                "author": "DevDocAI Team",
                "rating": 4.7,
                "downloads": 892,
                "tags": ["architecture", "design", "system"],
                "created_at": "2024-03-10T14:00:00Z",
                "updated_at": "2024-10-20T16:45:00Z"
            }
        ]
        
        if "browse" in endpoint or "/templates?" in endpoint or endpoint.startswith("/api/v1/templates?"):
            return {
                "templates": demo_templates,
                "pagination": {
                    "page": 1,
                    "per_page": 20,
                    "total": len(demo_templates),
                    "pages": 1
                }
            }
        
        elif "/download" in endpoint:
            template_id = endpoint.split('/')[-2]
            for template in demo_templates:
                if template["id"] == template_id:
                    return {
                        **template,
                        "content": {
                            "sections": ["Introduction", "Installation", "Usage", "API Reference"],
                            "template_text": "# {{title}}\n\n## Introduction\n{{description}}\n\n## Installation\n{{installation}}\n\n## Usage\n{{usage}}\n\n## API Reference\n{{api_reference}}"
                        },
                        "signature": "demo_signature_" + template_id,
                        "public_key": "demo_public_key"
                    }
            return {"error": True, "message": "Template not found"}
        
        elif method == "POST" and "/templates" in endpoint:
            return {
                "success": True,
                "template_id": f"demo-template-{int(time.time())}",
                "message": "Template published successfully (demo mode)"
            }
        
        else:
            # Default demo response
            return {
                "status": "demo",
                "message": "Demo response for offline mode",
                "endpoint": endpoint
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get API client statistics."""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.request_count),
            "offline_mode": self.offline_mode,
            "base_url": self.base_url
        }