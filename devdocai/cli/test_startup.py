#!/usr/bin/env python3
"""
Simple startup performance test for M012 CLI.
"""

import time
import subprocess
import sys
import statistics

def measure_startup(iterations=10):
    """Measure CLI startup time."""
    times = []
    
    for i in range(iterations):
        cmd = [sys.executable, "-m", "devdocai.cli.main", "--version"]
        
        start = time.perf_counter()
        result = subprocess.run(cmd, capture_output=True, text=True, env={'PYTHONPATH': '/workspaces/DocDevAI-v3.0.0'})
        elapsed = time.perf_counter() - start
        
        if result.returncode == 0:
            times.append(elapsed * 1000)  # Convert to ms
            print(f"Run {i+1}: {elapsed*1000:.2f}ms")
    
    if times:
        print(f"\nStatistics over {len(times)} runs:")
        print(f"  Average: {statistics.mean(times):.2f}ms")
        print(f"  Median:  {statistics.median(times):.2f}ms")
        print(f"  Min:     {min(times):.2f}ms")
        print(f"  Max:     {max(times):.2f}ms")
        print(f"  StdDev:  {statistics.stdev(times) if len(times) > 1 else 0:.2f}ms")
        
        # Check against target
        avg = statistics.mean(times)
        if avg < 200:
            print(f"\n✅ Target met: {avg:.2f}ms < 200ms")
        else:
            print(f"\n❌ Target missed: {avg:.2f}ms > 200ms")
    else:
        print("No successful runs")

if __name__ == "__main__":
    print("Testing CLI startup performance...")
    print("=" * 50)
    measure_startup()