#!/usr/bin/env python3
"""
M010 Security Module - Performance Benchmark Suite

Establishes baseline performance metrics and validates optimization improvements.
Targets:
- SBOM Generation: <30ms (70% improvement)
- PII Detection: <20ms (60% improvement) 
- Threat Detection: <5ms (50% improvement)
- DSR Processing: <500ms (50% improvement)
- Compliance Assessment: <1000ms
"""

import time
import json
import random
import string
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import statistics
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

# Import security components
from devdocai.security.security_manager import SecurityManager
from devdocai.security.sbom.generator import SBOMGenerator
from devdocai.security.pii.detector_advanced import AdvancedPIIDetector
from devdocai.security.dsr.request_handler import DSRHandler
from devdocai.security.monitoring.threat_detector import ThreatDetector
from devdocai.security.audit.compliance_reporter import ComplianceReporter


@dataclass
class BenchmarkResult:
    """Stores benchmark results for a single operation"""
    operation: str
    baseline_ms: float
    optimized_ms: float = 0.0
    improvement_pct: float = 0.0
    iterations: int = 100
    std_dev: float = 0.0
    memory_mb: float = 0.0
    throughput: float = 0.0
    
    def calculate_improvement(self):
        """Calculate improvement percentage"""
        if self.baseline_ms > 0 and self.optimized_ms > 0:
            self.improvement_pct = ((self.baseline_ms - self.optimized_ms) / self.baseline_ms) * 100


