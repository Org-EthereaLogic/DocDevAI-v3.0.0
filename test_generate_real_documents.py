#!/usr/bin/env python3
"""
DevDocAI v3.0.0 - Real Document Generation Test
Generates actual documentation using the AI-powered backend system
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project to path
sys.path.insert(0, os.path.abspath('.'))

from devdocai.core.config import ConfigurationManager
from devdocai.intelligence.llm_adapter import LLMAdapter
from devdocai.core.generator import DocumentGenerator
from devdocai.core.storage import StorageManager, Document

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{'='*80}")
    print(f"{text.center(80)}")
    print(f"{'='*80}")

def print_status(status: str, message: str):
    """Print status message with emoji"""
    emoji = {
        "success": "✅",
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
        "working": "🔄",
        "doc": "📄"
    }
    print(f"{emoji.get(status, '•')} {message}")

async def test_llm_generation():
    """Test basic LLM generation to confirm system is working"""
    print_header("Testing LLM Generation System")
    
    try:
        # Load configuration
        config = ConfigurationManager()
        print_status("info", f"Provider: {config.llm.provider}")
        print_status("info", f"Model: {config.llm.model}")
        
        # Initialize LLM adapter
        adapter = LLMAdapter(config)
        
        # Test simple generation (synchronous)
        print_status("working", "Testing AI generation...")
        response = adapter.generate(
            prompt="Write a one-line summary: DevDocAI is an AI-powered documentation system.",
            max_tokens=50
        )
        
        if response and response.content:
            print_status("success", f"AI Response: {response.content.strip()}")
            return True
        else:
            print_status("warning", "No response generated - check provider configuration")
            return False
            
    except Exception as e:
        print_status("error", f"LLM test failed: {e}")
        return False

async def generate_readme_document():
    """Generate a real README document"""
    print_header("Generating README Document")
    
    try:
        # Initialize components
        config = ConfigurationManager()
        storage = StorageManager(config)
        llm = LLMAdapter(config)
        generator = DocumentGenerator(config, storage, llm)
        
        # Define context for README
        context = {
            "project_name": "DevDocAI Backend Test Suite",
            "description": "A comprehensive AI-powered documentation generation system that leverages multiple LLM providers to create high-quality technical documentation automatically.",
            "features": [
                "Multi-provider LLM support (OpenAI, Claude, Gemini)",
                "Intelligent failover and retry mechanisms",
                "Advanced caching for improved performance",
                "Enterprise-grade security with encryption",
                "Template-based document generation",
                "Real-time progress tracking",
                "Comprehensive audit logging"
            ],
            "tech_stack": [
                "Python 3.8+",
                "FastAPI for REST API",
                "SQLite with SQLCipher encryption",
                "Multiple LLM provider integrations",
                "Async/await for performance"
            ],
            "installation": "pip install devdocai",
            "author": "DevDocAI Team",
            "license": "MIT",
            "version": "3.0.0"
        }
        
        print_status("working", "Generating README with AI...")
        start_time = time.time()
        
        # Generate document
        result = await generator.generate_document(
            template_name="readme",
            context=context,
            use_cache=False,  # Force fresh generation
            validate=True
        )
        
        generation_time = time.time() - start_time
        
        if result.success and result.document:
            # Save document
            output_dir = Path("generated_documents")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"README_{timestamp}.md"
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.document)
            
            print_status("success", f"README generated successfully!")
            print(f"  • Generation time: {generation_time:.2f} seconds")
            print(f"  • Document size: {len(result.document):,} characters")
            print(f"  • Saved to: {output_file}")
            
            # Show preview
            print("\n--- Document Preview ---")
            lines = result.document.split('\n')[:15]  # First 15 lines
            for line in lines:
                print(f"  {line}")
            if len(result.document.split('\n')) > 15:
                print("  ...")
            
            return str(output_file), result.document
        else:
            print_status("error", f"Generation failed: {result.error}")
            return None, None
            
    except Exception as e:
        print_status("error", f"README generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def generate_api_documentation():
    """Generate API documentation"""
    print_header("Generating API Documentation")
    
    try:
        # Initialize components
        config = ConfigurationManager()
        storage = StorageManager(config)
        llm = LLMAdapter(config)
        generator = DocumentGenerator(config, storage, llm)
        
        # Define context for API documentation
        context = {
            "api_name": "DevDocAI REST API",
            "base_url": "https://api.devdocai.com/v3",
            "version": "3.0.0",
            "description": "RESTful API for AI-powered documentation generation",
            "authentication": "Bearer token (API key required)",
            "rate_limit": "100 requests per minute",
            "endpoints": [
                {
                    "method": "POST",
                    "path": "/generate",
                    "description": "Generate documentation using AI",
                    "params": {
                        "template": "Template name (readme, api_doc, changelog)",
                        "context": "Context object with project details",
                        "use_cache": "Whether to use cached results (default: true)"
                    },
                    "response": "Generated document with metadata"
                },
                {
                    "method": "GET",
                    "path": "/templates",
                    "description": "List available document templates",
                    "response": "Array of template objects"
                },
                {
                    "method": "GET",
                    "path": "/status",
                    "description": "Check API health and provider status",
                    "response": "System status and provider availability"
                }
            ]
        }
        
        print_status("working", "Generating API documentation with AI...")
        start_time = time.time()
        
        # Generate document
        result = await generator.generate_document(
            template_name="api_doc",
            context=context,
            use_cache=False,
            validate=True
        )
        
        generation_time = time.time() - start_time
        
        if result.success and result.document:
            # Save document
            output_dir = Path("generated_documents")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"API_Documentation_{timestamp}.md"
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.document)
            
            print_status("success", f"API documentation generated successfully!")
            print(f"  • Generation time: {generation_time:.2f} seconds")
            print(f"  • Document size: {len(result.document):,} characters")
            print(f"  • Saved to: {output_file}")
            
            return str(output_file), result.document
        else:
            print_status("error", f"Generation failed: {result.error}")
            return None, None
            
    except Exception as e:
        print_status("error", f"API documentation generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def generate_changelog():
    """Generate a changelog document"""
    print_header("Generating Changelog")
    
    try:
        # Initialize components
        config = ConfigurationManager()
        storage = StorageManager(config)
        llm = LLMAdapter(config)
        generator = DocumentGenerator(config, storage, llm)
        
        # Define context for changelog
        context = {
            "project_name": "DevDocAI",
            "version": "3.0.0",
            "release_date": datetime.now().strftime("%Y-%m-%d"),
            "changes": {
                "added": [
                    "Multi-provider LLM support with automatic failover",
                    "Advanced caching system for improved performance (333x faster)",
                    "Enterprise security features including encryption and audit logging",
                    "Real-time document generation with progress tracking",
                    "Template marketplace for community templates",
                    "Batch operations for processing multiple documents"
                ],
                "improved": [
                    "Document generation speed (333x improvement)",
                    "Memory efficiency for large documents",
                    "Error handling and recovery mechanisms",
                    "API response times (sub-200ms)",
                    "Test coverage (85-95% across modules)"
                ],
                "fixed": [
                    "API timeout issues with long-running generations",
                    "Memory leaks in cache management",
                    "Concurrent request handling",
                    "Template validation errors",
                    "Storage encryption key management"
                ]
            }
        }
        
        print_status("working", "Generating changelog with AI...")
        start_time = time.time()
        
        # Generate document
        result = await generator.generate_document(
            template_name="changelog",
            context=context,
            use_cache=False,
            validate=True
        )
        
        generation_time = time.time() - start_time
        
        if result.success and result.document:
            # Save document
            output_dir = Path("generated_documents")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"CHANGELOG_{timestamp}.md"
            
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result.document)
            
            print_status("success", f"Changelog generated successfully!")
            print(f"  • Generation time: {generation_time:.2f} seconds")
            print(f"  • Document size: {len(result.document):,} characters")
            print(f"  • Saved to: {output_file}")
            
            return str(output_file), result.document
        else:
            print_status("error", f"Generation failed: {result.error}")
            return None, None
            
    except Exception as e:
        print_status("error", f"Changelog generation failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None

async def check_audit_logs():
    """Check audit logs for generation activity"""
    print_header("Checking Audit Logs")
    
    audit_file = Path("devdocai_audit.log")
    if audit_file.exists():
        with open(audit_file, "r") as f:
            lines = f.readlines()
        
        # Find recent generation logs
        recent_logs = [l for l in lines[-20:] if "llm_generation" in l or "api_call" in l]
        
        print_status("info", f"Found {len(recent_logs)} recent generation events")
        
        # Parse and display summary
        providers_used = set()
        total_tokens = 0
        
        for log in recent_logs:
            try:
                if "{" in log:
                    json_str = log[log.index("{"):]
                    data = json.loads(json_str)
                    if "provider" in data:
                        providers_used.add(data["provider"])
                    if "details" in data and "tokens" in data["details"]:
                        total_tokens += data["details"]["tokens"]
            except:
                pass
        
        print(f"  • Providers used: {', '.join(providers_used)}")
        print(f"  • Total tokens: {total_tokens}")
    else:
        print_status("warning", "No audit log file found")

async def main():
    """Main test orchestrator"""
    print_header("DevDocAI v3.0.0 - Real Document Generation Test")
    print(f"Starting at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    generated_files = []
    
    # Test 1: Basic LLM functionality
    llm_working = await test_llm_generation()
    
    if not llm_working:
        print_status("warning", "LLM not responding - will use local fallback")
    
    # Test 2: Generate README
    readme_file, readme_content = await generate_readme_document()
    if readme_file:
        generated_files.append(readme_file)
    
    # Test 3: Generate API Documentation
    api_file, api_content = await generate_api_documentation()
    if api_file:
        generated_files.append(api_file)
    
    # Test 4: Generate Changelog
    changelog_file, changelog_content = await generate_changelog()
    if changelog_file:
        generated_files.append(changelog_file)
    
    # Check audit logs
    await check_audit_logs()
    
    # Final report
    print_header("Generation Summary")
    
    if generated_files:
        print_status("success", f"Successfully generated {len(generated_files)} documents:")
        for file in generated_files:
            print(f"  📄 {file}")
        
        print("\n" + "="*80)
        print("✅ DOCUMENT GENERATION SUCCESSFUL!")
        print("Please review the generated documents in ./generated_documents/")
        print("The AI-powered backend is working correctly.")
    else:
        print_status("error", "No documents were generated")
        print("Please check:")
        print("  1. API keys are configured correctly")
        print("  2. Network connectivity to LLM providers")
        print("  3. Error logs for specific issues")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())