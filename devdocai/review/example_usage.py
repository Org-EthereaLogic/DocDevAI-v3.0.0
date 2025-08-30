"""
M007 Review Engine - Unified Implementation Usage Examples.

Demonstrates how to use the new unified review engine across different
operation modes and configuration scenarios.
"""

import asyncio
from devdocai.review import (
    ReviewEngine,
    OperationMode,
    ReviewEngineConfig,
    ReviewDimension,
    ReportGenerator
)


async def basic_usage_example():
    """Example: Basic document review in BASIC mode."""
    print("=== Basic Usage Example ===")
    
    # Initialize engine in basic mode
    engine = ReviewEngine(mode=OperationMode.BASIC)
    
    # Sample document content
    content = """
    # API Documentation
    
    This is a sample API documentation.
    
    ## Authentication
    TODO: Add authentication details
    
    ## Endpoints
    
    ### GET /users
    Returns list of users
    
    ### POST /users  
    Creates a new user
    """
    
    # Perform review
    result = await engine.review_document(
        content=content,
        document_type="api",
        metadata={"author": "developer"}
    )
    
    # Display results
    print(f"Overall Score: {result.overall_score:.1f}/100")
    print(f"Status: {result.status.value}")
    print(f"Total Issues: {len(result.all_issues)}")
    print(f"Execution Time: {result.metrics.execution_time_ms:.1f}ms")
    
    # Show top issues
    for issue in result.all_issues[:3]:
        print(f"- [{issue.severity.value.upper()}] {issue.title}")
    
    await engine.cleanup()
    print()


async def optimized_usage_example():
    """Example: Performance-optimized review with parallel processing."""
    print("=== Optimized Usage Example ===")
    
    # Configure for optimized performance
    config = ReviewEngineConfig(
        parallel_analysis=True,
        enable_caching=True,
        cache_ttl_seconds=1800,  # 30 minutes
        max_workers=6
    )
    
    # Initialize engine in optimized mode
    engine = ReviewEngine(
        mode=OperationMode.OPTIMIZED,
        config=config
    )
    
    # Multiple documents for batch processing
    documents = [
        {
            'id': 'doc1',
            'content': '''# User Guide
            This guide explains how to use our application.
            
            ## Getting Started
            Follow these steps to get started.
            ''',
            'type': 'guide'
        },
        {
            'id': 'doc2', 
            'content': '''# README
            ## Installation
            npm install package-name
            
            ## Usage
            import package from 'package-name';
            ''',
            'type': 'readme'
        },
        {
            'id': 'doc3',
            'content': '''# Changelog
            ## Version 2.0.0
            - Added new features
            - Fixed bugs
            ''',
            'type': 'changelog'
        }
    ]
    
    # Batch review with parallel processing
    results = await engine.batch_review(
        documents=documents,
        parallel=True,
        batch_size=10
    )
    
    print(f"Processed {len(results)} documents")
    for result in results:
        print(f"- {result.document_id}: {result.overall_score:.1f}/100 ({result.status.value})")
    
    # Show performance statistics
    stats = engine.get_statistics()
    print(f"Cache Hit Rate: {stats['cache_hit_rate']*100:.1f}%")
    
    await engine.cleanup()
    print()


async def secure_usage_example():
    """Example: Secure review with encryption and access control."""
    print("=== Secure Usage Example ===")
    
    # Configure security settings
    config = ReviewEngineConfig(
        enable_pii_detection=True,
        mask_pii_in_reports=True,
        pii_detection_confidence=0.8,
        strict_mode=True
    )
    
    # Initialize engine in secure mode with encryption key
    encryption_key = b'your-32-byte-encryption-key-here!!'  # 32 bytes for Fernet
    engine = ReviewEngine(
        mode=OperationMode.SECURE,
        config=config,
        encryption_key=encryption_key
    )
    
    # Document with potential PII
    content = """
    # Customer Data Processing
    
    Our system processes customer information including:
    - Email: john.doe@example.com
    - Phone: (555) 123-4567
    
    ## Security Measures
    All data is encrypted using AES-256.
    
    ## API Keys
    Use environment variables for secrets.
    Never hardcode: api_key = "sk_test_1234567890abcdef"
    """
    
    # Perform secure review with user ID for access control
    result = await engine.review_document(
        content=content,
        document_type="security",
        user_id="admin_user_123"
    )
    
    print(f"Security Review - Score: {result.overall_score:.1f}/100")
    print(f"Status: {result.status.value}")
    print(f"Security Issues: {sum(1 for issue in result.all_issues if issue.dimension.value == 'security_pii')}")
    
    # Show security-specific metrics
    security_metrics = await engine.get_security_metrics()
    print(f"PII Detected: {security_metrics.get('pii_detected', 0)} instances")
    print(f"Validations Performed: {security_metrics.get('validations_performed', 0)}")
    
    await engine.cleanup()
    print()


