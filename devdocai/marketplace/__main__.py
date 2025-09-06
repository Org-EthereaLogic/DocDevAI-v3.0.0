#!/usr/bin/env python3
"""
DevDocAI Template Marketplace CLI
Command-line interface for the Template Marketplace Client (M013).

Usage:
    python -m devdocai.marketplace [options]
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from .marketplace_client import TemplateMarketplaceClient


def print_info(client: TemplateMarketplaceClient):
    """Display marketplace client information."""
    print("\n" + "=" * 60)
    print("DevDocAI Template Marketplace Client - M013")
    print("=" * 60)
    print(f"Version: 3.0.0")
    print(f"Mode: {'Offline/Demo' if client.offline_mode else 'Online'}")
    print(f"Marketplace URL: {client.marketplace_url}")
    
    # Get cache info
    cache_info = client.get_cache_info()
    print(f"\nCache Information:")
    print(f"  Location: {cache_info['location']}")
    print(f"  Templates Cached: {cache_info['template_count']}")
    print(f"  Cache Size: {cache_info['size_mb']:.2f} MB")
    print(f"  Hit Rate: {cache_info['hit_rate']:.1%}")
    
    # Get stats
    stats = client.get_stats()
    print(f"\nStatistics:")
    print(f"  Templates Browsed: {stats['templates_browsed']}")
    print(f"  Templates Downloaded: {stats['templates_downloaded']}")
    print(f"  Templates Published: {stats['templates_published']}")
    print(f"  Signature Verifications: {stats['signature_verifications']}")
    print("=" * 60 + "\n")


def browse_templates(client: TemplateMarketplaceClient, args):
    """Browse available templates."""
    print(f"\nBrowsing templates (category: {args.category or 'all'})...")
    
    result = client.browse_templates(
        category=args.category,
        search=args.search,
        sort_by=args.sort_by or "popularity",
        page=args.page or 1,
        per_page=args.per_page or 10
    )
    
    if result.get("error"):
        print(f"Error: {result.get('message')}")
        return
    
    templates = result.get("templates", [])
    pagination = result.get("pagination", {})
    
    if not templates:
        print("No templates found.")
        return
    
    print(f"\nFound {pagination.get('total', len(templates))} templates:")
    print("-" * 60)
    
    for template in templates:
        print(f"\nID: {template['id']}")
        print(f"Name: {template['name']}")
        print(f"Version: {template['version']}")
        print(f"Category: {template['category']}")
        print(f"Description: {template['description']}")
        print(f"Author: {template.get('author', 'Unknown')}")
        print(f"Rating: {template.get('rating', 'N/A')}")
        print(f"Downloads: {template.get('downloads', 0)}")
        print(f"Tags: {', '.join(template.get('tags', []))}")
    
    if pagination.get("pages", 1) > 1:
        print(f"\nPage {pagination['page']} of {pagination['pages']}")


def search_templates(client: TemplateMarketplaceClient, query: str):
    """Search for templates."""
    print(f"\nSearching for: '{query}'...")
    
    result = client.search_templates(query)
    
    if result.get("error"):
        print(f"Error: {result.get('message')}")
        return
    
    templates = result.get("templates", [])
    
    if not templates:
        print("No templates found matching your search.")
        return
    
    print(f"\nFound {len(templates)} matching templates:")
    print("-" * 60)
    
    for template in templates:
        print(f"\nID: {template['id']}")
        print(f"Name: {template['name']}")
        print(f"Category: {template['category']}")
        print(f"Description: {template['description']}")
        print(f"Match Score: {template.get('score', 'N/A')}")


def download_template(client: TemplateMarketplaceClient, template_id: str):
    """Download a template."""
    print(f"\nDownloading template: {template_id}...")
    
    template_data, verified = client.download_template(template_id)
    
    if not template_data:
        print("Error: Failed to download template")
        return
    
    if template_data.get("error"):
        print(f"Error: {template_data.get('message')}")
        return
    
    print(f"Template downloaded successfully!")
    print(f"Signature Verified: {'✅ Yes' if verified else '❌ No'}")
    
    # Display template info
    print(f"\nTemplate Information:")
    print(f"  Name: {template_data.get('name')}")
    print(f"  Version: {template_data.get('version')}")
    print(f"  Category: {template_data.get('category')}")
    print(f"  Description: {template_data.get('description')}")
    
    # Show content preview
    content = template_data.get("content", {})
    if isinstance(content, dict):
        template_text = content.get("template_text", "")
        if template_text:
            lines = template_text.split('\n')[:5]
            print(f"\nContent Preview:")
            for line in lines:
                print(f"  {line}")
            if len(template_text.split('\n')) > 5:
                print("  ...")


def show_cache(client: TemplateMarketplaceClient):
    """Show local cache contents."""
    print("\nLocal Cache Contents:")
    print("-" * 60)
    
    cache_info = client.get_cache_info()
    print(f"Location: {cache_info['location']}")
    print(f"Templates: {cache_info['template_count']}")
    print(f"Metadata: {cache_info['metadata_count']}")
    print(f"Size: {cache_info['size_mb']:.2f} MB / {cache_info['max_size_mb']:.0f} MB")
    print(f"Hit Rate: {cache_info['hit_rate']:.1%}")
    print(f"Expiration: {cache_info['expiration_days']:.0f} days")
    
    # List cached templates
    result = client.local_cache.browse_cached_templates(per_page=100)
    templates = result.get("templates", [])
    
    if templates:
        print(f"\nCached Templates ({len(templates)}):")
        for template in templates:
            print(f"  - {template['id']} (v{template.get('version', '?')}): {template.get('name', 'Unknown')}")
    else:
        print("\nNo templates in cache.")


def template_info(client: TemplateMarketplaceClient, template_id: str):
    """Show detailed template information."""
    print(f"\nFetching information for: {template_id}...")
    
    info = client.get_template_info(template_id)
    
    if not info:
        print("Error: Template not found")
        return
    
    print(f"\nTemplate Details:")
    print("-" * 60)
    print(json.dumps(info, indent=2, default=str))


def publish_template(client: TemplateMarketplaceClient, template_path: str, demo: bool):
    """Publish a template to the marketplace."""
    print(f"\nPublishing template from: {template_path}")
    
    if demo:
        # Create demo template
        template = {
            "name": "Demo Template",
            "version": "1.0.0",
            "description": "This is a demo template for testing the publish functionality",
            "category": "documentation",
            "content": {
                "template_text": "# {{title}}\n\n{{description}}\n\n## Installation\n\n{{installation}}\n\n## Usage\n\n{{usage}}",
                "sections": ["Introduction", "Installation", "Usage"]
            },
            "tags": ["demo", "test", "documentation"],
            "author": "DevDocAI Demo"
        }
        print("\nUsing demo template (--demo flag set)")
    else:
        # Load template from file
        template_file = Path(template_path)
        if not template_file.exists():
            print(f"Error: Template file not found: {template_path}")
            return
        
        try:
            with open(template_file, 'r') as f:
                if template_file.suffix in ['.yaml', '.yml']:
                    import yaml
                    template = yaml.safe_load(f)
                else:
                    template = json.load(f)
        except Exception as e:
            print(f"Error loading template: {e}")
            return
    
    # Publish
    success, result = client.publish_template(template)
    
    if success:
        print(f"\n✅ Template published successfully!")
        print(f"Template ID: {result}")
        print(f"Status: Published to marketplace")
    else:
        print(f"\n❌ Failed to publish template")
        print(f"Error: {result}")


def clear_cache(client: TemplateMarketplaceClient):
    """Clear the local cache."""
    print("\nClearing local cache...")
    
    if client.clear_cache():
        print("✅ Cache cleared successfully")
    else:
        print("❌ Failed to clear cache")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="DevDocAI Template Marketplace Client - M013",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m devdocai.marketplace --info
  python -m devdocai.marketplace --browse --category api
  python -m devdocai.marketplace --search "REST API"
  python -m devdocai.marketplace --download --template-id api-docs-v1.0
  python -m devdocai.marketplace --cache --list
  python -m devdocai.marketplace --publish --template ./my-template.yaml
        """
    )
    
    # Mode options
    parser.add_argument("--offline", action="store_true",
                       help="Run in offline/demo mode")
    
    # Actions
    parser.add_argument("--info", action="store_true",
                       help="Show marketplace client information")
    
    parser.add_argument("--browse", action="store_true",
                       help="Browse available templates")
    
    parser.add_argument("--search", type=str, metavar="QUERY",
                       help="Search for templates")
    
    parser.add_argument("--download", action="store_true",
                       help="Download a template")
    
    parser.add_argument("--cache", action="store_true",
                       help="Cache operations")
    
    parser.add_argument("--template-info", action="store_true",
                       help="Show template information")
    
    parser.add_argument("--publish", action="store_true",
                       help="Publish a template")
    
    # Browse options
    parser.add_argument("--category", type=str,
                       choices=["documentation", "api", "readme", "tutorial",
                               "guide", "specification", "architecture", "other"],
                       help="Filter by category")
    
    parser.add_argument("--sort-by", type=str,
                       choices=["popularity", "recent", "rating"],
                       help="Sort criteria")
    
    parser.add_argument("--page", type=int, default=1,
                       help="Page number")
    
    parser.add_argument("--per-page", type=int, default=10,
                       help="Items per page")
    
    # Download/Info options
    parser.add_argument("--template-id", "--id", type=str,
                       help="Template ID")
    
    # Cache options
    parser.add_argument("--list", action="store_true",
                       help="List cached templates")
    
    parser.add_argument("--clear", action="store_true",
                       help="Clear cache")
    
    # Publish options
    parser.add_argument("--template", type=str,
                       help="Path to template file")
    
    parser.add_argument("--demo", action="store_true",
                       help="Use demo template for testing")
    
    args = parser.parse_args()
    
    # Initialize client (default to demo mode if not specified)
    client = TemplateMarketplaceClient(offline_mode=True if args.offline else False)
    
    # Execute requested action
    if args.info:
        print_info(client)
    
    elif args.browse:
        browse_templates(client, args)
    
    elif args.search:
        search_templates(client, args.search)
    
    elif args.download:
        if not args.template_id:
            print("Error: --template-id required for download")
            sys.exit(1)
        download_template(client, args.template_id)
    
    elif args.cache:
        if args.clear:
            clear_cache(client)
        else:
            show_cache(client)
    
    elif args.template_info:
        if not args.template_id:
            print("Error: --template-id required")
            sys.exit(1)
        template_info(client, args.template_id)
    
    elif args.publish:
        if not args.template and not args.demo:
            print("Error: --template or --demo required for publish")
            sys.exit(1)
        publish_template(client, args.template or "", args.demo)
    
    else:
        # Default action: show info
        print_info(client)


if __name__ == "__main__":
    main()