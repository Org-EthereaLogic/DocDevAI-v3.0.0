"""
SBOM Testing Framework Test Runner.

Comprehensive test runner for the SBOM Testing Framework that:
- Executes all test suites with proper dependency management
- Generates coverage reports targeting 95% coverage
- Provides performance benchmarking and quality metrics
- Validates enterprise-grade compliance requirements
"""

import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import yaml

# Import SBOM testing framework components
from .core import SBOMTestFramework, SBOMFormat
from .validators import SBOMValidator
from .generators import SBOMTestDataGenerator
from .assertions import SBOMAssertions, calculate_sbom_quality_score


@dataclass
class TestSuiteResult:
    """Results from a test suite execution."""
    suite_name: str
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    execution_time: float
    coverage_percentage: float
    error_messages: List[str]


@dataclass
class SBOMTestingSummary:
    """Summary of complete SBOM testing framework execution."""
    total_tests: int
    total_passed: int
    total_failed: int
    total_skipped: int
    total_execution_time: float
    overall_coverage: float
    quality_score: float
    performance_benchmarks: Dict[str, float]
    compliance_status: str
    suite_results: List[TestSuiteResult]


class SBOMTestRunner:
    """
    Comprehensive test runner for SBOM Testing Framework.
    
    Executes all test suites with proper coverage reporting,
    performance benchmarking, and compliance validation.
    """
    
    # Test suites in dependency order
    TEST_SUITES = [
        {
            "name": "core",
            "module": "tests.sbom.core",
            "description": "Core framework functionality",
            "required": True
        },
        {
            "name": "validators", 
            "module": "tests.sbom.validators",
            "description": "SPDX and CycloneDX format validators",
            "required": True
        },
        {
            "name": "generators",
            "module": "tests.sbom.generators", 
            "description": "Test data generators",
            "required": True
        },
        {
            "name": "assertions",
            "module": "tests.sbom.assertions",
            "description": "Custom assertion helpers",
            "required": True
        },
        {
            "name": "spdx_validators",
            "module": "tests.sbom.formatters.test_spdx_validators",
            "description": "SPDX format validation tests",
            "required": True
        },
        {
            "name": "cyclonedx_validators",
            "module": "tests.sbom.formatters.test_cyclonedx_validators", 
            "description": "CycloneDX format validation tests",
            "required": True
        },
        {
            "name": "signatures",
            "module": "tests.sbom.security.test_signatures",
            "description": "Ed25519 digital signature tests",
            "required": True
        },
        {
            "name": "performance",
            "module": "tests.sbom.performance.test_generation_speed",
            "description": "Performance and scalability tests", 
            "required": True
        },
        {
            "name": "integration",
            "module": "tests.sbom.integration.test_sbom_integration",
            "description": "Integration with M001-M008 systems",
            "required": False  # Optional if modules not available
        }
    ]
    
    # Coverage targets matching M001-M008 standards
    COVERAGE_TARGETS = {
        "minimum": 85.0,     # Absolute minimum
        "target": 95.0,      # Target for M010
        "excellent": 98.0    # Excellent coverage
    }
    
    # Performance benchmarks (seconds)
    PERFORMANCE_TARGETS = {
        "small_project": 5.0,
        "medium_project": 15.0,
        "large_project": 30.0,  # Key M010 requirement
        "validation_speed": 1.0,
        "signature_verification": 0.1
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize test runner."""
        self.output_dir = output_dir or Path("test_results")
        self.output_dir.mkdir(exist_ok=True)
        
        self.start_time = None
        self.end_time = None
        self.suite_results: List[TestSuiteResult] = []
    
    def run_all_tests(
        self, 
        verbose: bool = True,
        generate_html_report: bool = True,
        run_benchmarks: bool = True
    ) -> SBOMTestingSummary:
        """
        Run complete SBOM testing framework test suite.
        
        Args:
            verbose: Enable verbose output
            generate_html_report: Generate HTML coverage report
            run_benchmarks: Run performance benchmarks
            
        Returns:
            Complete testing summary
        """
        if verbose:
            print("🚀 Starting SBOM Testing Framework Test Suite")
            print("=" * 60)
        
        self.start_time = time.perf_counter()
        
        # Run individual test suites
        for suite_config in self.TEST_SUITES:
            if verbose:
                print(f"\n📋 Running {suite_config['name']} tests...")
            
            suite_result = self._run_test_suite(suite_config, verbose)
            self.suite_results.append(suite_result)
            
            if verbose:
                self._print_suite_result(suite_result)
        
        # Run performance benchmarks if requested
        performance_benchmarks = {}
        if run_benchmarks:
            if verbose:
                print(f"\n⚡ Running performance benchmarks...")
            performance_benchmarks = self._run_performance_benchmarks(verbose)
        
        self.end_time = time.perf_counter()
        
        # Calculate overall results
        summary = self._calculate_summary(performance_benchmarks)
        
        # Generate reports
        if generate_html_report:
            self._generate_html_report(summary)
        
        self._generate_json_report(summary)
        
        if verbose:
            self._print_final_summary(summary)
        
        return summary
    
    def _run_test_suite(self, suite_config: Dict[str, Any], verbose: bool) -> TestSuiteResult:
        """Run individual test suite."""
        suite_name = suite_config["name"]
        module = suite_config["module"]
        required = suite_config.get("required", True)
        
        start_time = time.perf_counter()
        
        try:
            # Run pytest for the specific module
            cmd = [
                sys.executable, "-m", "pytest",
                f"{module.replace('.', '/')}.py",
                "-v",
                "--tb=short",
                f"--cov={module}",
                "--cov-report=term-missing",
                f"--cov-report=html:{self.output_dir}/htmlcov_{suite_name}",
                "--cov-report=json",
                f"--junit-xml={self.output_dir}/junit_{suite_name}.xml"
            ]
            
            # Execute tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent.parent.parent  # Project root
            )
            
            execution_time = time.perf_counter() - start_time
            
            # Parse results
            output_lines = result.stdout.split('\n')
            error_lines = result.stderr.split('\n')
            
            # Extract test counts (simplified parsing)
            tests_run = 0
            tests_passed = 0
            tests_failed = 0
            tests_skipped = 0
            coverage_percentage = 0.0
            
            # Parse pytest output for test counts
            for line in output_lines:
                if "failed" in line and "passed" in line:
                    # Example: "2 failed, 8 passed in 1.23s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "failed," and i > 0:
                            tests_failed = int(parts[i-1])
                        elif part == "passed" and i > 0:
                            tests_passed = int(parts[i-1])
                elif " passed in " in line:
                    # Example: "10 passed in 2.34s"
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "passed" and i > 0:
                            tests_passed = int(parts[i-1])
            
            # Parse coverage from coverage.py output
            for line in output_lines:
                if "TOTAL" in line and "%" in line:
                    # Example: "TOTAL    100    20    80%"
                    parts = line.split()
                    for part in parts:
                        if part.endswith('%'):
                            coverage_percentage = float(part[:-1])
                            break
            
            tests_run = tests_passed + tests_failed + tests_skipped
            error_messages = [line for line in error_lines if line.strip()] if result.returncode != 0 else []
            
            return TestSuiteResult(
                suite_name=suite_name,
                tests_run=tests_run,
                tests_passed=tests_passed,
                tests_failed=tests_failed, 
                tests_skipped=tests_skipped,
                execution_time=execution_time,
                coverage_percentage=coverage_percentage,
                error_messages=error_messages
            )
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            
            if required:
                # For required suites, this is a failure
                return TestSuiteResult(
                    suite_name=suite_name,
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=1,
                    tests_skipped=0,
                    execution_time=execution_time,
                    coverage_percentage=0.0,
                    error_messages=[f"Failed to execute test suite: {e}"]
                )
            else:
                # For optional suites, mark as skipped
                return TestSuiteResult(
                    suite_name=suite_name,
                    tests_run=0,
                    tests_passed=0,
                    tests_failed=0,
                    tests_skipped=1,
                    execution_time=execution_time,
                    coverage_percentage=0.0,
                    error_messages=[f"Optional suite skipped: {e}"]
                )
    
    def _run_performance_benchmarks(self, verbose: bool) -> Dict[str, float]:
        """Run performance benchmarks."""
        benchmarks = {}
        
        try:
            # Initialize test components
            generator = SBOMTestDataGenerator(seed=42)
            validator = SBOMValidator()
            
            # Benchmark SBOM generation for different project sizes
            for size in ["small", "medium", "large"]:
                if verbose:
                    print(f"  🏃 Benchmarking {size} project generation...")
                
                dependency_tree = generator.generate_realistic_dependency_tree(
                    complexity=size
                )
                
                # Measure generation time
                from .core import create_sample_sbom
                start_time = time.perf_counter()
                sbom_content = create_sample_sbom(SBOMFormat.SPDX_JSON, dependency_tree)
                generation_time = time.perf_counter() - start_time
                
                benchmarks[f"{size}_generation"] = generation_time
                
                # Measure validation time
                start_time = time.perf_counter()
                validation_result = validator.validate(sbom_content)
                validation_time = time.perf_counter() - start_time
                
                benchmarks[f"{size}_validation"] = validation_time
            
            # Benchmark signature verification
            if verbose:
                print("  🔐 Benchmarking signature verification...")
            
            try:
                from cryptography.hazmat.primitives.asymmetric import ed25519
                
                # Generate key pair
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()
                
                # Test content
                test_content = b"Test SBOM content for benchmarking"
                signature = private_key.sign(test_content)
                
                # Measure verification time
                start_time = time.perf_counter()
                public_key.verify(signature, test_content)
                verification_time = time.perf_counter() - start_time
                
                benchmarks["signature_verification"] = verification_time
                
            except ImportError:
                benchmarks["signature_verification"] = 0.0  # Skip if cryptography not available
            
        except Exception as e:
            if verbose:
                print(f"  ⚠️ Benchmark error: {e}")
        
        return benchmarks
    
    def _calculate_summary(self, performance_benchmarks: Dict[str, float]) -> SBOMTestingSummary:
        """Calculate overall test summary."""
        total_tests = sum(result.tests_run for result in self.suite_results)
        total_passed = sum(result.tests_passed for result in self.suite_results)
        total_failed = sum(result.tests_failed for result in self.suite_results)
        total_skipped = sum(result.tests_skipped for result in self.suite_results)
        
        total_execution_time = self.end_time - self.start_time if self.end_time and self.start_time else 0.0
        
        # Calculate weighted coverage
        total_coverage_weight = 0.0
        weighted_coverage_sum = 0.0
        
        for result in self.suite_results:
            if result.tests_run > 0:  # Only count suites that actually ran
                weight = result.tests_run
                total_coverage_weight += weight
                weighted_coverage_sum += result.coverage_percentage * weight
        
        overall_coverage = weighted_coverage_sum / total_coverage_weight if total_coverage_weight > 0 else 0.0
        
        # Calculate quality score based on test results
        success_rate = total_passed / total_tests if total_tests > 0 else 0.0
        coverage_score = overall_coverage / 100.0
        performance_score = self._calculate_performance_score(performance_benchmarks)
        
        quality_score = (success_rate * 0.4 + coverage_score * 0.4 + performance_score * 0.2)
        
        # Determine compliance status
        compliance_status = "FAIL"
        if total_failed == 0 and overall_coverage >= self.COVERAGE_TARGETS["target"]:
            if quality_score >= 0.95:
                compliance_status = "EXCELLENT"
            elif quality_score >= 0.90:
                compliance_status = "GOOD"
            else:
                compliance_status = "PASS"
        elif total_failed == 0 and overall_coverage >= self.COVERAGE_TARGETS["minimum"]:
            compliance_status = "MARGINAL"
        
        return SBOMTestingSummary(
            total_tests=total_tests,
            total_passed=total_passed,
            total_failed=total_failed,
            total_skipped=total_skipped,
            total_execution_time=total_execution_time,
            overall_coverage=overall_coverage,
            quality_score=quality_score,
            performance_benchmarks=performance_benchmarks,
            compliance_status=compliance_status,
            suite_results=self.suite_results
        )
    
    def _calculate_performance_score(self, benchmarks: Dict[str, float]) -> float:
        """Calculate performance score based on benchmarks."""
        if not benchmarks:
            return 0.0
        
        score = 0.0
        total_weight = 0.0
        
        # Check performance against targets
        performance_checks = [
            ("small_generation", self.PERFORMANCE_TARGETS["small_project"], 0.2),
            ("medium_generation", self.PERFORMANCE_TARGETS["medium_project"], 0.3),
            ("large_generation", self.PERFORMANCE_TARGETS["large_project"], 0.3),
            ("signature_verification", self.PERFORMANCE_TARGETS["signature_verification"], 0.2)
        ]
        
        for benchmark_key, target_time, weight in performance_checks:
            if benchmark_key in benchmarks:
                actual_time = benchmarks[benchmark_key]
                if actual_time <= target_time:
                    score += weight  # Full score if meets target
                elif actual_time <= target_time * 1.5:
                    score += weight * 0.5  # Half score if within 50% of target
                # No score if significantly over target
                
                total_weight += weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _generate_html_report(self, summary: SBOMTestingSummary):
        """Generate HTML test report."""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SBOM Testing Framework Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .suite {{ margin: 10px 0; padding: 10px; border: 1px solid #ddd; }}
        .pass {{ background-color: #d4edda; }}
        .fail {{ background-color: #f8d7da; }}
        .skip {{ background-color: #fff3cd; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        .metric {{ display: inline-block; margin: 10px; padding: 10px; background: #e9ecef; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>SBOM Testing Framework Report</h1>
        <p>Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p>Status: <strong>{summary.compliance_status}</strong></p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">
            <strong>Tests:</strong> {summary.total_passed}/{summary.total_tests} passed
        </div>
        <div class="metric">
            <strong>Coverage:</strong> {summary.overall_coverage:.1f}%
        </div>
        <div class="metric">
            <strong>Quality:</strong> {summary.quality_score:.2f}
        </div>
        <div class="metric">
            <strong>Time:</strong> {summary.total_execution_time:.1f}s
        </div>
    </div>
    
    <div>
        <h2>Test Suites</h2>
        <table>
            <tr>
                <th>Suite</th>
                <th>Tests</th>
                <th>Passed</th>
                <th>Failed</th>
                <th>Coverage</th>
                <th>Time</th>
            </tr>
"""
        
        for result in summary.suite_results:
            status_class = "pass" if result.tests_failed == 0 else "fail"
            html_content += f"""
            <tr class="{status_class}">
                <td>{result.suite_name}</td>
                <td>{result.tests_run}</td>
                <td>{result.tests_passed}</td>
                <td>{result.tests_failed}</td>
                <td>{result.coverage_percentage:.1f}%</td>
                <td>{result.execution_time:.2f}s</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
    
    <div>
        <h2>Performance Benchmarks</h2>
        <table>
            <tr><th>Benchmark</th><th>Time (s)</th><th>Target (s)</th><th>Status</th></tr>
"""
        
        for benchmark, time_val in summary.performance_benchmarks.items():
            target_key = benchmark.replace("_generation", "_project").replace("_", "_")
            target_time = self.PERFORMANCE_TARGETS.get(target_key, 0.0)
            status = "✅ PASS" if time_val <= target_time else "❌ FAIL"
            
            html_content += f"""
            <tr>
                <td>{benchmark}</td>
                <td>{time_val:.3f}</td>
                <td>{target_time:.1f}</td>
                <td>{status}</td>
            </tr>
"""
        
        html_content += """
        </table>
    </div>
</body>
</html>
"""
        
        html_file = self.output_dir / "sbom_test_report.html"
        with open(html_file, "w") as f:
            f.write(html_content)
    
    def _generate_json_report(self, summary: SBOMTestingSummary):
        """Generate JSON test report."""
        json_file = self.output_dir / "sbom_test_report.json"
        
        with open(json_file, "w") as f:
            json.dump(asdict(summary), f, indent=2)
    
    def _print_suite_result(self, result: TestSuiteResult):
        """Print individual suite result."""
        status_emoji = "✅" if result.tests_failed == 0 else "❌"
        print(f"  {status_emoji} {result.suite_name}: {result.tests_passed}/{result.tests_run} passed, "
              f"{result.coverage_percentage:.1f}% coverage ({result.execution_time:.2f}s)")
        
        if result.error_messages:
            for error in result.error_messages[:3]:  # Show first 3 errors
                print(f"    ⚠️ {error}")
    
    def _print_final_summary(self, summary: SBOMTestingSummary):
        """Print final test summary."""
        print("\n" + "=" * 60)
        print("🎯 SBOM Testing Framework Results")
        print("=" * 60)
        
        status_emoji = {
            "EXCELLENT": "🏆",
            "GOOD": "✅", 
            "PASS": "✅",
            "MARGINAL": "⚠️",
            "FAIL": "❌"
        }.get(summary.compliance_status, "❓")
        
        print(f"Status: {status_emoji} {summary.compliance_status}")
        print(f"Tests: {summary.total_passed}/{summary.total_tests} passed")
        print(f"Coverage: {summary.overall_coverage:.1f}% (target: {self.COVERAGE_TARGETS['target']:.1f}%)")
        print(f"Quality Score: {summary.quality_score:.2f}")
        print(f"Total Time: {summary.total_execution_time:.1f}s")
        
        if summary.total_failed > 0:
            print(f"⚠️ {summary.total_failed} tests failed - review individual suite results")
        
        if summary.overall_coverage < self.COVERAGE_TARGETS["target"]:
            print(f"⚠️ Coverage below target - need {self.COVERAGE_TARGETS['target'] - summary.overall_coverage:.1f}% more")
        
        print(f"\n📊 Reports generated in: {self.output_dir}")
        print("   - sbom_test_report.html (detailed HTML report)")
        print("   - sbom_test_report.json (machine-readable results)")


def main():
    """Main entry point for SBOM test runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="SBOM Testing Framework Test Runner")
    parser.add_argument("--output-dir", type=Path, help="Output directory for reports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML report generation")
    parser.add_argument("--no-benchmarks", action="store_true", help="Skip performance benchmarks")
    
    args = parser.parse_args()
    
    runner = SBOMTestRunner(output_dir=args.output_dir)
    
    summary = runner.run_all_tests(
        verbose=args.verbose,
        generate_html_report=not args.no_html,
        run_benchmarks=not args.no_benchmarks
    )
    
    # Exit with appropriate code
    if summary.compliance_status in ["EXCELLENT", "GOOD", "PASS"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()