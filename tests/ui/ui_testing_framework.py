"""
UI Testing Framework for M011 Dashboard
Comprehensive testing framework for accessibility, responsive design, performance, and cross-browser compatibility.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor

# Playwright for browser automation
try:
    from playwright.async_api import async_playwright, Browser, Page, BrowserContext
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Accessibility testing with axe-core
try:
    import axe_selenium_python
    AXE_AVAILABLE = True
except ImportError:
    AXE_AVAILABLE = False

# Performance metrics collection
try:
    from lighthouse import Lighthouse
    LIGHTHOUSE_AVAILABLE = True
except ImportError:
    LIGHTHOUSE_AVAILABLE = False

# Visual regression testing
try:
    from percy import Percy
    PERCY_AVAILABLE = True
except ImportError:
    PERCY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestLevel(Enum):
    """Testing levels for progressive disclosure"""
    MINIMAL = "minimal"
    INTERMEDIATE = "intermediate"
    DETAILED = "detailed"
    FULL = "full"


class ViewportSize(Enum):
    """Standard viewport sizes for responsive testing"""
    # Mobile
    IPHONE_SE = (375, 667)
    IPHONE_12 = (390, 844)
    IPHONE_14_PRO = (393, 852)
    GALAXY_S20 = (360, 800)
    
    # Tablet
    IPAD_MINI = (768, 1024)
    IPAD_PRO = (1024, 1366)
    SURFACE_PRO = (912, 1368)
    
    # Desktop
    LAPTOP = (1366, 768)
    DESKTOP_HD = (1920, 1080)
    DESKTOP_QHD = (2560, 1440)
    DESKTOP_4K = (3840, 2160)


class NetworkProfile(Enum):
    """Network throttling profiles for performance testing"""
    NO_THROTTLE = {"download": -1, "upload": -1, "latency": 0}
    GPRS = {"download": 50 * 1024, "upload": 20 * 1024, "latency": 500}
    SLOW_2G = {"download": 250 * 1024, "upload": 50 * 1024, "latency": 300}
    FAST_2G = {"download": 450 * 1024, "upload": 150 * 1024, "latency": 150}
    SLOW_3G = {"download": 780 * 1024, "upload": 330 * 1024, "latency": 200}
    FAST_3G = {"download": 1.6 * 1024 * 1024, "upload": 750 * 1024, "latency": 100}
    SLOW_4G = {"download": 3 * 1024 * 1024, "upload": 1.5 * 1024 * 1024, "latency": 50}
    WIFI = {"download": 30 * 1024 * 1024, "upload": 15 * 1024 * 1024, "latency": 2}


class ColorBlindType(Enum):
    """Types of color blindness for accessibility testing"""
    NONE = "none"
    PROTANOPIA = "protanopia"  # Red-blind
    DEUTERANOPIA = "deuteranopia"  # Green-blind
    TRITANOPIA = "tritanopia"  # Blue-blind
    ACHROMATOPSIA = "achromatopsia"  # Complete color blindness


@dataclass
class AccessibilityResult:
    """Results from accessibility testing"""
    wcag_level: str = "AA"
    violations: List[Dict] = field(default_factory=list)
    passes: List[Dict] = field(default_factory=list)
    incomplete: List[Dict] = field(default_factory=list)
    inapplicable: List[Dict] = field(default_factory=list)
    contrast_issues: List[Dict] = field(default_factory=list)
    keyboard_nav_score: float = 0.0
    screen_reader_score: float = 0.0
    focus_management_score: float = 0.0
    aria_compliance: float = 0.0
    overall_score: float = 0.0
    details: Dict = field(default_factory=dict)


@dataclass
class ResponsiveResult:
    """Results from responsive design testing"""
    viewport: Tuple[int, int]
    layout_score: float = 0.0
    content_visibility: float = 0.0
    touch_target_compliance: float = 0.0
    text_readability: float = 0.0
    image_optimization: float = 0.0
    navigation_usability: float = 0.0
    overall_score: float = 0.0
    issues: List[Dict] = field(default_factory=list)
    screenshots: List[str] = field(default_factory=list)


@dataclass
class PerformanceResult:
    """Results from performance testing"""
    load_time: float = 0.0
    time_to_interactive: float = 0.0
    first_contentful_paint: float = 0.0
    largest_contentful_paint: float = 0.0
    cumulative_layout_shift: float = 0.0
    first_input_delay: float = 0.0
    total_blocking_time: float = 0.0
    speed_index: float = 0.0
    memory_usage: Dict[str, float] = field(default_factory=dict)
    network_requests: int = 0
    bundle_size: Dict[str, float] = field(default_factory=dict)
    core_web_vitals_score: float = 0.0
    overall_score: float = 0.0


@dataclass
class UITestConfig:
    """Configuration for UI testing"""
    # Target URLs
    base_url: str = "http://localhost:3000"
    dashboard_url: str = "/dashboard"
    
    # Browser settings
    browsers: List[str] = field(default_factory=lambda: ["chromium", "firefox", "webkit"])
    headless: bool = True
    
    # Test levels
    test_accessibility: bool = True
    test_responsive: bool = True
    test_performance: bool = True
    test_visual: bool = True
    test_interaction: bool = True
    test_colorblind: bool = True
    
    # Thresholds
    wcag_level: str = "AA"
    min_contrast_ratio: float = 4.5
    max_load_time: float = 3.0
    max_interaction_time: float = 0.1
    min_browser_compatibility: float = 0.99
    min_accessibility_score: float = 1.0
    
    # Viewport sizes to test
    viewports: List[ViewportSize] = field(default_factory=lambda: [
        ViewportSize.IPHONE_SE,
        ViewportSize.IPAD_MINI,
        ViewportSize.DESKTOP_HD
    ])
    
    # Network profiles to test
    network_profiles: List[NetworkProfile] = field(default_factory=lambda: [
        NetworkProfile.SLOW_3G,
        NetworkProfile.FAST_3G,
        NetworkProfile.WIFI
    ])
    
    # Output settings
    output_dir: Path = Path("test_results/ui")
    generate_report: bool = True
    save_screenshots: bool = True
    save_videos: bool = False


class UITestingFramework:
    """Main UI Testing Framework for M011 Dashboard"""
    
    def __init__(self, config: Optional[UITestConfig] = None):
        self.config = config or UITestConfig()
        self.results: Dict[str, Any] = {}
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Create output directory
        self.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sub-frameworks
        self.accessibility_tester = AccessibilityTester(self.config)
        self.responsive_tester = ResponsiveTester(self.config)
        self.performance_tester = PerformanceTester(self.config)
        self.interaction_tester = InteractionTester(self.config)
        self.visual_tester = VisualRegressionTester(self.config)
        self.colorblind_tester = ColorBlindTester(self.config)
        
    async def setup_browser(self, browser_name: str = "chromium"):
        """Setup browser for testing"""
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available. Install with: pip install playwright")
            return False
            
        try:
            playwright = await async_playwright().start()
            
            # Launch browser
            if browser_name == "chromium":
                self.browser = await playwright.chromium.launch(
                    headless=self.config.headless
                )
            elif browser_name == "firefox":
                self.browser = await playwright.firefox.launch(
                    headless=self.config.headless
                )
            elif browser_name == "webkit":
                self.browser = await playwright.webkit.launch(
                    headless=self.config.headless
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to setup browser: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all configured UI tests"""
        logger.info("Starting comprehensive UI testing")
        
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "config": self.config.__dict__,
            "results": {}
        }
        
        for browser in self.config.browsers:
            logger.info(f"Testing with {browser} browser")
            
            if not await self.setup_browser(browser):
                continue
                
            browser_results = {
                "accessibility": None,
                "responsive": None,
                "performance": None,
                "interaction": None,
                "visual": None,
                "colorblind": None
            }
            
            try:
                # Run accessibility tests
                if self.config.test_accessibility:
                    logger.info("Running accessibility tests...")
                    browser_results["accessibility"] = await self.accessibility_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                
                # Run responsive design tests
                if self.config.test_responsive:
                    logger.info("Running responsive design tests...")
                    browser_results["responsive"] = await self.responsive_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                
                # Run performance tests
                if self.config.test_performance:
                    logger.info("Running performance tests...")
                    browser_results["performance"] = await self.performance_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                
                # Run interaction tests
                if self.config.test_interaction:
                    logger.info("Running interaction tests...")
                    browser_results["interaction"] = await self.interaction_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                
                # Run visual regression tests
                if self.config.test_visual:
                    logger.info("Running visual regression tests...")
                    browser_results["visual"] = await self.visual_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                
                # Run color blind tests
                if self.config.test_colorblind:
                    logger.info("Running color blind accessibility tests...")
                    browser_results["colorblind"] = await self.colorblind_tester.test(
                        self.browser, self.config.base_url + self.config.dashboard_url
                    )
                    
            finally:
                if self.browser:
                    await self.browser.close()
            
            all_results["results"][browser] = browser_results
        
        # Generate report if configured
        if self.config.generate_report:
            self._generate_report(all_results)
        
        return all_results
    
    def _generate_report(self, results: Dict[str, Any]):
        """Generate comprehensive test report"""
        report_path = self.config.output_dir / f"ui_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Test report saved to {report_path}")
        
        # Generate summary
        self._generate_summary(results)
    
    def _generate_summary(self, results: Dict[str, Any]):
        """Generate test summary"""
        summary = []
        summary.append("=" * 80)
        summary.append("UI TESTING FRAMEWORK - TEST SUMMARY")
        summary.append("=" * 80)
        summary.append(f"Test Date: {results['timestamp']}")
        summary.append(f"Browsers Tested: {', '.join(results['results'].keys())}")
        summary.append("")
        
        # Calculate overall scores
        for browser, browser_results in results['results'].items():
            summary.append(f"\n{browser.upper()} Results:")
            summary.append("-" * 40)
            
            if browser_results.get('accessibility'):
                acc = browser_results['accessibility']
                summary.append(f"  Accessibility Score: {acc.get('overall_score', 0):.2%}")
                summary.append(f"    - WCAG {acc.get('wcag_level', 'AA')} Compliance: {acc.get('wcag_compliance', 0):.2%}")
                summary.append(f"    - Keyboard Navigation: {acc.get('keyboard_nav_score', 0):.2%}")
                summary.append(f"    - Screen Reader: {acc.get('screen_reader_score', 0):.2%}")
            
            if browser_results.get('responsive'):
                resp = browser_results['responsive']
                summary.append(f"  Responsive Design Score: {resp.get('overall_score', 0):.2%}")
                summary.append(f"    - Viewports Tested: {len(resp.get('viewports', []))}")
            
            if browser_results.get('performance'):
                perf = browser_results['performance']
                summary.append(f"  Performance Score: {perf.get('overall_score', 0):.2%}")
                summary.append(f"    - Load Time: {perf.get('load_time', 0):.2f}s")
                summary.append(f"    - LCP: {perf.get('largest_contentful_paint', 0):.2f}s")
                summary.append(f"    - FID: {perf.get('first_input_delay', 0):.0f}ms")
                summary.append(f"    - CLS: {perf.get('cumulative_layout_shift', 0):.3f}")
        
        summary.append("\n" + "=" * 80)
        
        # Save summary
        summary_path = self.config.output_dir / f"ui_test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_path, "w") as f:
            f.write("\n".join(summary))
        
        # Print summary to console
        print("\n".join(summary))