async def enterprise_usage_example():
    """Example: Enterprise mode with all features enabled."""
    print("=== Enterprise Usage Example ===")
    
    # Full enterprise configuration
    config = ReviewEngineConfig(
        # Performance settings
        parallel_analysis=True,
        max_workers=8,
        enable_caching=True,
        cache_ttl_seconds=3600,
        
        # Quality settings
        approval_threshold=90.0,
        conditional_approval_threshold=75.0,
        strict_mode=True,
        
        # Security settings
        enable_pii_detection=True,
        mask_pii_in_reports=True,
        pii_detection_confidence=0.9,
        
        # Feature settings
        auto_fix_enabled=True,
        generate_suggestions=True,
        include_code_snippets=True,
        use_quality_engine=True,
        use_miair_optimization=True,
        
        # Dimension weights for enterprise use
        dimension_weights={
            ReviewDimension.TECHNICAL_ACCURACY: 0.30,
            ReviewDimension.COMPLETENESS: 0.25,
            ReviewDimension.SECURITY_PII: 0.25,
            ReviewDimension.CONSISTENCY: 0.10,
            ReviewDimension.STYLE_FORMATTING: 0.10,
        }
    )
    
    # Initialize enterprise engine
    engine = ReviewEngine(
        mode=OperationMode.ENTERPRISE,
        config=config
    )
    
    # Complex enterprise document
    content = """
    # Enterprise API Specification v2.0
    
    ## Overview
    This document specifies the Enterprise REST API for customer management.
    
    ## Authentication
    All API calls require Bearer token authentication:
    ```
    Authorization: Bearer <token>
    ```
    
    ## Endpoints
    
    ### Customer Management
    
    #### GET /api/v2/customers
    Retrieves paginated list of customers.
    
    **Parameters:**
    - `page`: Page number (default: 1)
    - `limit`: Items per page (default: 50, max: 200)
    
    **Response:**
    ```json
    {
      "data": [
        {
          "id": "cust_123",
          "email": "customer@company.com",
          "created_at": "2024-01-15T10:30:00Z"
        }
      ],
      "pagination": {
        "page": 1,
        "limit": 50,
        "total": 150
      }
    }
    ```
    
    #### POST /api/v2/customers
    Creates a new customer record.
    
    **Request Body:**
    ```json
    {
      "email": "new.customer@company.com",
      "name": "New Customer",
      "phone": "+1-555-0123"
    }
    ```
    
    ## Error Handling
    
    All errors follow RFC 7807 Problem Details format:
    
    ```json
    {
      "type": "https://api.company.com/errors/validation",
      "title": "Validation Failed",
      "status": 400,
      "detail": "Email address is required",
      "instance": "/api/v2/customers"
    }
    ```
    
    ## Rate Limiting
    
    API calls are limited to 1000 requests per hour per API key.
    
    ## Security Considerations
    
    - All communications must use TLS 1.2 or higher
    - API keys should be rotated every 90 days
    - Never log or expose customer PII in error messages
    """
    
    # Perform comprehensive enterprise review
    result = await engine.review_document(
        content=content,
        document_type="api",
        metadata={
            "version": "2.0",
            "classification": "enterprise",
            "compliance_required": True
        },
        user_id="enterprise_reviewer"
    )
    
    print(f"Enterprise Review Results:")
    print(f"Overall Score: {result.overall_score:.1f}/100")
    print(f"Status: {result.status.value}")
    print(f"Total Issues: {len(result.all_issues)}")
    
    # Show dimension breakdown
    print("\nDimension Breakdown:")
    for dim_result in result.dimension_results:
        print(f"- {dim_result.dimension.value}: {dim_result.score:.1f}/100 "
              f"(Weight: {dim_result.weight:.2f})")
    
    # Generate comprehensive report
    markdown_report = ReportGenerator.generate_markdown_report(result, "ENTERPRISE")
    html_report = ReportGenerator.generate_html_report(result, "ENTERPRISE")
    
    print(f"\nMarkdown Report Length: {len(markdown_report)} characters")
    print(f"HTML Report Length: {len(html_report)} characters")
    
    # Auto-fix issues if enabled
    if config.auto_fix_enabled and result.all_issues:
        auto_fixable = [issue for issue in result.all_issues if issue.auto_fixable]
        if auto_fixable:
            fixed_content, fixed_issues = await engine.auto_fix_issues(content, auto_fixable)
            print(f"\nAuto-fixed {len(fixed_issues)} issues")
    
    # Performance statistics
    stats = engine.get_statistics()
    print(f"\nPerformance Statistics:")
    print(f"Cache Hit Rate: {stats['cache_hit_rate']*100:.1f}%")
    print(f"Reviews Performed: {stats['reviews_performed']}")
    
    await engine.cleanup()
    print()


async def custom_configuration_example():
    """Example: Custom dimension configuration."""
    print("=== Custom Configuration Example ===")
    
    # Custom dimension configuration
    config = ReviewEngineConfig(
        enabled_dimensions={
            ReviewDimension.TECHNICAL_ACCURACY,
            ReviewDimension.SECURITY_PII,
            ReviewDimension.COMPLETENESS
        },
        dimension_weights={
            ReviewDimension.TECHNICAL_ACCURACY: 0.5,
            ReviewDimension.SECURITY_PII: 0.3,
            ReviewDimension.COMPLETENESS: 0.2
        },
        approval_threshold=85.0,
        strict_mode=False
    )
    
    engine = ReviewEngine(
        mode=OperationMode.OPTIMIZED,
        config=config
    )
    
    content = """
    # Security Guidelines
    
    ## Password Requirements
    - Minimum 12 characters
    - Must include uppercase, lowercase, numbers
    - No common dictionary words
    
    ## API Security
    Always validate input parameters.
    
    TODO: Add rate limiting examples
    """
    
    result = await engine.review_document(
        content=content,
        document_type="security"
    )
    
    print(f"Custom Review - Score: {result.overall_score:.1f}/100")
    print(f"Enabled Dimensions: {len(result.dimension_results)}")
    for dim_result in result.dimension_results:
        print(f"- {dim_result.dimension.value}: {dim_result.score:.1f}/100")
    
    await engine.cleanup()
    print()


async def main():
    """Run all usage examples."""
    print("M007 Unified Review Engine - Usage Examples\n")
    
    await basic_usage_example()
    await optimized_usage_example()
    await secure_usage_example()
    await enterprise_usage_example()
    await custom_configuration_example()
    
    print("=== All Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())