class M010BenchmarkSuite:
    """Comprehensive benchmark suite for M010 Security Module"""
    
    def __init__(self):
        self.results: Dict[str, BenchmarkResult] = {}
        self.security_manager = SecurityManager()
        self.sbom_generator = SBOMGenerator()
        self.pii_detector = AdvancedPIIDetector()
        self.dsr_handler = DSRHandler()
        self.threat_detector = ThreatDetector()
        self.compliance_reporter = ComplianceReporter()
        
    def _measure_time(self, func, *args, iterations: int = 100, **kwargs) -> Tuple[float, float]:
        """Measure execution time with multiple iterations"""
        times = []
        for _ in range(iterations):
            start = time.perf_counter()
            func(*args, **kwargs)
            end = time.perf_counter()
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = statistics.mean(times)
        std_dev = statistics.stdev(times) if len(times) > 1 else 0
        return avg_time, std_dev
    
    def _measure_memory(self, func, *args, **kwargs) -> float:
        """Measure memory usage of a function"""
        import tracemalloc
        tracemalloc.start()
        func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak / 1024 / 1024  # Convert to MB
    
    def _generate_test_data(self) -> Dict[str, Any]:
        """Generate test data for benchmarks"""
        return {
            'small_document': self._generate_document(1000),
            'medium_document': self._generate_document(10000),
            'large_document': self._generate_document(100000),
            'project_dependencies': self._generate_dependencies(100),
            'large_dependencies': self._generate_dependencies(10000),
            'threat_events': self._generate_threat_events(1000),
            'dsr_request': self._generate_dsr_request(),
            'compliance_standards': ['GDPR', 'CCPA', 'HIPAA', 'SOC2', 'ISO27001']
        }
    
    def _generate_document(self, size: int) -> str:
        """Generate a test document with PII"""
        pii_patterns = [
            'john.doe@example.com',
            'SSN: 123-45-6789',
            'Phone: +1-555-123-4567',
            'Credit Card: 4111-1111-1111-1111',
            'DOB: 01/15/1990',
            'IP: 192.168.1.1'
        ]
        
        text = []
        for i in range(size // 100):
            if random.random() < 0.1:  # 10% chance of PII
                text.append(random.choice(pii_patterns))
            else:
                text.append(''.join(random.choices(string.ascii_letters + string.digits + ' ', k=100)))
        
        return ' '.join(text)
    
    def _generate_dependencies(self, count: int) -> List[Dict]:
        """Generate test dependencies for SBOM"""
        deps = []
        for i in range(count):
            deps.append({
                'name': f'package-{i}',
                'version': f'{random.randint(1,10)}.{random.randint(0,20)}.{random.randint(0,100)}',
                'license': random.choice(['MIT', 'Apache-2.0', 'GPL-3.0', 'BSD-3-Clause']),
                'dependencies': [f'package-{random.randint(0, count-1)}' for _ in range(random.randint(0, 5))]
            })
        return deps
    
    def _generate_threat_events(self, count: int) -> List[Dict]:
        """Generate test threat events"""
        event_types = ['login_failure', 'unauthorized_access', 'data_exfiltration', 
                      'malware_detected', 'ddos_attempt', 'sql_injection']
        
        events = []
        for i in range(count):
            events.append({
                'timestamp': time.time() - random.randint(0, 86400),
                'type': random.choice(event_types),
                'severity': random.choice(['low', 'medium', 'high', 'critical']),
                'source_ip': f'192.168.{random.randint(0,255)}.{random.randint(0,255)}',
                'user_id': f'user-{random.randint(1,1000)}',
                'details': {'attempt': i, 'blocked': random.choice([True, False])}
            })
        return events
    
    def _generate_dsr_request(self) -> Dict:
        """Generate test DSR request"""
        return {
            'request_id': 'DSR-2024-001',
            'type': random.choice(['access', 'deletion', 'portability', 'rectification']),
            'user_id': 'user-123',
            'email': 'user@example.com',
            'submitted_at': time.time(),
            'data_categories': ['personal', 'usage', 'preferences', 'communications']
        }
    
    def benchmark_sbom_generation(self, test_data: Dict) -> BenchmarkResult:
        """Benchmark SBOM generation performance"""
        print("\n📊 Benchmarking SBOM Generation...")
        
        # Small project
        small_time, small_std = self._measure_time(
            self.sbom_generator.generate,
            test_data['project_dependencies'][:100],
            iterations=50
        )
        
        # Large project
        large_time, large_std = self._measure_time(
            self.sbom_generator.generate,
            test_data['large_dependencies'],
            iterations=10
        )
        
        # Memory usage
        memory = self._measure_memory(
            self.sbom_generator.generate,
            test_data['large_dependencies']
        )
        
        result = BenchmarkResult(
            operation='SBOM Generation',
            baseline_ms=small_time,
            iterations=50,
            std_dev=small_std,
            memory_mb=memory,
            throughput=100 / (small_time / 1000)  # Dependencies per second
        )
        
        print(f"  Small project (100 deps): {small_time:.2f}ms ± {small_std:.2f}ms")
        print(f"  Large project (10K deps): {large_time:.2f}ms ± {large_std:.2f}ms")
        print(f"  Memory usage: {memory:.2f}MB")
        print(f"  Throughput: {result.throughput:.2f} deps/sec")
        print(f"  Target: <30ms (small), <100ms (large)")
        
        return result
    
    def benchmark_pii_detection(self, test_data: Dict) -> BenchmarkResult:
        """Benchmark PII detection performance"""
        print("\n🔍 Benchmarking PII Detection...")
        
        # Single document
        doc_time, doc_std = self._measure_time(
            self.pii_detector.detect,
            test_data['medium_document'],
            iterations=100
        )
        
        # Batch processing
        documents = [test_data['small_document'] for _ in range(100)]
        batch_start = time.perf_counter()
        for doc in documents:
            self.pii_detector.detect(doc)
        batch_end = time.perf_counter()
        batch_throughput = 100 / (batch_end - batch_start)
        
        # Memory usage
        memory = self._measure_memory(
            self.pii_detector.detect,
            test_data['large_document']
        )
        
        result = BenchmarkResult(
            operation='PII Detection',
            baseline_ms=doc_time,
            iterations=100,
            std_dev=doc_std,
            memory_mb=memory,
            throughput=batch_throughput
        )
        
        print(f"  Single document: {doc_time:.2f}ms ± {doc_std:.2f}ms")
        print(f"  Batch throughput: {batch_throughput:.2f} docs/sec")
        print(f"  Memory usage: {memory:.2f}MB")
        print(f"  Target: <20ms, 100+ docs/sec")
        
        return result
    
    def benchmark_threat_detection(self, test_data: Dict) -> BenchmarkResult:
        """Benchmark threat detection performance"""
        print("\n⚠️ Benchmarking Threat Detection...")
        
        # Single event
        event_time, event_std = self._measure_time(
            self.threat_detector.analyze_event,
            test_data['threat_events'][0],
            iterations=1000
        )
        
        # Event stream throughput
        events = test_data['threat_events']
        stream_start = time.perf_counter()
        for event in events:
            self.threat_detector.analyze_event(event)
        stream_end = time.perf_counter()
        event_throughput = len(events) / (stream_end - stream_start)
        
        # Memory usage
        memory = self._measure_memory(
            lambda: [self.threat_detector.analyze_event(e) for e in events[:100]]
        )
        
        result = BenchmarkResult(
            operation='Threat Detection',
            baseline_ms=event_time,
            iterations=1000,
            std_dev=event_std,
            memory_mb=memory,
            throughput=event_throughput
        )
        
        print(f"  Single event: {event_time:.2f}ms ± {event_std:.2f}ms")
        print(f"  Event throughput: {event_throughput:.2f} events/sec")
        print(f"  Memory usage: {memory:.2f}MB")
        print(f"  Target: <5ms, 10,000+ events/sec")
        
        return result
    
    def benchmark_dsr_processing(self, test_data: Dict) -> BenchmarkResult:
        """Benchmark DSR processing performance"""
        print("\n📋 Benchmarking DSR Processing...")
        
        # Standard request
        dsr_time, dsr_std = self._measure_time(
            self.dsr_handler.process_request,
            test_data['dsr_request'],
            iterations=20
        )
        
        # Memory usage
        memory = self._measure_memory(
            self.dsr_handler.process_request,
            test_data['dsr_request']
        )
        
        result = BenchmarkResult(
            operation='DSR Processing',
            baseline_ms=dsr_time,
            iterations=20,
            std_dev=dsr_std,
            memory_mb=memory,
            throughput=1000 / dsr_time  # Requests per second
        )
        
        print(f"  Standard request: {dsr_time:.2f}ms ± {dsr_std:.2f}ms")
        print(f"  Memory usage: {memory:.2f}MB")
        print(f"  Throughput: {result.throughput:.2f} requests/sec")
        print(f"  Target: <500ms")
        
        return result
    
    def benchmark_compliance_assessment(self, test_data: Dict) -> BenchmarkResult:
        """Benchmark compliance assessment performance"""
        print("\n✅ Benchmarking Compliance Assessment...")
        
        # Full assessment
        compliance_time, compliance_std = self._measure_time(
            self.compliance_reporter.generate_report,
            test_data['compliance_standards'],
            iterations=10
        )
        
        # Memory usage
        memory = self._measure_memory(
            self.compliance_reporter.generate_report,
            test_data['compliance_standards']
        )
        
        result = BenchmarkResult(
            operation='Compliance Assessment',
            baseline_ms=compliance_time,
            iterations=10,
            std_dev=compliance_std,
            memory_mb=memory,
            throughput=1000 / compliance_time  # Assessments per second
        )
        
        print(f"  Full assessment: {compliance_time:.2f}ms ± {compliance_std:.2f}ms")
        print(f"  Memory usage: {memory:.2f}MB")
        print(f"  Throughput: {result.throughput:.2f} assessments/sec")
        print(f"  Target: <1000ms")
        
        return result
    
    def run_baseline_benchmarks(self) -> Dict[str, BenchmarkResult]:
        """Run all baseline benchmarks"""
        print("\n" + "="*60)
        print("M010 Security Module - Baseline Performance Benchmarks")
        print("="*60)
        
        test_data = self._generate_test_data()
        
        self.results['sbom'] = self.benchmark_sbom_generation(test_data)
        self.results['pii'] = self.benchmark_pii_detection(test_data)
        self.results['threat'] = self.benchmark_threat_detection(test_data)
        self.results['dsr'] = self.benchmark_dsr_processing(test_data)
        self.results['compliance'] = self.benchmark_compliance_assessment(test_data)
        
        self._print_summary()
        return self.results
    
    def run_optimized_benchmarks(self) -> Dict[str, BenchmarkResult]:
        """Run benchmarks on optimized implementations"""
        print("\n" + "="*60)
        print("M010 Security Module - Optimized Performance Benchmarks")
        print("="*60)
        
        # Import optimized components (will be created)
        try:
            from devdocai.security.optimized.sbom_optimized import OptimizedSBOMGenerator
            from devdocai.security.optimized.pii_optimized import OptimizedPIIDetector
            from devdocai.security.optimized.threat_optimized import OptimizedThreatDetector
            from devdocai.security.optimized.dsr_optimized import OptimizedDSRHandler
            from devdocai.security.optimized.compliance_optimized import OptimizedComplianceReporter
            
            # Replace with optimized versions
            self.sbom_generator = OptimizedSBOMGenerator()
            self.pii_detector = OptimizedPIIDetector()
            self.threat_detector = OptimizedThreatDetector()
            self.dsr_handler = OptimizedDSRHandler()
            self.compliance_reporter = OptimizedComplianceReporter()
            
            test_data = self._generate_test_data()
            
            # Run benchmarks and update optimized times
            sbom_result = self.benchmark_sbom_generation(test_data)
            self.results['sbom'].optimized_ms = sbom_result.baseline_ms
            self.results['sbom'].calculate_improvement()
            
            pii_result = self.benchmark_pii_detection(test_data)
            self.results['pii'].optimized_ms = pii_result.baseline_ms
            self.results['pii'].calculate_improvement()
            
            threat_result = self.benchmark_threat_detection(test_data)
            self.results['threat'].optimized_ms = threat_result.baseline_ms
            self.results['threat'].calculate_improvement()
            
            dsr_result = self.benchmark_dsr_processing(test_data)
            self.results['dsr'].optimized_ms = dsr_result.baseline_ms
            self.results['dsr'].calculate_improvement()
            
            compliance_result = self.benchmark_compliance_assessment(test_data)
            self.results['compliance'].optimized_ms = compliance_result.baseline_ms
            self.results['compliance'].calculate_improvement()
            
            self._print_comparison()
            
        except ImportError:
            print("⚠️ Optimized implementations not yet available")
            print("Run baseline benchmarks first, then implement optimizations")
        
        return self.results
    
    def _print_summary(self):
        """Print benchmark summary"""
        print("\n" + "="*60)
        print("Baseline Performance Summary")
        print("="*60)
        
        for key, result in self.results.items():
            print(f"\n{result.operation}:")
            print(f"  Average time: {result.baseline_ms:.2f}ms")
            print(f"  Std deviation: {result.std_dev:.2f}ms")
            print(f"  Memory usage: {result.memory_mb:.2f}MB")
            print(f"  Throughput: {result.throughput:.2f} ops/sec")
    
    def _print_comparison(self):
        """Print before/after comparison"""
        print("\n" + "="*60)
        print("Performance Optimization Results")
        print("="*60)
        
        total_improvement = 0
        count = 0
        
        for key, result in self.results.items():
            if result.optimized_ms > 0:
                print(f"\n{result.operation}:")
                print(f"  Baseline: {result.baseline_ms:.2f}ms")
                print(f"  Optimized: {result.optimized_ms:.2f}ms")
                print(f"  Improvement: {result.improvement_pct:.1f}%")
                
                # Check if target met
                targets = {
                    'sbom': 30,
                    'pii': 20,
                    'threat': 5,
                    'dsr': 500,
                    'compliance': 1000
                }
                
                target = targets.get(key, 0)
                if result.optimized_ms <= target:
                    print(f"  ✅ Target met (<{target}ms)")
                else:
                    print(f"  ❌ Target not met (<{target}ms)")
                
                total_improvement += result.improvement_pct
                count += 1
        
        if count > 0:
            avg_improvement = total_improvement / count
            print(f"\n🎯 Average Performance Improvement: {avg_improvement:.1f}%")
            
            if avg_improvement >= 50:
                print("✅ Pass 2 Performance Target Achieved (50-70% improvement)")
            else:
                print(f"⚠️ Pass 2 Target Not Met (achieved {avg_improvement:.1f}%, target 50-70%)")
    
    def export_results(self, filename: str = 'benchmark_results.json'):
        """Export benchmark results to JSON"""
        results_dict = {}
        for key, result in self.results.items():
            results_dict[key] = {
                'operation': result.operation,
                'baseline_ms': result.baseline_ms,
                'optimized_ms': result.optimized_ms,
                'improvement_pct': result.improvement_pct,
                'memory_mb': result.memory_mb,
                'throughput': result.throughput,
                'std_dev': result.std_dev
            }
        
        with open(filename, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\n📊 Results exported to {filename}")


def main():
    """Run the benchmark suite"""
    suite = M010BenchmarkSuite()
    
    # Run baseline benchmarks
    print("\n🚀 Starting M010 Performance Benchmark Suite")
    baseline_results = suite.run_baseline_benchmarks()
    
    # Export baseline results
    suite.export_results('m010_baseline_benchmarks.json')
    
    # Try to run optimized benchmarks (will fail initially)
    print("\n🔄 Attempting optimized benchmarks...")
    suite.run_optimized_benchmarks()
    
    print("\n✅ Benchmark suite complete!")
    print("Next step: Implement optimizations based on baseline results")


if __name__ == "__main__":
    main()