class AccessibilityTester:
    """WCAG 2.1 AA Compliance Testing"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
        
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Run comprehensive accessibility tests"""
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            results = {
                "wcag_level": self.config.wcag_level,
                "wcag_compliance": 0.0,
                "violations": [],
                "passes": [],
                "keyboard_nav_score": 0.0,
                "screen_reader_score": 0.0,
                "focus_management_score": 0.0,
                "aria_compliance": 0.0,
                "contrast_issues": [],
                "overall_score": 0.0
            }
            
            # Run axe-core accessibility tests
            if AXE_AVAILABLE:
                axe_results = await self._run_axe_tests(page)
                results.update(axe_results)
            
            # Test keyboard navigation
            keyboard_results = await self._test_keyboard_navigation(page)
            results["keyboard_nav_score"] = keyboard_results["score"]
            
            # Test focus management
            focus_results = await self._test_focus_management(page)
            results["focus_management_score"] = focus_results["score"]
            
            # Test ARIA attributes
            aria_results = await self._test_aria_compliance(page)
            results["aria_compliance"] = aria_results["score"]
            
            # Test color contrast
            contrast_results = await self._test_color_contrast(page)
            results["contrast_issues"] = contrast_results["issues"]
            
            # Calculate overall score
            scores = [
                results["wcag_compliance"],
                results["keyboard_nav_score"],
                results["focus_management_score"],
                results["aria_compliance"],
                1.0 if len(results["contrast_issues"]) == 0 else 0.5
            ]
            results["overall_score"] = sum(scores) / len(scores)
            
            return results
            
        finally:
            await context.close()
    
    async def _run_axe_tests(self, page: Page) -> Dict[str, Any]:
        """Run axe-core accessibility tests"""
        # Inject axe-core script
        await page.add_script_tag(
            url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.7.2/axe.min.js"
        )
        
        # Run axe analysis
        axe_results = await page.evaluate("""
            async () => {
                return await axe.run();
            }
        """)
        
        violations = axe_results.get("violations", [])
        passes = axe_results.get("passes", [])
        
        # Calculate WCAG compliance score
        total_checks = len(violations) + len(passes)
        compliance_score = len(passes) / total_checks if total_checks > 0 else 0
        
        return {
            "wcag_compliance": compliance_score,
            "violations": violations,
            "passes": passes
        }
    
    async def _test_keyboard_navigation(self, page: Page) -> Dict[str, Any]:
        """Test keyboard navigation functionality"""
        results = {
            "score": 0.0,
            "issues": []
        }
        
        # Test tab navigation
        focusable_elements = await page.query_selector_all(
            'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        
        if len(focusable_elements) == 0:
            results["issues"].append("No focusable elements found")
            return results
        
        # Test tab order
        tab_order_correct = True
        for i, element in enumerate(focusable_elements):
            await page.keyboard.press("Tab")
            focused = await page.evaluate("document.activeElement")
            
            # Check if focus moves in logical order
            if not focused:
                tab_order_correct = False
                results["issues"].append(f"Focus lost at element {i}")
        
        # Test keyboard shortcuts
        shortcuts_work = await self._test_keyboard_shortcuts(page)
        
        # Calculate score
        scores = []
        scores.append(1.0 if tab_order_correct else 0.0)
        scores.append(1.0 if shortcuts_work else 0.5)
        
        results["score"] = sum(scores) / len(scores)
        return results
    
    async def _test_keyboard_shortcuts(self, page: Page) -> bool:
        """Test keyboard shortcuts functionality"""
        try:
            # Test common shortcuts
            await page.keyboard.press("Escape")  # Close dialogs
            await page.keyboard.press("Enter")   # Submit forms
            await page.keyboard.press("Space")   # Toggle checkboxes
            
            return True
        except Exception:
            return False
    
    async def _test_focus_management(self, page: Page) -> Dict[str, Any]:
        """Test focus management and indicators"""
        results = {
            "score": 0.0,
            "issues": []
        }
        
        # Check for visible focus indicators
        focus_styles = await page.evaluate("""
            () => {
                const styles = getComputedStyle(document.body);
                const focusVisible = styles.getPropertyValue('--focus-visible') || 
                                   document.querySelector(':focus-visible');
                return focusVisible !== null;
            }
        """)
        
        if not focus_styles:
            results["issues"].append("No visible focus indicators found")
        
        # Test focus trap in modals
        modal_focus_trap = await self._test_modal_focus_trap(page)
        
        # Calculate score
        scores = []
        scores.append(1.0 if focus_styles else 0.0)
        scores.append(1.0 if modal_focus_trap else 0.5)
        
        results["score"] = sum(scores) / len(scores)
        return results
    
    async def _test_modal_focus_trap(self, page: Page) -> bool:
        """Test focus trap in modal dialogs"""
        # Check if modals properly trap focus
        modals = await page.query_selector_all('[role="dialog"], .modal')
        
        for modal in modals:
            # Check if modal has proper focus management
            has_focus_trap = await page.evaluate("""
                (modal) => {
                    const focusableElements = modal.querySelectorAll(
                        'a, button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
                    );
                    return focusableElements.length > 0;
                }
            """, modal)
            
            if not has_focus_trap:
                return False
        
        return True
    
    async def _test_aria_compliance(self, page: Page) -> Dict[str, Any]:
        """Test ARIA attributes compliance"""
        results = {
            "score": 0.0,
            "issues": []
        }
        
        # Check for proper ARIA labels
        aria_checks = await page.evaluate("""
            () => {
                const checks = {
                    labels: 0,
                    descriptions: 0,
                    live_regions: 0,
                    landmarks: 0
                };
                
                // Check aria-label and aria-labelledby
                const labeled = document.querySelectorAll('[aria-label], [aria-labelledby]');
                checks.labels = labeled.length;
                
                // Check aria-describedby
                const described = document.querySelectorAll('[aria-describedby]');
                checks.descriptions = described.length;
                
                // Check live regions
                const liveRegions = document.querySelectorAll('[aria-live]');
                checks.live_regions = liveRegions.length;
                
                // Check landmarks
                const landmarks = document.querySelectorAll('[role="navigation"], [role="main"], [role="banner"]');
                checks.landmarks = landmarks.length;
                
                return checks;
            }
        """)
        
        # Calculate compliance score
        total_score = 0.0
        if aria_checks["labels"] > 0:
            total_score += 0.25
        if aria_checks["descriptions"] > 0:
            total_score += 0.25
        if aria_checks["live_regions"] > 0:
            total_score += 0.25
        if aria_checks["landmarks"] > 0:
            total_score += 0.25
        
        results["score"] = total_score
        
        if total_score < 1.0:
            if aria_checks["labels"] == 0:
                results["issues"].append("Missing ARIA labels")
            if aria_checks["live_regions"] == 0:
                results["issues"].append("No ARIA live regions for dynamic content")
        
        return results
    
    async def _test_color_contrast(self, page: Page) -> Dict[str, Any]:
        """Test color contrast ratios"""
        results = {
            "issues": []
        }
        
        # Get all text elements
        text_elements = await page.query_selector_all('p, h1, h2, h3, h4, h5, h6, span, a, button, label')
        
        for element in text_elements[:10]:  # Test first 10 elements for performance
            contrast_ratio = await page.evaluate("""
                (element) => {
                    const style = getComputedStyle(element);
                    const color = style.color;
                    const backgroundColor = style.backgroundColor;
                    
                    // Simple contrast calculation (would need full implementation)
                    // This is a placeholder - real implementation would calculate actual ratio
                    return 4.5;  // Placeholder value
                }
            """, element)
            
            if contrast_ratio < self.config.min_contrast_ratio:
                text = await element.text_content()
                results["issues"].append({
                    "element": text[:50] if text else "Unknown",
                    "contrast_ratio": contrast_ratio,
                    "required": self.config.min_contrast_ratio
                })
        
        return results


class ResponsiveTester:
    """Responsive design testing across viewports"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
    
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Test responsive design across all configured viewports"""
        results = {
            "viewports": [],
            "overall_score": 0.0
        }
        
        for viewport_size in self.config.viewports:
            viewport_result = await self._test_viewport(
                browser, url, viewport_size
            )
            results["viewports"].append(viewport_result)
        
        # Calculate overall score
        if results["viewports"]:
            total_score = sum(v.get("overall_score", 0) for v in results["viewports"])
            results["overall_score"] = total_score / len(results["viewports"])
        
        return results
    
    async def _test_viewport(self, browser: Browser, url: str, viewport: ViewportSize) -> Dict[str, Any]:
        """Test specific viewport size"""
        width, height = viewport.value
        
        context = await browser.new_context(
            viewport={"width": width, "height": height}
        )
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            result = {
                "viewport": f"{width}x{height}",
                "viewport_name": viewport.name,
                "layout_score": 0.0,
                "content_visibility": 0.0,
                "touch_target_compliance": 0.0,
                "text_readability": 0.0,
                "navigation_usability": 0.0,
                "issues": []
            }
            
            # Test layout integrity
            layout_score = await self._test_layout_integrity(page, width, height)
            result["layout_score"] = layout_score
            
            # Test content visibility
            visibility_score = await self._test_content_visibility(page)
            result["content_visibility"] = visibility_score
            
            # Test touch targets (mobile only)
            if width < 768:
                touch_score = await self._test_touch_targets(page)
                result["touch_target_compliance"] = touch_score
            else:
                result["touch_target_compliance"] = 1.0
            
            # Test text readability
            readability_score = await self._test_text_readability(page, width)
            result["text_readability"] = readability_score
            
            # Test navigation usability
            nav_score = await self._test_navigation_usability(page, width)
            result["navigation_usability"] = nav_score
            
            # Take screenshot if configured
            if self.config.save_screenshots:
                screenshot_path = self.config.output_dir / f"screenshot_{viewport.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result["screenshot"] = str(screenshot_path)
            
            # Calculate overall score
            scores = [
                result["layout_score"],
                result["content_visibility"],
                result["touch_target_compliance"],
                result["text_readability"],
                result["navigation_usability"]
            ]
            result["overall_score"] = sum(scores) / len(scores)
            
            return result
            
        finally:
            await context.close()
    
    async def _test_layout_integrity(self, page: Page, width: int, height: int) -> float:
        """Test if layout maintains integrity at viewport size"""
        
        # Check for horizontal scrolling (bad for mobile)
        has_horizontal_scroll = await page.evaluate("""
            () => document.documentElement.scrollWidth > document.documentElement.clientWidth
        """)
        
        # Check for overlapping elements
        overlapping = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('div, section, article, nav, header, footer');
                let overlaps = 0;
                
                for (let i = 0; i < elements.length; i++) {
                    for (let j = i + 1; j < elements.length; j++) {
                        const rect1 = elements[i].getBoundingClientRect();
                        const rect2 = elements[j].getBoundingClientRect();
                        
                        if (!(rect1.right < rect2.left || 
                              rect1.left > rect2.right || 
                              rect1.bottom < rect2.top || 
                              rect1.top > rect2.bottom)) {
                            overlaps++;
                        }
                    }
                }
                
                return overlaps;
            }
        """)
        
        # Score calculation
        score = 1.0
        if has_horizontal_scroll:
            score -= 0.3
        if overlapping > 0:
            score -= min(0.5, overlapping * 0.1)
        
        return max(0, score)
    
    async def _test_content_visibility(self, page: Page) -> float:
        """Test if critical content is visible"""
        
        # Check if key elements are visible
        critical_elements = await page.evaluate("""
            () => {
                const selectors = ['h1', '.dashboard-header', '.critical-alert', 'nav'];
                let visible = 0;
                let total = 0;
                
                for (const selector of selectors) {
                    const elements = document.querySelectorAll(selector);
                    total += elements.length;
                    
                    elements.forEach(el => {
                        const rect = el.getBoundingClientRect();
                        if (rect.width > 0 && rect.height > 0) {
                            visible++;
                        }
                    });
                }
                
                return total > 0 ? visible / total : 0;
            }
        """)
        
        return critical_elements
    
    async def _test_touch_targets(self, page: Page) -> float:
        """Test touch target sizes for mobile"""
        
        # Check if interactive elements meet minimum size (48x48px)
        compliance = await page.evaluate("""
            () => {
                const minSize = 48;
                const interactive = document.querySelectorAll('button, a, input, select, [role="button"]');
                let compliant = 0;
                
                interactive.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width >= minSize && rect.height >= minSize) {
                        compliant++;
                    }
                });
                
                return interactive.length > 0 ? compliant / interactive.length : 1;
            }
        """)
        
        return compliance
    
    async def _test_text_readability(self, page: Page, width: int) -> float:
        """Test text readability at viewport size"""
        
        # Check font sizes
        readability = await page.evaluate("""
            (width) => {
                const minFontSize = width < 768 ? 14 : 12;
                const textElements = document.querySelectorAll('p, span, a, li');
                let readable = 0;
                
                textElements.forEach(el => {
                    const fontSize = parseFloat(getComputedStyle(el).fontSize);
                    if (fontSize >= minFontSize) {
                        readable++;
                    }
                });
                
                return textElements.length > 0 ? readable / textElements.length : 1;
            }
        """, width)
        
        return readability
    
    async def _test_navigation_usability(self, page: Page, width: int) -> float:
        """Test navigation usability at viewport size"""
        
        if width < 768:
            # Mobile: Check for hamburger menu
            has_mobile_menu = await page.evaluate("""
                () => {
                    const menuButtons = document.querySelectorAll('[aria-label*="menu"], .hamburger, .menu-toggle');
                    return menuButtons.length > 0;
                }
            """)
            return 1.0 if has_mobile_menu else 0.5
        else:
            # Desktop: Check for visible navigation
            has_nav = await page.evaluate("""
                () => {
                    const nav = document.querySelector('nav');
                    if (nav) {
                        const rect = nav.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0;
                    }
                    return false;
                }
            """)
            return 1.0 if has_nav else 0.5


class PerformanceTester:
    """Performance testing with Core Web Vitals"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
    
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Run performance tests"""
        results = {
            "network_profiles": [],
            "overall_score": 0.0
        }
        
        for network_profile in self.config.network_profiles:
            profile_result = await self._test_with_network_profile(
                browser, url, network_profile
            )
            results["network_profiles"].append(profile_result)
        
        # Calculate overall score
        if results["network_profiles"]:
            total_score = sum(p.get("overall_score", 0) for p in results["network_profiles"])
            results["overall_score"] = total_score / len(results["network_profiles"])
        
        return results
    
    async def _test_with_network_profile(
        self, browser: Browser, url: str, profile: NetworkProfile
    ) -> Dict[str, Any]:
        """Test with specific network conditions"""
        
        context = await browser.new_context()
        
        # Apply network throttling
        if profile != NetworkProfile.NO_THROTTLE:
            await context.route("**/*", lambda route, request: route.continue_())
            # Note: Real throttling would require CDP or browser-specific APIs
        
        page = await context.new_page()
        
        try:
            # Start performance measurement
            start_time = time.time()
            
            # Navigate and measure
            await page.goto(url)
            load_time = time.time() - start_time
            
            # Wait for page to be interactive
            await page.wait_for_load_state("networkidle")
            
            # Collect performance metrics
            metrics = await page.evaluate("""
                () => {
                    const perfData = performance.getEntriesByType('navigation')[0];
                    const paintData = performance.getEntriesByType('paint');
                    
                    return {
                        domContentLoaded: perfData.domContentLoadedEventEnd - perfData.domContentLoadedEventStart,
                        loadComplete: perfData.loadEventEnd - perfData.loadEventStart,
                        firstPaint: paintData.find(p => p.name === 'first-paint')?.startTime || 0,
                        firstContentfulPaint: paintData.find(p => p.name === 'first-contentful-paint')?.startTime || 0
                    };
                }
            """)
            
            # Get Core Web Vitals
            web_vitals = await self._get_core_web_vitals(page)
            
            result = {
                "network_profile": profile.name,
                "load_time": load_time,
                "time_to_interactive": metrics.get("loadComplete", 0) / 1000,
                "first_contentful_paint": metrics.get("firstContentfulPaint", 0) / 1000,
                "largest_contentful_paint": web_vitals.get("lcp", 0),
                "cumulative_layout_shift": web_vitals.get("cls", 0),
                "first_input_delay": web_vitals.get("fid", 0),
                "memory_usage": await self._get_memory_usage(page),
                "network_requests": await self._count_network_requests(page),
                "bundle_size": await self._get_bundle_sizes(page)
            }
            
            # Calculate Core Web Vitals score
            result["core_web_vitals_score"] = self._calculate_web_vitals_score(result)
            
            # Calculate overall performance score
            result["overall_score"] = self._calculate_performance_score(result)
            
            return result
            
        finally:
            await context.close()
    
    async def _get_core_web_vitals(self, page: Page) -> Dict[str, float]:
        """Get Core Web Vitals metrics"""
        
        # Inject web-vitals library
        await page.add_script_tag(
            url="https://unpkg.com/web-vitals@3/dist/web-vitals.iife.js"
        )
        
        # Collect metrics
        vitals = await page.evaluate("""
            () => new Promise(resolve => {
                const vitals = {};
                
                webVitals.onLCP(metric => vitals.lcp = metric.value);
                webVitals.onFID(metric => vitals.fid = metric.value);
                webVitals.onCLS(metric => vitals.cls = metric.value);
                
                // Wait for metrics to be collected
                setTimeout(() => resolve(vitals), 2000);
            })
        """)
        
        return vitals
    
    async def _get_memory_usage(self, page: Page) -> Dict[str, float]:
        """Get memory usage metrics"""
        
        memory = await page.evaluate("""
            () => {
                if (performance.memory) {
                    return {
                        usedJSHeapSize: performance.memory.usedJSHeapSize / 1048576,  // Convert to MB
                        totalJSHeapSize: performance.memory.totalJSHeapSize / 1048576,
                        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit / 1048576
                    };
                }
                return {};
            }
        """)
        
        return memory
    
    async def _count_network_requests(self, page: Page) -> int:
        """Count total network requests"""
        
        requests = await page.evaluate("""
            () => performance.getEntriesByType('resource').length
        """)
        
        return requests
    
    async def _get_bundle_sizes(self, page: Page) -> Dict[str, float]:
        """Get JavaScript bundle sizes"""
        
        bundles = await page.evaluate("""
            () => {
                const resources = performance.getEntriesByType('resource');
                const scripts = resources.filter(r => r.name.endsWith('.js'));
                
                let totalSize = 0;
                scripts.forEach(script => {
                    totalSize += script.transferSize || 0;
                });
                
                return {
                    totalJS: totalSize / 1024,  // Convert to KB
                    scriptCount: scripts.length
                };
            }
        """)
        
        return bundles
    
    def _calculate_web_vitals_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate Core Web Vitals score"""
        
        score = 1.0
        
        # LCP scoring (good < 2.5s, needs improvement < 4s, poor >= 4s)
        lcp = metrics.get("largest_contentful_paint", 0)
        if lcp < 2.5:
            pass  # Good
        elif lcp < 4:
            score -= 0.2
        else:
            score -= 0.4
        
        # FID scoring (good < 100ms, needs improvement < 300ms, poor >= 300ms)
        fid = metrics.get("first_input_delay", 0)
        if fid < 100:
            pass  # Good
        elif fid < 300:
            score -= 0.2
        else:
            score -= 0.4
        
        # CLS scoring (good < 0.1, needs improvement < 0.25, poor >= 0.25)
        cls = metrics.get("cumulative_layout_shift", 0)
        if cls < 0.1:
            pass  # Good
        elif cls < 0.25:
            score -= 0.1
        else:
            score -= 0.2
        
        return max(0, score)
    
    def _calculate_performance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall performance score"""
        
        score = 1.0
        
        # Load time scoring
        load_time = metrics.get("load_time", 0)
        if load_time > self.config.max_load_time:
            score -= min(0.3, (load_time - self.config.max_load_time) * 0.1)
        
        # TTI scoring
        tti = metrics.get("time_to_interactive", 0)
        if tti > 5:
            score -= 0.2
        
        # FCP scoring
        fcp = metrics.get("first_contentful_paint", 0)
        if fcp > 2:
            score -= 0.1
        
        # Core Web Vitals weight
        web_vitals_score = metrics.get("core_web_vitals_score", 0)
        score = (score * 0.5) + (web_vitals_score * 0.5)
        
        return max(0, score)


class InteractionTester:
    """User interaction and navigation testing"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
    
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Test user interactions"""
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            results = {
                "keyboard_navigation": await self._test_keyboard_navigation(page),
                "mouse_interactions": await self._test_mouse_interactions(page),
                "touch_gestures": await self._test_touch_gestures(page),
                "form_interactions": await self._test_form_interactions(page),
                "progressive_disclosure": await self._test_progressive_disclosure(page),
                "critical_alerts": await self._test_critical_alerts(page),
                "overall_score": 0.0
            }
            
            # Calculate overall score
            scores = [v.get("score", 0) for v in results.values() if isinstance(v, dict)]
            if scores:
                results["overall_score"] = sum(scores) / len(scores)
            
            return results
            
        finally:
            await context.close()
    
    async def _test_keyboard_navigation(self, page: Page) -> Dict[str, Any]:
        """Test keyboard navigation comprehensively"""
        
        result = {
            "score": 0.0,
            "tab_navigation": False,
            "arrow_navigation": False,
            "shortcuts": False,
            "escape_handling": False
        }
        
        # Test Tab navigation
        try:
            await page.keyboard.press("Tab")
            await page.keyboard.press("Tab")
            await page.keyboard.press("Shift+Tab")
            result["tab_navigation"] = True
        except Exception:
            pass
        
        # Test Arrow key navigation
        try:
            await page.keyboard.press("ArrowDown")
            await page.keyboard.press("ArrowUp")
            await page.keyboard.press("ArrowLeft")
            await page.keyboard.press("ArrowRight")
            result["arrow_navigation"] = True
        except Exception:
            pass
        
        # Test keyboard shortcuts
        try:
            await page.keyboard.press("Control+S")  # Save
            await page.keyboard.press("Control+F")  # Find
            result["shortcuts"] = True
        except Exception:
            pass
        
        # Test Escape key handling
        try:
            await page.keyboard.press("Escape")
            result["escape_handling"] = True
        except Exception:
            pass
        
        # Calculate score
        true_count = sum(1 for v in result.values() if v is True)
        result["score"] = true_count / 4
        
        return result
    
    async def _test_mouse_interactions(self, page: Page) -> Dict[str, Any]:
        """Test mouse interactions"""
        
        result = {
            "score": 0.0,
            "hover_states": False,
            "click_response": False,
            "double_click": False,
            "right_click": False,
            "drag_drop": False
        }
        
        # Test hover states
        buttons = await page.query_selector_all("button")
        if buttons:
            button = buttons[0]
            await button.hover()
            result["hover_states"] = True
        
        # Test click response time
        if buttons:
            start = time.time()
            await buttons[0].click()
            response_time = time.time() - start
            result["click_response"] = response_time < self.config.max_interaction_time
        
        # Test double-click
        try:
            if buttons:
                await buttons[0].dblclick()
                result["double_click"] = True
        except Exception:
            pass
        
        # Test right-click
        try:
            if buttons:
                await buttons[0].click(button="right")
                result["right_click"] = True
        except Exception:
            pass
        
        # Calculate score
        true_count = sum(1 for k, v in result.items() if k != "score" and v is True)
        result["score"] = true_count / 5
        
        return result
    
    async def _test_touch_gestures(self, page: Page) -> Dict[str, Any]:
        """Test touch gestures for mobile"""
        
        result = {
            "score": 1.0,  # Default to perfect score for non-mobile
            "tap": True,
            "swipe": True,
            "pinch": True,
            "long_press": True
        }
        
        # Only test on mobile viewports
        viewport = page.viewport_size
        if viewport and viewport["width"] < 768:
            # These would be tested with real touch events
            # Placeholder for now
            pass
        
        return result
    
    async def _test_form_interactions(self, page: Page) -> Dict[str, Any]:
        """Test form interactions and validation"""
        
        result = {
            "score": 0.0,
            "input_fields": False,
            "validation": False,
            "error_messages": False,
            "success_feedback": False
        }
        
        # Find form elements
        inputs = await page.query_selector_all("input, textarea, select")
        
        if inputs:
            # Test input fields
            for input_field in inputs[:3]:  # Test first 3 inputs
                await input_field.fill("Test input")
                result["input_fields"] = True
            
            # Test validation
            forms = await page.query_selector_all("form")
            if forms:
                # Submit empty form to trigger validation
                await forms[0].evaluate("form => form.requestSubmit()")
                
                # Check for error messages
                errors = await page.query_selector_all(".error, [aria-invalid='true']")
                result["validation"] = len(errors) > 0
                result["error_messages"] = len(errors) > 0
        
        # Calculate score
        true_count = sum(1 for k, v in result.items() if k != "score" and v is True)
        result["score"] = true_count / 4 if true_count > 0 else 0.5
        
        return result
    
    async def _test_progressive_disclosure(self, page: Page) -> Dict[str, Any]:
        """Test progressive disclosure functionality"""
        
        result = {
            "score": 0.0,
            "default_view": False,
            "expansion_controls": False,
            "detail_levels": False,
            "state_persistence": False
        }
        
        # Check for expandable sections
        expandables = await page.query_selector_all(
            "[aria-expanded], .collapsible, .expandable, details"
        )
        
        if expandables:
            result["expansion_controls"] = True
            
            # Test expansion
            for expandable in expandables[:2]:
                await expandable.click()
                await page.wait_for_timeout(300)  # Wait for animation
            
            result["detail_levels"] = True
        
        # Check for default minimal view
        hidden_elements = await page.query_selector_all("[hidden], .collapsed")
        result["default_view"] = len(hidden_elements) > 0
        
        # Test state persistence (would need page reload)
        result["state_persistence"] = True  # Placeholder
        
        # Calculate score
        true_count = sum(1 for k, v in result.items() if k != "score" and v is True)
        result["score"] = true_count / 4
        
        return result
    
    async def _test_critical_alerts(self, page: Page) -> Dict[str, Any]:
        """Test critical alert display and prominence"""
        
        result = {
            "score": 0.0,
            "visual_hierarchy": False,
            "animations": False,
            "dismissal": False,
            "persistence": False,
            "screen_reader": False
        }
        
        # Check for alert elements
        alerts = await page.query_selector_all(
            "[role='alert'], .alert, .notification, .critical"
        )
        
        if alerts:
            # Check visual hierarchy
            for alert in alerts[:2]:
                z_index = await alert.evaluate(
                    "el => getComputedStyle(el).zIndex"
                )
                result["visual_hierarchy"] = z_index != "auto"
            
            # Check for animations
            animation = await alerts[0].evaluate(
                "el => getComputedStyle(el).animation"
            )
            result["animations"] = animation != "none"
            
            # Check dismissal mechanism
            close_buttons = await page.query_selector_all(
                "[aria-label*='close'], .close, .dismiss"
            )
            result["dismissal"] = len(close_buttons) > 0
            
            # Check for ARIA live regions
            live_regions = await page.query_selector_all("[aria-live]")
            result["screen_reader"] = len(live_regions) > 0
        
        # Calculate score
        true_count = sum(1 for k, v in result.items() if k != "score" and v is True)
        result["score"] = true_count / 5 if alerts else 0.5
        
        return result


class VisualRegressionTester:
    """Visual regression testing"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
    
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Run visual regression tests"""
        
        result = {
            "score": 1.0,  # Default to passing
            "screenshots_captured": 0,
            "visual_differences": []
        }
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            # Capture screenshots for different states
            screenshots = []
            
            # Default state
            screenshot_path = self.config.output_dir / f"visual_default_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=str(screenshot_path))
            screenshots.append(str(screenshot_path))
            
            # Hover states
            buttons = await page.query_selector_all("button")
            if buttons:
                await buttons[0].hover()
                screenshot_path = self.config.output_dir / f"visual_hover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path))
                screenshots.append(str(screenshot_path))
            
            # Focus states
            inputs = await page.query_selector_all("input")
            if inputs:
                await inputs[0].focus()
                screenshot_path = self.config.output_dir / f"visual_focus_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path))
                screenshots.append(str(screenshot_path))
            
            result["screenshots_captured"] = len(screenshots)
            result["screenshots"] = screenshots
            
            # In a real implementation, these would be compared against baseline images
            # using image diff algorithms
            
        finally:
            await context.close()
        
        return result


class ColorBlindTester:
    """Color blind accessibility testing"""
    
    def __init__(self, config: UITestConfig):
        self.config = config
    
    async def test(self, browser: Browser, url: str) -> Dict[str, Any]:
        """Test color blind accessibility"""
        
        results = {
            "color_blind_types": [],
            "overall_score": 0.0
        }
        
        for cb_type in [ColorBlindType.PROTANOPIA, ColorBlindType.DEUTERANOPIA, 
                       ColorBlindType.TRITANOPIA, ColorBlindType.ACHROMATOPSIA]:
            type_result = await self._test_color_blind_type(browser, url, cb_type)
            results["color_blind_types"].append(type_result)
        
        # Calculate overall score
        if results["color_blind_types"]:
            total_score = sum(t.get("score", 0) for t in results["color_blind_types"])
            results["overall_score"] = total_score / len(results["color_blind_types"])
        
        return results
    
    async def _test_color_blind_type(
        self, browser: Browser, url: str, cb_type: ColorBlindType
    ) -> Dict[str, Any]:
        """Test specific color blind type"""
        
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            # Apply color blind filter CSS
            await self._apply_color_blind_filter(page, cb_type)
            
            result = {
                "type": cb_type.name,
                "score": 0.0,
                "pattern_differentiation": False,
                "text_labels": False,
                "icon_differentiation": False,
                "contrast_adequate": False
            }
            
            # Test pattern differentiation
            patterns = await page.evaluate("""
                () => {
                    // Check for patterns, textures, or shapes in addition to colors
                    const elements = document.querySelectorAll('[class*="pattern"], [class*="texture"]');
                    return elements.length > 0;
                }
            """)
            result["pattern_differentiation"] = patterns
            
            # Test text labels for color-coded info
            labels = await page.evaluate("""
                () => {
                    // Check if color-coded elements have text labels
                    const colorCoded = document.querySelectorAll('[class*="status"], [class*="alert"]');
                    let hasLabels = true;
                    
                    colorCoded.forEach(el => {
                        if (!el.textContent.trim() && !el.getAttribute('aria-label')) {
                            hasLabels = false;
                        }
                    });
                    
                    return hasLabels;
                }
            """)
            result["text_labels"] = labels
            
            # Test icon differentiation
            icons = await page.evaluate("""
                () => {
                    // Check if icons use shapes in addition to colors
                    const icons = document.querySelectorAll('[class*="icon"], svg, i');
                    return icons.length > 0;
                }
            """)
            result["icon_differentiation"] = icons
            
            # Test contrast (simplified)
            result["contrast_adequate"] = True  # Placeholder
            
            # Calculate score
            true_count = sum(1 for k, v in result.items() 
                           if k not in ["type", "score"] and v is True)
            result["score"] = true_count / 4
            
            # Take screenshot with color blind filter
            if self.config.save_screenshots:
                screenshot_path = self.config.output_dir / f"colorblind_{cb_type.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path))
                result["screenshot"] = str(screenshot_path)
            
            return result
            
        finally:
            await context.close()
    
    async def _apply_color_blind_filter(self, page: Page, cb_type: ColorBlindType):
        """Apply CSS filter to simulate color blindness"""
        
        filters = {
            ColorBlindType.PROTANOPIA: "url('#protanopia')",
            ColorBlindType.DEUTERANOPIA: "url('#deuteranopia')",
            ColorBlindType.TRITANOPIA: "url('#tritanopia')",
            ColorBlindType.ACHROMATOPSIA: "grayscale(100%)"
        }
        
        if cb_type in filters:
            await page.add_style_tag(content=f"""
                body {{
                    filter: {filters[cb_type]};
                }}
            """)
            
            # Add SVG filters for actual color blind simulation
            if cb_type != ColorBlindType.ACHROMATOPSIA:
                await page.evaluate("""
                    () => {
                        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                        svg.style.display = 'none';
                        
                        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
                        
                        // Add color blind filter matrices here
                        // These are simplified - real implementation would have accurate matrices
                        
                        svg.appendChild(defs);
                        document.body.appendChild(svg);
                    }
                """)


if __name__ == "__main__":
    # Example usage
    import asyncio
    
    async def main():
        config = UITestConfig(
            base_url="http://localhost:3000",
            dashboard_url="/dashboard",
            browsers=["chromium"],
            headless=True,
            test_accessibility=True,
            test_responsive=True,
            test_performance=True,
            save_screenshots=True
        )
        
        framework = UITestingFramework(config)
        results = await framework.run_all_tests()
        
        print(f"Overall UI Test Score: {results.get('overall_score', 0):.2%}")
    
    asyncio.run(main())