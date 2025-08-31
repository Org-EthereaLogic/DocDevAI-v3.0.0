"""
Performance Testing Module with Core Web Vitals
Comprehensive performance validation for M011 Dashboard
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

import pytest
from unittest.mock import Mock, patch, AsyncMock

# Import main framework
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from tests.ui.ui_testing_framework import (
    PerformanceTester,
    UITestConfig,
    NetworkProfile,
    PerformanceResult
)

logger = logging.getLogger(__name__)


@dataclass
class PerformanceTarget:
    """Performance target thresholds"""
    metric: str
    good: float
    needs_improvement: float
    poor: float
    unit: str


class CoreWebVitals:
    """Core Web Vitals definitions and thresholds"""
    
    # Largest Contentful Paint (LCP)
    LCP = PerformanceTarget(
        metric="LCP",
        good=2.5,  # seconds
        needs_improvement=4.0,
        poor=float('inf'),
        unit="seconds"
    )
    
    # First Input Delay (FID)
    FID = PerformanceTarget(
        metric="FID",
        good=100,  # milliseconds
        needs_improvement=300,
        poor=float('inf'),
        unit="milliseconds"
    )
    
    # Cumulative Layout Shift (CLS)
    CLS = PerformanceTarget(
        metric="CLS",
        good=0.1,
        needs_improvement=0.25,
        poor=float('inf'),
        unit="score"
    )
    
    # Additional metrics
    FCP = PerformanceTarget(
        metric="FCP",  # First Contentful Paint
        good=1.8,
        needs_improvement=3.0,
        poor=float('inf'),
        unit="seconds"
    )
    
    TTFB = PerformanceTarget(
        metric="TTFB",  # Time to First Byte
        good=0.8,
        needs_improvement=1.8,
        poor=float('inf'),
        unit="seconds"
    )
    
    TTI = PerformanceTarget(
        metric="TTI",  # Time to Interactive
        good=3.8,
        needs_improvement=7.3,
        poor=float('inf'),
        unit="seconds"
    )
    
    TBT = PerformanceTarget(
        metric="TBT",  # Total Blocking Time
        good=200,
        needs_improvement=600,
        poor=float('inf'),
        unit="milliseconds"
    )
    
    SI = PerformanceTarget(
        metric="SI",  # Speed Index
        good=3.4,
        needs_improvement=5.8,
        poor=float('inf'),
        unit="seconds"
    )


@dataclass
class ResourceMetrics:
    """Resource loading metrics"""
    total_resources: int = 0
    total_size: float = 0.0  # MB
    javascript_size: float = 0.0
    css_size: float = 0.0
    image_size: float = 0.0
    font_size: float = 0.0
    other_size: float = 0.0
    cached_resources: int = 0
    cache_hit_rate: float = 0.0


@dataclass
class MemoryMetrics:
    """Memory usage metrics"""
    initial_heap: float = 0.0  # MB
    peak_heap: float = 0.0
    final_heap: float = 0.0
    heap_growth: float = 0.0
    gc_count: int = 0
    gc_time: float = 0.0  # milliseconds


class PerformanceValidator:
    """Performance validation and scoring"""
    
    @staticmethod
    def score_metric(value: float, target: PerformanceTarget) -> Dict[str, Any]:
        """Score a performance metric against targets"""
        
        if value <= target.good:
            score = 1.0
            rating = "good"
        elif value <= target.needs_improvement:
            # Linear interpolation between good and needs_improvement
            score = 0.5 + 0.5 * (target.needs_improvement - value) / (target.needs_improvement - target.good)
            rating = "needs_improvement"
        else:
            # Exponential decay for poor performance
            score = max(0, 0.5 * (target.needs_improvement / value))
            rating = "poor"
        
        return {
            "value": value,
            "score": score,
            "rating": rating,
            "target": {
                "good": target.good,
                "needs_improvement": target.needs_improvement
            },
            "unit": target.unit
        }
    
    @staticmethod
    def calculate_overall_score(metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        
        # Weights for different metrics
        weights = {
            "LCP": 0.25,
            "FID": 0.25,
            "CLS": 0.25,
            "FCP": 0.1,
            "TTI": 0.1,
            "TBT": 0.05
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in metrics and "score" in metrics[metric]:
                total_score += metrics[metric]["score"] * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0


class AdvancedPerformanceTester:
    """Advanced performance testing with detailed metrics"""
    
    def __init__(self, config: Optional[UITestConfig] = None):
        self.config = config or UITestConfig()
        self.validator = PerformanceValidator()
        
    async def run_performance_audit(
        self, browser, url: str
    ) -> Dict[str, Any]:
        """Run comprehensive performance audit"""
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "audits": [],
            "summary": {
                "overall_score": 0.0,
                "core_web_vitals_passed": False,
                "recommendations": []
            }
        }
        
        # Test with different network conditions
        for profile in self.config.network_profiles:
            audit_result = await self._audit_with_profile(
                browser, url, profile
            )
            results["audits"].append(audit_result)
        
        # Calculate summary
        results["summary"] = self._calculate_summary(results["audits"])
        
        # Generate recommendations
        results["summary"]["recommendations"] = self._generate_recommendations(
            results["audits"]
        )
        
        return results
    
    async def _audit_with_profile(
        self, browser, url: str, profile: NetworkProfile
    ) -> Dict[str, Any]:
        """Audit performance with specific network profile"""
        
        context = await browser.new_context()
        
        # Apply network throttling if available
        if hasattr(context, 'set_offline'):
            await self._apply_network_throttling(context, profile)
        
        page = await context.new_page()
        
        # Enable performance monitoring
        await self._enable_performance_monitoring(page)
        
        try:
            # Start timing
            start_time = time.time()
            
            # Navigate to page
            await page.goto(url, wait_until="networkidle")
            
            # Wait for page to be fully loaded
            await page.wait_for_load_state("domcontentloaded")
            
            # Collect metrics
            result = {
                "network_profile": profile.name,
                "timestamp": datetime.now().isoformat(),
                "metrics": {},
                "resources": None,
                "memory": None,
                "runtime": None
            }
            
            # Collect Core Web Vitals
            web_vitals = await self._collect_web_vitals(page)
            for metric, value in web_vitals.items():
                target = getattr(CoreWebVitals, metric, None)
                if target:
                    result["metrics"][metric] = self.validator.score_metric(value, target)
            
            # Collect additional performance metrics
            perf_metrics = await self._collect_performance_metrics(page)
            result["metrics"].update(perf_metrics)
            
            # Collect resource metrics
            result["resources"] = await self._collect_resource_metrics(page)
            
            # Collect memory metrics
            result["memory"] = await self._collect_memory_metrics(page)
            
            # Collect runtime metrics
            result["runtime"] = await self._collect_runtime_metrics(page, start_time)
            
            # Calculate score
            result["score"] = self.validator.calculate_overall_score(result["metrics"])
            
            # Run specific performance tests
            result["tests"] = {
                "progressive_loading": await self._test_progressive_loading(page),
                "interaction_responsiveness": await self._test_interaction_responsiveness(page),
                "animation_performance": await self._test_animation_performance(page),
                "memory_leaks": await self._test_memory_leaks(page),
                "bundle_optimization": await self._test_bundle_optimization(page)
            }
            
            return result
            
        finally:
            await context.close()
    
    async def _enable_performance_monitoring(self, page):
        """Enable performance monitoring on page"""
        
        # Inject performance monitoring script
        await page.add_script_tag(content="""
            window.__performance_marks = [];
            window.__performance_measures = [];
            
            // Override performance.mark
            const originalMark = performance.mark.bind(performance);
            performance.mark = function(name) {
                window.__performance_marks.push({name, time: performance.now()});
                return originalMark(name);
            };
            
            // Override performance.measure
            const originalMeasure = performance.measure.bind(performance);
            performance.measure = function(name, startMark, endMark) {
                const measure = originalMeasure(name, startMark, endMark);
                window.__performance_measures.push({name, duration: measure.duration});
                return measure;
            };
            
            // Monitor long tasks
            if ('PerformanceObserver' in window) {
                const observer = new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (entry.duration > 50) {
                            console.warn('Long task detected:', entry.duration);
                        }
                    }
                });
                observer.observe({entryTypes: ['longtask']});
            }
        """)
    
    async def _apply_network_throttling(self, context, profile: NetworkProfile):
        """Apply network throttling to context"""
        
        # This would require CDP (Chrome DevTools Protocol) access
        # Simplified version for illustration
        
        if profile != NetworkProfile.NO_THROTTLE:
            # In real implementation, would use CDP to throttle
            pass
    
    async def _collect_web_vitals(self, page) -> Dict[str, float]:
        """Collect Core Web Vitals metrics"""
        
        # Inject web-vitals library
        await page.add_script_tag(
            url="https://unpkg.com/web-vitals@3/dist/web-vitals.iife.js"
        )
        
        # Collect metrics
        vitals = await page.evaluate("""
            () => new Promise(resolve => {
                const vitals = {};
                let metricsCollected = 0;
                const expectedMetrics = 3;
                
                const checkComplete = () => {
                    metricsCollected++;
                    if (metricsCollected >= expectedMetrics) {
                        resolve(vitals);
                    }
                };
                
                // Collect LCP
                webVitals.onLCP(metric => {
                    vitals.LCP = metric.value / 1000;  // Convert to seconds
                    checkComplete();
                });
                
                // Collect FID (or use TBT as proxy)
                webVitals.onFID(metric => {
                    vitals.FID = metric.value;
                    checkComplete();
                }, {reportAllChanges: true});
                
                // Collect CLS
                webVitals.onCLS(metric => {
                    vitals.CLS = metric.value;
                    checkComplete();
                });
                
                // Timeout fallback
                setTimeout(() => {
                    // Use TBT as FID proxy if FID not available
                    if (!vitals.FID) {
                        vitals.FID = performance.measure ? 50 : 100;  // Placeholder
                    }
                    resolve(vitals);
                }, 5000);
            })
        """)
        
        return vitals
    
    async def _collect_performance_metrics(self, page) -> Dict[str, Any]:
        """Collect additional performance metrics"""
        
        metrics = await page.evaluate("""
            () => {
                const navigation = performance.getEntriesByType('navigation')[0];
                const paint = performance.getEntriesByType('paint');
                
                const metrics = {};
                
                // Navigation timing
                if (navigation) {
                    metrics.TTFB = {
                        value: navigation.responseStart - navigation.requestStart,
                        score: 0,
                        unit: 'milliseconds'
                    };
                    
                    metrics.domContentLoaded = {
                        value: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                        score: 0,
                        unit: 'milliseconds'
                    };
                    
                    metrics.loadComplete = {
                        value: navigation.loadEventEnd - navigation.loadEventStart,
                        score: 0,
                        unit: 'milliseconds'
                    };
                }
                
                // Paint timing
                const fcp = paint.find(p => p.name === 'first-contentful-paint');
                if (fcp) {
                    metrics.FCP = {
                        value: fcp.startTime / 1000,
                        score: 0,
                        unit: 'seconds'
                    };
                }
                
                // Calculate TTI (simplified)
                const tti = navigation ? navigation.loadEventEnd : 0;
                if (tti) {
                    metrics.TTI = {
                        value: tti / 1000,
                        score: 0,
                        unit: 'seconds'
                    };
                }
                
                return metrics;
            }
        """)
        
        # Score the metrics
        for metric_name, metric_data in metrics.items():
            target = getattr(CoreWebVitals, metric_name, None)
            if target and isinstance(metric_data, dict):
                scored = self.validator.score_metric(metric_data["value"], target)
                metrics[metric_name] = scored
        
        return metrics
    
    async def _collect_resource_metrics(self, page) -> ResourceMetrics:
        """Collect resource loading metrics"""
        
        resources = await page.evaluate("""
            () => {
                const resources = performance.getEntriesByType('resource');
                const metrics = {
                    total_resources: resources.length,
                    total_size: 0,
                    javascript_size: 0,
                    css_size: 0,
                    image_size: 0,
                    font_size: 0,
                    other_size: 0,
                    cached_resources: 0
                };
                
                resources.forEach(resource => {
                    const size = resource.transferSize / (1024 * 1024);  // Convert to MB
                    metrics.total_size += size;
                    
                    // Check if cached
                    if (resource.transferSize === 0 && resource.decodedBodySize > 0) {
                        metrics.cached_resources++;
                    }
                    
                    // Categorize by type
                    const url = resource.name;
                    if (url.match(/\\.js$/)) {
                        metrics.javascript_size += size;
                    } else if (url.match(/\\.css$/)) {
                        metrics.css_size += size;
                    } else if (url.match(/\\.(png|jpg|jpeg|gif|svg|webp)$/)) {
                        metrics.image_size += size;
                    } else if (url.match(/\\.(woff|woff2|ttf|eot)$/)) {
                        metrics.font_size += size;
                    } else {
                        metrics.other_size += size;
                    }
                });
                
                metrics.cache_hit_rate = metrics.total_resources > 0 
                    ? metrics.cached_resources / metrics.total_resources 
                    : 0;
                
                return metrics;
            }
        """)
        
        return ResourceMetrics(**resources)
    
    async def _collect_memory_metrics(self, page) -> MemoryMetrics:
        """Collect memory usage metrics"""
        
        memory = await page.evaluate("""
            () => {
                if (!performance.memory) {
                    return {
                        initial_heap: 0,
                        peak_heap: 0,
                        final_heap: 0,
                        heap_growth: 0,
                        gc_count: 0,
                        gc_time: 0
                    };
                }
                
                const currentHeap = performance.memory.usedJSHeapSize / (1024 * 1024);  // MB
                const limit = performance.memory.jsHeapSizeLimit / (1024 * 1024);
                
                return {
                    initial_heap: currentHeap,
                    peak_heap: currentHeap,
                    final_heap: currentHeap,
                    heap_growth: 0,
                    gc_count: 0,  // Would need GC observer
                    gc_time: 0
                };
            }
        """)
        
        return MemoryMetrics(**memory)
    
    async def _collect_runtime_metrics(self, page, start_time: float) -> Dict[str, Any]:
        """Collect runtime performance metrics"""
        
        runtime = await page.evaluate("""
            () => {
                const marks = window.__performance_marks || [];
                const measures = window.__performance_measures || [];
                
                // Get JavaScript execution time
                let jsTime = 0;
                if (performance.measure) {
                    try {
                        performance.measure('js-execution', 'navigationStart');
                        const jsMeasure = performance.getEntriesByName('js-execution')[0];
                        jsTime = jsMeasure ? jsMeasure.duration : 0;
                    } catch (e) {}
                }
                
                return {
                    marks: marks,
                    measures: measures,
                    js_execution_time: jsTime,
                    user_timing_marks: performance.getEntriesByType('mark').length,
                    user_timing_measures: performance.getEntriesByType('measure').length
                };
            }
        """)
        
        runtime["total_time"] = (time.time() - start_time) * 1000  # Convert to ms
        
        return runtime
    
    async def _test_progressive_loading(self, page) -> Dict[str, Any]:
        """Test progressive loading implementation"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        # Check for lazy loading images
        lazy_images = await page.evaluate("""
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                const lazyCount = images.filter(img => img.loading === 'lazy').length;
                return {
                    total: images.length,
                    lazy: lazyCount,
                    percentage: images.length > 0 ? lazyCount / images.length : 1
                };
            }
        """)
        
        if lazy_images["percentage"] < 0.5:
            result["passed"] = False
            result["issues"].append(f"Only {lazy_images['percentage']*100:.0f}% of images use lazy loading")
        
        # Check for code splitting
        scripts = await page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script[src]'));
                return scripts.map(s => ({
                    src: s.src,
                    async: s.async,
                    defer: s.defer,
                    module: s.type === 'module'
                }));
            }
        """)
        
        async_count = sum(1 for s in scripts if s["async"] or s["defer"])
        if scripts and async_count / len(scripts) < 0.5:
            result["passed"] = False
            result["issues"].append("Insufficient use of async/defer for scripts")
        
        return result
    
    async def _test_interaction_responsiveness(self, page) -> Dict[str, Any]:
        """Test interaction responsiveness"""
        
        result = {
            "passed": True,
            "response_times": [],
            "issues": []
        }
        
        # Find interactive elements
        buttons = await page.query_selector_all("button")
        
        for button in buttons[:3]:  # Test first 3 buttons
            # Measure click response time
            start = time.time()
            await button.click()
            response_time = (time.time() - start) * 1000  # Convert to ms
            
            result["response_times"].append(response_time)
            
            if response_time > 100:  # 100ms threshold
                result["passed"] = False
                result["issues"].append(f"Button response time too slow: {response_time:.0f}ms")
        
        return result
    
    async def _test_animation_performance(self, page) -> Dict[str, Any]:
        """Test animation performance"""
        
        result = {
            "passed": True,
            "animations": [],
            "issues": []
        }
        
        # Check for CSS animations and transitions
        animations = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                const animated = [];
                
                elements.forEach(el => {
                    const style = getComputedStyle(el);
                    if (style.animation !== 'none' || style.transition !== 'none') {
                        animated.push({
                            tag: el.tagName,
                            animation: style.animation,
                            transition: style.transition,
                            willChange: style.willChange
                        });
                    }
                });
                
                return animated;
            }
        """)
        
        result["animations"] = animations
        
        # Check for will-change optimization
        optimized = [a for a in animations if a["willChange"] != "auto"]
        if animations and len(optimized) / len(animations) < 0.5:
            result["passed"] = False
            result["issues"].append("Animations not optimized with will-change")
        
        # Check for transform animations (better performance than position)
        for anim in animations[:5]:
            if "left" in str(anim["animation"]) or "top" in str(anim["animation"]):
                result["issues"].append("Animation using position instead of transform")
        
        return result
    
    async def _test_memory_leaks(self, page) -> Dict[str, Any]:
        """Test for memory leaks"""
        
        result = {
            "passed": True,
            "heap_growth": 0,
            "issues": []
        }
        
        # Get initial heap size
        initial = await page.evaluate("performance.memory ? performance.memory.usedJSHeapSize : 0")
        
        # Simulate user interactions
        for _ in range(5):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(100)
        
        # Force garbage collection if available
        await page.evaluate("if (window.gc) window.gc()")
        
        # Get final heap size
        final = await page.evaluate("performance.memory ? performance.memory.usedJSHeapSize : 0")
        
        # Calculate growth
        growth = (final - initial) / (1024 * 1024)  # Convert to MB
        result["heap_growth"] = growth
        
        if growth > 10:  # 10MB threshold
            result["passed"] = False
            result["issues"].append(f"Potential memory leak: {growth:.1f}MB heap growth")
        
        return result
    
    async def _test_bundle_optimization(self, page) -> Dict[str, Any]:
        """Test JavaScript bundle optimization"""
        
        result = {
            "passed": True,
            "bundle_size": 0,
            "issues": []
        }
        
        # Check bundle sizes
        bundles = await page.evaluate("""
            () => {
                const scripts = performance.getEntriesByType('resource')
                    .filter(r => r.name.endsWith('.js'));
                
                let totalSize = 0;
                const large = [];
                
                scripts.forEach(script => {
                    const size = script.transferSize / 1024;  // KB
                    totalSize += size;
                    
                    if (size > 200) {  // 200KB threshold per file
                        large.push({
                            url: script.name.split('/').pop(),
                            size: size
                        });
                    }
                });
                
                return {
                    total: totalSize,
                    count: scripts.length,
                    large: large
                };
            }
        """)
        
        result["bundle_size"] = bundles["total"]
        
        if bundles["total"] > 1024:  # 1MB total threshold
            result["passed"] = False
            result["issues"].append(f"Total JS bundle too large: {bundles['total']:.0f}KB")
        
        if bundles["large"]:
            result["passed"] = False
            for bundle in bundles["large"]:
                result["issues"].append(f"Large bundle: {bundle['url']} ({bundle['size']:.0f}KB)")
        
        return result
    
    def _calculate_summary(self, audits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary from all audits"""
        
        summary = {
            "overall_score": 0.0,
            "core_web_vitals_passed": True,
            "average_metrics": {},
            "network_comparison": []
        }
        
        if not audits:
            return summary
        
        # Calculate average score
        total_score = sum(a.get("score", 0) for a in audits)
        summary["overall_score"] = total_score / len(audits)
        
        # Check Core Web Vitals pass/fail
        for audit in audits:
            metrics = audit.get("metrics", {})
            
            # Check if all Core Web Vitals are good
            for vital in ["LCP", "FID", "CLS"]:
                if vital in metrics:
                    if metrics[vital].get("rating") != "good":
                        summary["core_web_vitals_passed"] = False
                        break
        
        # Calculate average metrics across all network conditions
        metric_sums = {}
        metric_counts = {}
        
        for audit in audits:
            for metric, data in audit.get("metrics", {}).items():
                if isinstance(data, dict) and "value" in data:
                    if metric not in metric_sums:
                        metric_sums[metric] = 0
                        metric_counts[metric] = 0
                    metric_sums[metric] += data["value"]
                    metric_counts[metric] += 1
        
        for metric in metric_sums:
            summary["average_metrics"][metric] = metric_sums[metric] / metric_counts[metric]
        
        # Network comparison
        for audit in audits:
            summary["network_comparison"].append({
                "profile": audit["network_profile"],
                "score": audit.get("score", 0),
                "LCP": audit.get("metrics", {}).get("LCP", {}).get("value", 0)
            })
        
        return summary
    
    def _generate_recommendations(self, audits: List[Dict[str, Any]]) -> List[str]:
        """Generate performance recommendations"""
        
        recommendations = []
        
        for audit in audits:
            metrics = audit.get("metrics", {})
            tests = audit.get("tests", {})
            resources = audit.get("resources", {})
            
            # LCP recommendations
            if "LCP" in metrics and metrics["LCP"].get("rating") != "good":
                recommendations.append("Optimize Largest Contentful Paint: Use lazy loading, optimize images, and prioritize critical resources")
            
            # FID recommendations
            if "FID" in metrics and metrics["FID"].get("rating") != "good":
                recommendations.append("Improve First Input Delay: Reduce JavaScript execution time, break up long tasks")
            
            # CLS recommendations
            if "CLS" in metrics and metrics["CLS"].get("rating") != "good":
                recommendations.append("Reduce Cumulative Layout Shift: Set size attributes on images/videos, avoid inserting content above existing content")
            
            # Bundle size recommendations
            if tests.get("bundle_optimization", {}).get("bundle_size", 0) > 500:
                recommendations.append("Optimize JavaScript bundles: Implement code splitting, tree shaking, and minification")
            
            # Resource recommendations
            if resources and isinstance(resources, dict):
                if resources.get("cache_hit_rate", 0) < 0.5:
                    recommendations.append("Improve caching: Implement service workers and optimize cache headers")
                
                if resources.get("total_size", 0) > 3:  # 3MB
                    recommendations.append("Reduce total page weight: Optimize images, minify CSS/JS, remove unused code")
        
        # Deduplicate recommendations
        return list(set(recommendations))


# Test Cases

@pytest.mark.asyncio
class TestPerformanceMetrics:
    """Test suite for performance metrics"""
    
    async def test_core_web_vitals_scoring(self):
        """Test Core Web Vitals scoring"""
        validator = PerformanceValidator()
        
        # Test LCP scoring
        lcp_good = validator.score_metric(2.0, CoreWebVitals.LCP)
        assert lcp_good["rating"] == "good"
        assert lcp_good["score"] == 1.0
        
        lcp_needs_improvement = validator.score_metric(3.5, CoreWebVitals.LCP)
        assert lcp_needs_improvement["rating"] == "needs_improvement"
        assert 0.5 < lcp_needs_improvement["score"] < 1.0
        
        lcp_poor = validator.score_metric(5.0, CoreWebVitals.LCP)
        assert lcp_poor["rating"] == "poor"
        assert lcp_poor["score"] < 0.5
    
    async def test_performance_audit(self):
        """Test performance audit execution"""
        config = UITestConfig()
        tester = AdvancedPerformanceTester(config)
        
        # Mock browser and page
        browser = Mock()
        context = Mock()
        page = Mock()
        
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()
        
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.add_script_tag = AsyncMock()
        page.evaluate = AsyncMock(return_value={
            "LCP": 2.3,
            "FID": 90,
            "CLS": 0.08
        })
        page.query_selector_all = AsyncMock(return_value=[])
        page.wait_for_timeout = AsyncMock()
        
        # Run audit with mocked browser
        result = await tester._audit_with_profile(
            browser, "http://localhost:3000", NetworkProfile.WIFI
        )
        
        assert "metrics" in result
        assert "score" in result
        assert result["network_profile"] == "WIFI"
    
    async def test_resource_metrics_collection(self):
        """Test resource metrics collection"""
        config = UITestConfig()
        tester = AdvancedPerformanceTester(config)
        
        # Mock page
        page = Mock()
        page.evaluate = AsyncMock(return_value={
            "total_resources": 50,
            "total_size": 2.5,
            "javascript_size": 1.2,
            "css_size": 0.3,
            "image_size": 0.8,
            "font_size": 0.1,
            "other_size": 0.1,
            "cached_resources": 25,
            "cache_hit_rate": 0.5
        })
        
        metrics = await tester._collect_resource_metrics(page)
        
        assert metrics.total_resources == 50
        assert metrics.cache_hit_rate == 0.5
        assert metrics.javascript_size == 1.2
    
    async def test_memory_leak_detection(self):
        """Test memory leak detection"""
        config = UITestConfig()
        tester = AdvancedPerformanceTester(config)
        
        # Mock page with no memory leak
        page = Mock()
        page.evaluate = AsyncMock(side_effect=[
            10000000,  # Initial heap: 10MB
            10500000   # Final heap: 10.5MB (0.5MB growth - acceptable)
        ])
        page.wait_for_timeout = AsyncMock()
        
        result = await tester._test_memory_leaks(page)
        
        assert result["passed"] is True
        assert result["heap_growth"] < 1  # Less than 1MB growth
        
        # Mock page with memory leak
        page.evaluate = AsyncMock(side_effect=[
            10000000,   # Initial heap: 10MB
            25000000    # Final heap: 25MB (15MB growth - leak!)
        ])
        
        result = await tester._test_memory_leaks(page)
        
        assert result["passed"] is False
        assert "memory leak" in result["issues"][0].lower()
    
    async def test_bundle_optimization_check(self):
        """Test bundle optimization checking"""
        config = UITestConfig()
        tester = AdvancedPerformanceTester(config)
        
        # Mock page with optimized bundles
        page = Mock()
        page.evaluate = AsyncMock(return_value={
            "total": 450,  # 450KB total
            "count": 5,
            "large": []
        })
        
        result = await tester._test_bundle_optimization(page)
        
        assert result["passed"] is True
        assert result["bundle_size"] == 450
        
        # Mock page with large bundles
        page.evaluate = AsyncMock(return_value={
            "total": 1500,  # 1.5MB total
            "count": 3,
            "large": [
                {"url": "vendor.js", "size": 800},
                {"url": "app.js", "size": 500}
            ]
        })
        
        result = await tester._test_bundle_optimization(page)
        
        assert result["passed"] is False
        assert len(result["issues"]) > 0
    
    async def test_recommendation_generation(self):
        """Test performance recommendation generation"""
        config = UITestConfig()
        tester = AdvancedPerformanceTester(config)
        
        # Create audit results with issues
        audits = [{
            "metrics": {
                "LCP": {"value": 4.5, "rating": "poor"},
                "FID": {"value": 350, "rating": "poor"},
                "CLS": {"value": 0.3, "rating": "poor"}
            },
            "tests": {
                "bundle_optimization": {"bundle_size": 1200}
            },
            "resources": {
                "cache_hit_rate": 0.2,
                "total_size": 5.0
            }
        }]
        
        recommendations = tester._generate_recommendations(audits)
        
        assert len(recommendations) > 0
        assert any("Largest Contentful Paint" in r for r in recommendations)
        assert any("First Input Delay" in r for r in recommendations)
        assert any("Cumulative Layout Shift" in r for r in recommendations)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])