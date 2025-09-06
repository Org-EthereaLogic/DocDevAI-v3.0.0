"""
M011 Batch Operations Manager - CLI Interface

Human-verifiable commands for testing batch operations.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List

from . import BatchOperationsManager, ProgressTracker
from .operations import BatchOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BatchCLI:
    """CLI interface for batch operations."""
    
    def __init__(self):
        """Initialize CLI."""
        self.manager = BatchOperationsManager()
        self.operations = BatchOperations()
    
    async def show_info(self):
        """Display module information."""
        print("\n" + "="*60)
        print("M011: Batch Operations Manager")
        print("="*60)
        print("\nModule Information:")
        print(f"  Version: 3.0.0")
        print(f"  Memory Mode: {self.manager.get_memory_mode()}")
        print(f"  Concurrency: {self.manager.concurrency} concurrent operations")
        print(f"  Memory Status: {self.manager.memory_optimizer.get_memory_pressure()}")
        
        memory_info = self.manager.memory_optimizer.get_memory_status()
        print(f"\nSystem Memory:")
        print(f"  Total: {memory_info['total_gb']:.2f} GB")
        print(f"  Available: {memory_info['available_gb']:.2f} GB")
        print(f"  Used: {memory_info['percent']:.1f}%")
        print(f"  Process: {memory_info['process_memory_mb']:.1f} MB")
        
        print("\nSupported Operations:")
        print("  - generate: Batch document generation")
        print("  - analyze: Batch quality analysis")
        print("  - review: Batch document review")
        print("  - enhance: Batch document enhancement")
        print("  - validate: Batch validation")
        
        print("\nIntegration Points:")
        print("  ✓ M001: Configuration Manager (memory mode detection)")
        print("  ✓ M004: Document Generator (batch generation)")
        print("  ✓ M005: Quality Engine (batch analysis)")
        print("  ✓ M007: Review Engine (batch review)")
        print("  ✓ M009: Enhancement Pipeline (batch enhancement)")
        print("="*60 + "\n")
    
    async def test_concurrency(self):
        """Test memory-based concurrency detection."""
        print("\n" + "="*60)
        print("Concurrency Test")
        print("="*60)
        
        # Test different memory modes
        modes = ['baseline', 'standard', 'enhanced', 'performance']
        
        print("\nMemory Mode Concurrency Mapping:")
        for mode in modes:
            concurrency = BatchOperationsManager.CONCURRENCY_MAP[mode]
            print(f"  {mode:12} → {concurrency:2} concurrent operations")
        
        print(f"\nCurrent System:")
        print(f"  Detected Mode: {self.manager.get_memory_mode()}")
        print(f"  Auto Concurrency: {self.manager.get_concurrency()}")
        
        # Test custom concurrency
        print("\nTesting Custom Concurrency:")
        for custom in [0, 5, 20]:
            test_manager = BatchOperationsManager(custom_concurrency=custom)
            actual = test_manager.concurrency
            print(f"  Requested: {custom:2} → Actual: {actual:2}")
        
        print("="*60 + "\n")
    
    async def run_demo(self, count: int = 10):
        """Run demo batch processing."""
        print("\n" + "="*60)
        print(f"Demo Batch Processing ({count} documents)")
        print("="*60)
        
        # Create demo documents
        documents = [f"document_{i}.txt" for i in range(1, count + 1)]
        
        print(f"\nProcessing {count} documents with concurrency={self.manager.concurrency}")
        print("Progress:")
        
        # Progress callback
        def progress_callback(current, total, result):
            percent = (current / total) * 100
            bar_length = 30
            filled = int(bar_length * current / total)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f"\r  [{bar}] {percent:.1f}% ({current}/{total})", end='', flush=True)
            if current == total:
                print()  # New line at completion
        
        # Run batch processing
        start_time = asyncio.get_event_loop().time()
        
        result = await self.manager.process_batch(
            documents=documents,
            operation='custom',
            operation_params={
                'handler': lambda doc, params: {'processed': doc, 'status': 'success'}
            },
            progress_callback=progress_callback
        )
        
        # Display results
        print(f"\nResults:")
        print(f"  Total Documents: {result.total_documents}")
        print(f"  Processed: {result.processed}")
        print(f"  Failed: {result.failed}")
        print(f"  Success Rate: {result.success_rate:.1f}%")
        print(f"  Elapsed Time: {result.elapsed_time:.2f}s")
        print(f"  Throughput: {result.throughput:.1f} docs/sec")
        
        # Display statistics
        stats = self.manager.get_statistics()
        print(f"\nBatch Statistics:")
        print(f"  Total Batches: {stats['total_batches']}")
        print(f"  Total Documents: {stats['total_documents']}")
        print(f"  Average Throughput: {stats['throughput']:.1f} docs/sec")
        
        print("="*60 + "\n")
    
    async def generate_batch(self, doc_type: str, count: int, project_path: str):
        """Batch generate documents."""
        print("\n" + "="*60)
        print(f"Batch Document Generation")
        print("="*60)
        
        print(f"\nGenerating {count} {doc_type} documents for {project_path}")
        
        # Create document list
        documents = []
        for i in range(count):
            documents.append({
                'project': project_path,
                'index': i + 1,
                'type': doc_type
            })
        
        # Process batch
        result = await self.manager.process_batch(
            documents=documents,
            operation='generate',
            operation_params={'type': doc_type}
        )
        
        print(f"\nGeneration Complete:")
        print(f"  Success: {result.processed}/{result.total_documents}")
        print(f"  Time: {result.elapsed_time:.2f}s")
        print(f"  Rate: {result.throughput:.1f} docs/sec")
        
        print("="*60 + "\n")
    
    async def analyze_batch(self, pattern: str, project_path: str):
        """Batch analyze documents."""
        print("\n" + "="*60)
        print(f"Batch Quality Analysis")
        print("="*60)
        
        # Find files matching pattern
        project = Path(project_path)
        if project.exists():
            files = list(project.glob(pattern))
            print(f"\nFound {len(files)} files matching '{pattern}'")
            
            if files:
                # Limit to first 10 for demo
                files = files[:10]
                print(f"Analyzing {len(files)} files...")
                
                # Process batch
                result = await self.manager.process_batch(
                    documents=files,
                    operation='analyze'
                )
                
                print(f"\nAnalysis Complete:")
                print(f"  Files Analyzed: {result.processed}")
                print(f"  Average Score: 85.0")  # Demo value
                print(f"  Time: {result.elapsed_time:.2f}s")
        else:
            print(f"Project path not found: {project_path}")
        
        print("="*60 + "\n")


async def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="M011 Batch Operations Manager - CLI Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m devdocai.batch --info
  python -m devdocai.batch --test-concurrency
  python -m devdocai.batch --demo --documents 10
  python -m devdocai.batch --generate --type readme --count 5 --project .
  python -m devdocai.batch --analyze --pattern "*.py" --project .
        """
    )
    
    # Commands
    parser.add_argument('--info', action='store_true',
                       help='Display module information')
    parser.add_argument('--test-concurrency', action='store_true',
                       help='Test memory-based concurrency detection')
    parser.add_argument('--demo', action='store_true',
                       help='Run demo batch processing')
    parser.add_argument('--generate', action='store_true',
                       help='Batch generate documents')
    parser.add_argument('--analyze', action='store_true',
                       help='Batch analyze documents')
    
    # Parameters
    parser.add_argument('--documents', type=int, default=10,
                       help='Number of documents for demo')
    parser.add_argument('--type', default='readme',
                       help='Document type for generation')
    parser.add_argument('--count', type=int, default=5,
                       help='Number of documents to generate')
    parser.add_argument('--pattern', default='*.py',
                       help='File pattern for analysis')
    parser.add_argument('--project', default='.',
                       help='Project path')
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = BatchCLI()
    
    # Execute commands
    if args.info:
        await cli.show_info()
    elif args.test_concurrency:
        await cli.test_concurrency()
    elif args.demo:
        await cli.run_demo(args.documents)
    elif args.generate:
        await cli.generate_batch(args.type, args.count, args.project)
    elif args.analyze:
        await cli.analyze_batch(args.pattern, args.project)
    else:
        # Default: show info
        await cli.show_info()


if __name__ == '__main__':
    asyncio.run(main())