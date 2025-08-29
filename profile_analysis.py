#!/usr/bin/env python3
"""
Profile the full analysis to find bottlenecks
"""

import sys
sys.path.insert(0, '/workspaces/DocDevAI-v3.0.0')

from devdocai.miair.engine_unified import create_engine, EngineMode
import time
import cProfile
import pstats
import io

def profile_analysis():
    """Profile the full analysis process."""
    
    test_doc = """
    # Software Architecture Document
    
    ## Overview
    This document provides comprehensive architectural guidelines for modern software development.
    The system consists of several interconnected modules that work together to provide
    a scalable and maintainable solution for document processing and analysis.
    
    ### Performance Considerations
    The architecture is designed to handle high throughput scenarios with:
    - Asynchronous processing capabilities
    - Caching mechanisms for frequently accessed data
    - Load balancing across multiple instances
    """
    
    print("🔍 Profiling M003 Full Analysis Process")
    
    # Create optimized engine
    engine = create_engine(EngineMode.OPTIMIZED)
    
    # Profile a single analysis
    pr = cProfile.Profile()
    pr.enable()
    
    # Run multiple analyses for better profiling data
    for i in range(20):
        result = engine.analyze(test_doc, f"doc_{i}")
    
    pr.disable()
    
    # Analyze profile results
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # Top 30 functions
    
    print(s.getvalue())

if __name__ == "__main__":
    profile_analysis()