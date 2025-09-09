"""
Performance Comparison Test - Original vs Optimized Storage
Measures improvement between Pass 1 and Pass 2 implementations
"""

import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from devdocai.core.config import ConfigurationManager
from devdocai.core.storage import Document
from devdocai.core.storage import StorageManager as OriginalStorage
from devdocai.core.storage_optimized import StorageManager as OptimizedStorage


class PerformanceComparison:
    """Compare performance between original and optimized implementations."""

    def __init__(self):
        self.results = {"original": {}, "optimized": {}}

    def create_test_config(self, db_path: str, encryption: bool = False) -> ConfigurationManager:
        """Create test configuration."""
        config = ConfigurationManager()
        config.config = {
            "storage": {
                "database_path": db_path,
                "encryption_enabled": encryption,
                "encryption_key": "test_key" if encryption else None,
                "cache_size": 10000,
                "pool_size": 10,
            }
        }
        return config

    def generate_documents(self, count: int, size: int = 100) -> List[Document]:
        """Generate test documents."""
        docs = []
        for i in range(count):
            doc = Document(
                id=f"doc_{i:06d}",
                content="x" * size,
                type="test",
                metadata={"author": f"author_{i % 10}", "tags": [f"tag_{i % 5}"]},
            )
            docs.append(doc)
        return docs

    def benchmark_operation(self, operation, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark a single operation."""
        timings = []

        for _ in range(iterations):
            start = time.perf_counter()
            operation()
            end = time.perf_counter()
            timings.append(end - start)

        return {
            "mean": statistics.mean(timings),
            "median": statistics.median(timings),
            "stdev": statistics.stdev(timings) if len(timings) > 1 else 0,
            "min": min(timings),
            "max": max(timings),
            "ops_per_sec": 1 / statistics.mean(timings) if statistics.mean(timings) > 0 else 0,
        }

    def run_read_benchmark(self, storage, doc_ids: List[str], name: str):
        """Run read performance benchmark."""
        print(f"\n🔍 Benchmarking {name} READ performance...")

        def read_op():
            doc_id = doc_ids[read_op.counter % len(doc_ids)]
            doc = storage.get_document(doc_id)
            assert doc is not None
            read_op.counter += 1

        read_op.counter = 0

        stats = self.benchmark_operation(read_op, iterations=10000)

        print(f"  Mean latency: {stats['mean']*1000:.3f} ms")
        print(f"  Operations/sec: {stats['ops_per_sec']:,.0f}")

        return stats

    def run_write_benchmark(self, storage, name: str, start_id: int = 100000):
        """Run write performance benchmark."""
        print(f"\n✍️  Benchmarking {name} WRITE performance...")

        def write_op():
            doc = Document(
                id=f"doc_{start_id + write_op.counter:06d}", content="x" * 100, type="test"
            )
            storage.save_document(doc)
            write_op.counter += 1

        write_op.counter = 0

        stats = self.benchmark_operation(write_op, iterations=1000)

        print(f"  Mean latency: {stats['mean']*1000:.3f} ms")
        print(f"  Operations/sec: {stats['ops_per_sec']:,.0f}")

        return stats

    def run_exists_benchmark(self, storage, doc_ids: List[str], name: str):
        """Run existence check benchmark."""
        print(f"\n✅ Benchmarking {name} EXISTS performance...")

        def exists_op():
            doc_id = doc_ids[exists_op.counter % len(doc_ids)]
            exists = storage.document_exists(doc_id)
            assert exists
            exists_op.counter += 1

        exists_op.counter = 0

        stats = self.benchmark_operation(exists_op, iterations=10000)

        print(f"  Mean latency: {stats['mean']*1000:.3f} ms")
        print(f"  Operations/sec: {stats['ops_per_sec']:,.0f}")

        return stats

    def run_bulk_benchmark(self, storage, name: str, start_id: int = 200000):
        """Run bulk operations benchmark."""
        print(f"\n📦 Benchmarking {name} BULK performance...")

        # Test bulk save
        batch_size = 100
        docs = []
        for i in range(batch_size):
            docs.append(Document(id=f"doc_{start_id + i:06d}", content="x" * 100, type="test"))

        start = time.perf_counter()
        results = storage.bulk_save(docs)
        end = time.perf_counter()

        assert all(results.values())
        bulk_save_time = end - start
        bulk_save_ops = batch_size / bulk_save_time

        print(f"  Bulk save ({batch_size} docs): {bulk_save_time*1000:.2f} ms")
        print(f"  Operations/sec: {bulk_save_ops:,.0f}")

        # Test bulk get (if available)
        if hasattr(storage, "bulk_get"):
            doc_ids = [f"doc_{start_id + i:06d}" for i in range(batch_size)]

            start = time.perf_counter()
            docs = storage.bulk_get(doc_ids)
            end = time.perf_counter()

            bulk_get_time = end - start
            bulk_get_ops = batch_size / bulk_get_time

            print(f"  Bulk get ({batch_size} docs): {bulk_get_time*1000:.2f} ms")
            print(f"  Operations/sec: {bulk_get_ops:,.0f}")

            return {"bulk_save_ops": bulk_save_ops, "bulk_get_ops": bulk_get_ops}

        return {"bulk_save_ops": bulk_save_ops}

    def compare_implementations(self):
        """Run full comparison between original and optimized."""
        print("\n" + "=" * 80)
        print("STORAGE PERFORMANCE COMPARISON")
        print("Original (Pass 1) vs Optimized (Pass 2)")
        print("=" * 80)

        # Create temporary databases
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            original_db = f.name
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            optimized_db = f.name

        try:
            # Test 1: In-memory, no encryption (baseline)
            print("\n" + "=" * 60)
            print("TEST 1: IN-MEMORY DATABASE (NO ENCRYPTION)")
            print("=" * 60)

            config_orig = self.create_test_config(":memory:", encryption=False)
            config_opt = self.create_test_config(":memory:", encryption=False)

            original = OriginalStorage(config_orig)
            optimized = OptimizedStorage(config_opt)

            # Prepare test data
            print("\nPreparing test data...")
            docs = self.generate_documents(1000)
            doc_ids = []

            for doc in docs:
                original.save_document(doc)
                optimized.save_document(doc)
                doc_ids.append(doc.id)

            # Run benchmarks
            orig_read = self.run_read_benchmark(original, doc_ids, "Original")
            opt_read = self.run_read_benchmark(optimized, doc_ids, "Optimized")

            orig_write = self.run_write_benchmark(original, "Original")
            opt_write = self.run_write_benchmark(optimized, "Optimized")

            orig_exists = self.run_exists_benchmark(original, doc_ids, "Original")
            opt_exists = self.run_exists_benchmark(optimized, doc_ids, "Optimized")

            orig_bulk = self.run_bulk_benchmark(original, "Original")
            opt_bulk = self.run_bulk_benchmark(optimized, "Optimized")

            # Test 2: File-based with encryption
            print("\n" + "=" * 60)
            print("TEST 2: FILE DATABASE WITH ENCRYPTION")
            print("=" * 60)

            config_orig_enc = self.create_test_config(original_db, encryption=True)
            config_opt_enc = self.create_test_config(optimized_db, encryption=True)

            original_enc = OriginalStorage(config_orig_enc)
            optimized_enc = OptimizedStorage(config_opt_enc)

            # Prepare encrypted test data
            print("\nPreparing encrypted test data...")
            for doc in docs[:100]:  # Use fewer docs for encrypted test
                original_enc.save_document(doc)
                optimized_enc.save_document(doc)

            # Run encrypted benchmarks
            orig_enc_read = self.run_read_benchmark(
                original_enc, doc_ids[:100], "Original (Encrypted)"
            )
            opt_enc_read = self.run_read_benchmark(
                optimized_enc, doc_ids[:100], "Optimized (Encrypted)"
            )

            # Print summary
            print("\n" + "=" * 80)
            print("PERFORMANCE SUMMARY")
            print("=" * 80)

            print("\n📊 READ PERFORMANCE (ops/sec):")
            print(f"  Original (no encryption):  {orig_read['ops_per_sec']:>12,.0f}")
            print(f"  Optimized (no encryption): {opt_read['ops_per_sec']:>12,.0f}")
            improvement = (opt_read["ops_per_sec"] / orig_read["ops_per_sec"] - 1) * 100
            print(f"  Improvement:                {improvement:>11.1f}%")

            print(f"\n  Original (encrypted):      {orig_enc_read['ops_per_sec']:>12,.0f}")
            print(f"  Optimized (encrypted):     {opt_enc_read['ops_per_sec']:>12,.0f}")
            enc_improvement = (opt_enc_read["ops_per_sec"] / orig_enc_read["ops_per_sec"] - 1) * 100
            print(f"  Improvement:                {enc_improvement:>11.1f}%")

            print("\n📊 WRITE PERFORMANCE (ops/sec):")
            print(f"  Original:                  {orig_write['ops_per_sec']:>12,.0f}")
            print(f"  Optimized:                 {opt_write['ops_per_sec']:>12,.0f}")
            write_improvement = (opt_write["ops_per_sec"] / orig_write["ops_per_sec"] - 1) * 100
            print(f"  Improvement:                {write_improvement:>11.1f}%")

            print("\n📊 EXISTS CHECK PERFORMANCE (ops/sec):")
            print(f"  Original:                  {orig_exists['ops_per_sec']:>12,.0f}")
            print(f"  Optimized:                 {opt_exists['ops_per_sec']:>12,.0f}")
            exists_improvement = (opt_exists["ops_per_sec"] / orig_exists["ops_per_sec"] - 1) * 100
            print(f"  Improvement:                {exists_improvement:>11.1f}%")

            print("\n📊 BULK SAVE PERFORMANCE (ops/sec):")
            print(f"  Original:                  {orig_bulk['bulk_save_ops']:>12,.0f}")
            print(f"  Optimized:                 {opt_bulk['bulk_save_ops']:>12,.0f}")
            bulk_improvement = (opt_bulk["bulk_save_ops"] / orig_bulk["bulk_save_ops"] - 1) * 100
            print(f"  Improvement:                {bulk_improvement:>11.1f}%")

            # Check if target is met
            print("\n" + "=" * 80)
            print("TARGET ASSESSMENT")
            print("=" * 80)

            target = 200_000
            best_performance = opt_read["ops_per_sec"]

            if best_performance >= target:
                print(f"✅ TARGET ACHIEVED: {best_performance:,.0f} ops/sec >= {target:,} ops/sec")
            else:
                print(f"❌ TARGET NOT MET: {best_performance:,.0f} ops/sec < {target:,} ops/sec")
                print(f"   Gap: {target - best_performance:,.0f} ops/sec")
                print(f"   Need {(target / best_performance):.1f}x more performance")

            # Test cache effectiveness
            if hasattr(optimized, "_cache"):
                cache_stats = optimized._cache.get_stats()
                print("\n📊 CACHE STATISTICS:")
                print(f"  Cache size: {cache_stats['size']}/{cache_stats['max_size']}")
                print(f"  Cache hits: {cache_stats['hits']:,}")
                print(f"  Cache misses: {cache_stats['misses']:,}")
                print(f"  Hit rate: {cache_stats['hit_rate']*100:.1f}%")

            print("\n" + "=" * 80)

        finally:
            # Cleanup
            if os.path.exists(original_db):
                os.unlink(original_db)
            if os.path.exists(optimized_db):
                os.unlink(optimized_db)


def main():
    """Run performance comparison."""
    comparison = PerformanceComparison()
    comparison.compare_implementations()


if __name__ == "__main__":
    main()
