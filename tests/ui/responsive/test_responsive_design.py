"""
Responsive Design Testing Module
Comprehensive viewport and device testing for M011 Dashboard
"""

import asyncio
import json
import logging
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
    ResponsiveTester,
    UITestConfig,
    ViewportSize,
    ResponsiveResult
)

logger = logging.getLogger(__name__)


class DeviceProfile:
    """Device profiles for testing"""
    
    DEVICES = {
        # Mobile Phones
        "iPhone SE": {
            "viewport": (375, 667),
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True
        },
        "iPhone 12": {
            "viewport": (390, 844),
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            "device_scale_factor": 3,
            "is_mobile": True,
            "has_touch": True
        },
        "iPhone 14 Pro Max": {
            "viewport": (430, 932),
            "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)",
            "device_scale_factor": 3,
            "is_mobile": True,
            "has_touch": True
        },
        "Samsung Galaxy S20": {
            "viewport": (360, 800),
            "user_agent": "Mozilla/5.0 (Linux; Android 11; SM-G981B)",
            "device_scale_factor": 3,
            "is_mobile": True,
            "has_touch": True
        },
        "Google Pixel 5": {
            "viewport": (393, 851),
            "user_agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5)",
            "device_scale_factor": 2.625,
            "is_mobile": True,
            "has_touch": True
        },
        
        # Tablets
        "iPad Mini": {
            "viewport": (768, 1024),
            "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)",
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True
        },
        "iPad Pro 11": {
            "viewport": (834, 1194),
            "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)",
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True
        },
        "iPad Pro 12.9": {
            "viewport": (1024, 1366),
            "user_agent": "Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X)",
            "device_scale_factor": 2,
            "is_mobile": True,
            "has_touch": True
        },
        "Surface Pro 7": {
            "viewport": (912, 1368),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "device_scale_factor": 1.5,
            "is_mobile": False,
            "has_touch": True
        },
        
        # Desktops
        "Desktop HD": {
            "viewport": (1920, 1080),
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "device_scale_factor": 1,
            "is_mobile": False,
            "has_touch": False
        },
        "Desktop QHD": {
            "viewport": (2560, 1440),
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "device_scale_factor": 2,
            "is_mobile": False,
            "has_touch": False
        },
        "Desktop 4K": {
            "viewport": (3840, 2160),
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64)",
            "device_scale_factor": 1.5,
            "is_mobile": False,
            "has_touch": False
        }
    }


@dataclass
class BreakpointTest:
    """Breakpoint test configuration"""
    name: str
    min_width: int
    max_width: int
    expected_layout: str
    critical_elements: List[str]


class ResponsiveDesignTester:
    """Comprehensive responsive design testing"""
    
    def __init__(self, config: Optional[UITestConfig] = None):
        self.config = config or UITestConfig()
        self.breakpoints = self._define_breakpoints()
        self.results: Dict[str, Any] = {}
        
    def _define_breakpoints(self) -> List[BreakpointTest]:
        """Define standard breakpoints to test"""
        return [
            BreakpointTest(
                name="Mobile Small",
                min_width=320,
                max_width=374,
                expected_layout="mobile",
                critical_elements=["nav-hamburger", "mobile-header", "bottom-nav"]
            ),
            BreakpointTest(
                name="Mobile Medium",
                min_width=375,
                max_width=424,
                expected_layout="mobile",
                critical_elements=["nav-hamburger", "mobile-header", "bottom-nav"]
            ),
            BreakpointTest(
                name="Mobile Large",
                min_width=425,
                max_width=767,
                expected_layout="mobile",
                critical_elements=["nav-hamburger", "mobile-header"]
            ),
            BreakpointTest(
                name="Tablet Portrait",
                min_width=768,
                max_width=1023,
                expected_layout="tablet",
                critical_elements=["sidebar-collapsed", "tablet-nav"]
            ),
            BreakpointTest(
                name="Tablet Landscape",
                min_width=1024,
                max_width=1439,
                expected_layout="tablet-wide",
                critical_elements=["sidebar-expanded", "desktop-nav"]
            ),
            BreakpointTest(
                name="Desktop",
                min_width=1440,
                max_width=1919,
                expected_layout="desktop",
                critical_elements=["sidebar-expanded", "desktop-nav", "breadcrumbs"]
            ),
            BreakpointTest(
                name="Desktop Wide",
                min_width=1920,
                max_width=3840,
                expected_layout="desktop-wide",
                critical_elements=["sidebar-expanded", "desktop-nav", "breadcrumbs", "side-panel"]
            )
        ]
    
    async def test_all_devices(self, browser, url: str) -> Dict[str, Any]:
        """Test across all device profiles"""
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "devices_tested": [],
            "breakpoints_tested": [],
            "issues": [],
            "summary": {
                "total_devices": len(DeviceProfile.DEVICES),
                "passed": 0,
                "failed": 0,
                "overall_score": 0.0
            }
        }
        
        # Test each device profile
        for device_name, device_config in DeviceProfile.DEVICES.items():
            device_result = await self._test_device(
                browser, url, device_name, device_config
            )
            results["devices_tested"].append(device_result)
            
            if device_result["passed"]:
                results["summary"]["passed"] += 1
            else:
                results["summary"]["failed"] += 1
        
        # Test breakpoints
        for breakpoint in self.breakpoints:
            breakpoint_result = await self._test_breakpoint(
                browser, url, breakpoint
            )
            results["breakpoints_tested"].append(breakpoint_result)
        
        # Calculate overall score
        if results["summary"]["total_devices"] > 0:
            results["summary"]["overall_score"] = (
                results["summary"]["passed"] / results["summary"]["total_devices"]
            )
        
        return results
    
    async def _test_device(
        self, browser, url: str, device_name: str, device_config: Dict
    ) -> Dict[str, Any]:
        """Test specific device configuration"""
        
        context = await browser.new_context(
            viewport={
                "width": device_config["viewport"][0],
                "height": device_config["viewport"][1]
            },
            user_agent=device_config["user_agent"],
            device_scale_factor=device_config["device_scale_factor"],
            is_mobile=device_config["is_mobile"],
            has_touch=device_config["has_touch"]
        )
        
        page = await context.new_page()
        
        try:
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            
            result = {
                "device": device_name,
                "viewport": device_config["viewport"],
                "is_mobile": device_config["is_mobile"],
                "passed": True,
                "tests": {}
            }
            
            # Run specific tests
            result["tests"]["layout"] = await self._test_layout_integrity(
                page, device_config["viewport"][0], device_config["viewport"][1]
            )
            
            result["tests"]["content_visibility"] = await self._test_content_visibility(page)
            
            result["tests"]["navigation"] = await self._test_navigation_adaptation(
                page, device_config["is_mobile"]
            )
            
            result["tests"]["touch_targets"] = await self._test_touch_targets(
                page, device_config["has_touch"]
            )
            
            result["tests"]["text_scaling"] = await self._test_text_scaling(page)
            
            result["tests"]["images"] = await self._test_image_optimization(
                page, device_config["viewport"][0]
            )
            
            result["tests"]["forms"] = await self._test_form_adaptation(
                page, device_config["is_mobile"]
            )
            
            # Check if all tests passed
            result["passed"] = all(
                test.get("passed", False) for test in result["tests"].values()
            )
            
            # Take screenshot if configured
            if self.config.save_screenshots:
                screenshot_path = self.config.output_dir / f"responsive_{device_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)
                result["screenshot"] = str(screenshot_path)
            
            return result
            
        finally:
            await context.close()
    
    async def _test_breakpoint(
        self, browser, url: str, breakpoint: BreakpointTest
    ) -> Dict[str, Any]:
        """Test specific breakpoint"""
        
        # Test at the minimum, middle, and maximum of the breakpoint range
        test_widths = [
            breakpoint.min_width,
            (breakpoint.min_width + breakpoint.max_width) // 2,
            breakpoint.max_width
        ]
        
        result = {
            "breakpoint": breakpoint.name,
            "range": f"{breakpoint.min_width}px - {breakpoint.max_width}px",
            "expected_layout": breakpoint.expected_layout,
            "tests": [],
            "passed": True
        }
        
        for width in test_widths:
            context = await browser.new_context(
                viewport={"width": width, "height": 800}
            )
            page = await context.new_page()
            
            try:
                await page.goto(url)
                await page.wait_for_load_state("networkidle")
                
                test_result = {
                    "width": width,
                    "layout_correct": True,
                    "elements_present": True,
                    "no_overflow": True
                }
                
                # Check for expected layout
                layout_class = await page.evaluate(f"""
                    () => {{
                        const body = document.body;
                        return body.className.includes('{breakpoint.expected_layout}');
                    }}
                """)
                test_result["layout_correct"] = layout_class
                
                # Check for critical elements
                for element in breakpoint.critical_elements:
                    element_present = await page.evaluate(f"""
                        () => {{
                            const element = document.querySelector('.{element}') || 
                                          document.querySelector('#{element}');
                            return element !== null;
                        }}
                    """)
                    if not element_present:
                        test_result["elements_present"] = False
                        break
                
                # Check for horizontal overflow
                has_overflow = await page.evaluate("""
                    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
                """)
                test_result["no_overflow"] = not has_overflow
                
                result["tests"].append(test_result)
                
                if not all([test_result["layout_correct"], 
                          test_result["elements_present"], 
                          test_result["no_overflow"]]):
                    result["passed"] = False
                    
            finally:
                await context.close()
        
        return result
    
    async def _test_layout_integrity(
        self, page, width: int, height: int
    ) -> Dict[str, Any]:
        """Test layout integrity at specific viewport"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        # Check for horizontal scrolling
        has_horizontal_scroll = await page.evaluate("""
            () => document.documentElement.scrollWidth > document.documentElement.clientWidth
        """)
        
        if has_horizontal_scroll:
            result["passed"] = False
            result["issues"].append("Horizontal scrolling detected")
        
        # Check for overlapping elements
        overlaps = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('header, nav, main, footer, aside');
                const overlapping = [];
                
                for (let i = 0; i < elements.length; i++) {
                    for (let j = i + 1; j < elements.length; j++) {
                        const rect1 = elements[i].getBoundingClientRect();
                        const rect2 = elements[j].getBoundingClientRect();
                        
                        const overlap = !(rect1.right < rect2.left || 
                                        rect1.left > rect2.right || 
                                        rect1.bottom < rect2.top || 
                                        rect1.top > rect2.bottom);
                        
                        if (overlap) {
                            overlapping.push({
                                element1: elements[i].tagName,
                                element2: elements[j].tagName
                            });
                        }
                    }
                }
                
                return overlapping;
            }
        """)
        
        if overlaps:
            result["passed"] = False
            result["issues"].append(f"Overlapping elements: {len(overlaps)}")
        
        # Check for cut-off content
        cutoff = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('*');
                let cutoffCount = 0;
                
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.right > window.innerWidth || rect.left < 0) {
                        cutoffCount++;
                    }
                });
                
                return cutoffCount;
            }
        """)
        
        if cutoff > 0:
            result["passed"] = False
            result["issues"].append(f"Content cut off: {cutoff} elements")
        
        return result
    
    async def _test_content_visibility(self, page) -> Dict[str, Any]:
        """Test critical content visibility"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        # Critical elements that must be visible
        critical_selectors = [
            "h1", ".dashboard-title", ".critical-alert",
            "nav", ".main-navigation", ".user-menu"
        ]
        
        for selector in critical_selectors:
            visible = await page.evaluate(f"""
                (selector) => {{
                    const element = document.querySelector(selector);
                    if (!element) return false;
                    
                    const rect = element.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0 && 
                           rect.top < window.innerHeight && 
                           rect.bottom > 0;
                }}
            """, selector)
            
            if not visible:
                result["passed"] = False
                result["issues"].append(f"Critical element not visible: {selector}")
        
        return result
    
    async def _test_navigation_adaptation(self, page, is_mobile: bool) -> Dict[str, Any]:
        """Test navigation adaptation for device type"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        if is_mobile:
            # Check for mobile navigation (hamburger menu)
            has_hamburger = await page.evaluate("""
                () => {
                    const hamburger = document.querySelector('.hamburger, .menu-toggle, [aria-label*="menu"]');
                    return hamburger !== null;
                }
            """)
            
            if not has_hamburger:
                result["passed"] = False
                result["issues"].append("Mobile navigation (hamburger menu) not found")
            
            # Check that desktop nav is hidden
            desktop_nav_visible = await page.evaluate("""
                () => {
                    const nav = document.querySelector('.desktop-nav, nav.horizontal');
                    if (!nav) return false;
                    
                    const style = getComputedStyle(nav);
                    return style.display !== 'none' && style.visibility !== 'hidden';
                }
            """)
            
            if desktop_nav_visible:
                result["passed"] = False
                result["issues"].append("Desktop navigation visible on mobile")
        else:
            # Check for desktop navigation
            has_desktop_nav = await page.evaluate("""
                () => {
                    const nav = document.querySelector('nav, .main-navigation');
                    if (!nav) return false;
                    
                    const rect = nav.getBoundingClientRect();
                    return rect.width > 0 && rect.height > 0;
                }
            """)
            
            if not has_desktop_nav:
                result["passed"] = False
                result["issues"].append("Desktop navigation not found")
        
        return result
    
    async def _test_touch_targets(self, page, has_touch: bool) -> Dict[str, Any]:
        """Test touch target sizes for touch devices"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        if not has_touch:
            return result  # Skip for non-touch devices
        
        # Minimum touch target size (48x48px as per WCAG)
        min_size = 48
        
        non_compliant = await page.evaluate(f"""
            (minSize) => {{
                const interactive = document.querySelectorAll('button, a, input, select, [role="button"]');
                const nonCompliant = [];
                
                interactive.forEach(el => {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width < minSize || rect.height < minSize) {{
                        nonCompliant.push({{
                            element: el.tagName,
                            class: el.className,
                            width: rect.width,
                            height: rect.height
                        }});
                    }}
                }});
                
                return nonCompliant;
            }}
        """, min_size)
        
        if non_compliant:
            result["passed"] = False
            result["issues"].append(f"Touch targets too small: {len(non_compliant)} elements")
            result["details"] = non_compliant[:5]  # First 5 for brevity
        
        # Check for adequate spacing between touch targets
        spacing_issues = await page.evaluate("""
            () => {
                const interactive = document.querySelectorAll('button, a, input');
                const spacingIssues = [];
                const minSpacing = 8;  // Minimum 8px between targets
                
                for (let i = 0; i < interactive.length; i++) {
                    for (let j = i + 1; j < interactive.length; j++) {
                        const rect1 = interactive[i].getBoundingClientRect();
                        const rect2 = interactive[j].getBoundingClientRect();
                        
                        const horizontalSpace = Math.min(
                            Math.abs(rect1.right - rect2.left),
                            Math.abs(rect2.right - rect1.left)
                        );
                        
                        const verticalSpace = Math.min(
                            Math.abs(rect1.bottom - rect2.top),
                            Math.abs(rect2.bottom - rect1.top)
                        );
                        
                        if ((horizontalSpace < minSpacing && horizontalSpace > 0) || 
                            (verticalSpace < minSpacing && verticalSpace > 0)) {
                            spacingIssues.push({
                                element1: interactive[i].tagName,
                                element2: interactive[j].tagName
                            });
                        }
                    }
                }
                
                return spacingIssues;
            }
        """)
        
        if spacing_issues:
            result["passed"] = False
            result["issues"].append(f"Insufficient spacing between touch targets: {len(spacing_issues)} pairs")
        
        return result
    
    async def _test_text_scaling(self, page) -> Dict[str, Any]:
        """Test text scaling and readability"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        # Test text can scale to 200% without breaking layout
        await page.evaluate("document.body.style.fontSize = '200%'")
        
        # Check for overflow after scaling
        has_overflow = await page.evaluate("""
            () => {
                return document.documentElement.scrollWidth > document.documentElement.clientWidth ||
                       document.body.scrollWidth > document.body.clientWidth;
            }
        """)
        
        if has_overflow:
            result["passed"] = False
            result["issues"].append("Text scaling to 200% causes horizontal overflow")
        
        # Reset font size
        await page.evaluate("document.body.style.fontSize = ''")
        
        # Check minimum font sizes
        small_text = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('p, span, a, li, td');
                const smallText = [];
                const minSize = 12;  // Minimum 12px for body text
                
                elements.forEach(el => {
                    const fontSize = parseFloat(getComputedStyle(el).fontSize);
                    if (fontSize < minSize) {
                        smallText.push({
                            element: el.tagName,
                            fontSize: fontSize,
                            text: el.textContent.substring(0, 30)
                        });
                    }
                });
                
                return smallText;
            }
        """)
        
        if small_text:
            result["passed"] = False
            result["issues"].append(f"Text too small: {len(small_text)} elements below 12px")
            result["details"] = small_text[:5]
        
        return result
    
    async def _test_image_optimization(self, page, viewport_width: int) -> Dict[str, Any]:
        """Test image optimization for viewport"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        images = await page.evaluate("""
            () => {
                const images = document.querySelectorAll('img');
                return Array.from(images).map(img => ({
                    src: img.src,
                    naturalWidth: img.naturalWidth,
                    displayWidth: img.getBoundingClientRect().width,
                    hasAlt: img.hasAttribute('alt'),
                    loading: img.loading,
                    srcset: img.srcset
                }));
            }
        """)
        
        for img in images:
            # Check for oversized images
            if img["naturalWidth"] > img["displayWidth"] * 2:
                result["issues"].append(
                    f"Oversized image: {img['naturalWidth']}px natural, "
                    f"{img['displayWidth']}px displayed"
                )
            
            # Check for responsive images on small viewports
            if viewport_width < 768 and not img["srcset"]:
                result["issues"].append("Image missing srcset for responsive loading")
            
            # Check for lazy loading on images below fold
            if not img["loading"]:
                result["issues"].append("Image missing lazy loading attribute")
        
        if result["issues"]:
            result["passed"] = False
        
        return result
    
    async def _test_form_adaptation(self, page, is_mobile: bool) -> Dict[str, Any]:
        """Test form adaptation for device type"""
        
        result = {
            "passed": True,
            "issues": []
        }
        
        forms = await page.query_selector_all("form")
        
        for form in forms:
            if is_mobile:
                # Check for appropriate input types on mobile
                inputs = await form.query_selector_all("input")
                
                for input_field in inputs:
                    input_type = await input_field.get_attribute("type")
                    input_name = await input_field.get_attribute("name")
                    
                    # Check for appropriate input types
                    if input_name and "email" in input_name.lower() and input_type != "email":
                        result["issues"].append(f"Email input should use type='email' on mobile")
                    
                    if input_name and "phone" in input_name.lower() and input_type != "tel":
                        result["issues"].append(f"Phone input should use type='tel' on mobile")
                    
                    if input_name and "date" in input_name.lower() and input_type != "date":
                        result["issues"].append(f"Date input should use type='date' on mobile")
                
                # Check for stacked layout on mobile
                form_width = await form.evaluate("el => el.getBoundingClientRect().width")
                if form_width > 400:  # Forms should be narrow on mobile
                    result["issues"].append("Form too wide for mobile viewport")
            else:
                # Check for appropriate layout on desktop
                labels = await form.query_selector_all("label")
                inputs = await form.query_selector_all("input, select, textarea")
                
                if len(labels) != len(inputs):
                    result["issues"].append("Mismatch between labels and inputs")
        
        if result["issues"]:
            result["passed"] = False
        
        return result


# Test Cases

@pytest.mark.asyncio
class TestResponsiveDesign:
    """Test suite for responsive design"""
    
    async def test_mobile_viewports(self):
        """Test mobile viewport adaptations"""
        config = UITestConfig()
        tester = ResponsiveDesignTester(config)
        
        # Mock browser and page
        browser = Mock()
        context = Mock()
        page = Mock()
        
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()
        
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock(return_value=False)
        page.query_selector_all = AsyncMock(return_value=[])
        
        # Test iPhone SE viewport
        device_config = DeviceProfile.DEVICES["iPhone SE"]
        result = await tester._test_device(
            browser, "http://localhost:3000", "iPhone SE", device_config
        )
        
        assert result["device"] == "iPhone SE"
        assert result["viewport"] == (375, 667)
        assert result["is_mobile"] is True
    
    async def test_tablet_viewports(self):
        """Test tablet viewport adaptations"""
        config = UITestConfig()
        tester = ResponsiveDesignTester(config)
        
        # Mock setup
        browser = Mock()
        context = Mock()
        page = Mock()
        
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()
        
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock(return_value=True)
        page.query_selector_all = AsyncMock(return_value=[])
        
        # Test iPad Pro viewport
        device_config = DeviceProfile.DEVICES["iPad Pro 11"]
        result = await tester._test_device(
            browser, "http://localhost:3000", "iPad Pro 11", device_config
        )
        
        assert result["device"] == "iPad Pro 11"
        assert result["viewport"] == (834, 1194)
    
    async def test_desktop_viewports(self):
        """Test desktop viewport adaptations"""
        config = UITestConfig()
        tester = ResponsiveDesignTester(config)
        
        # Mock setup
        browser = Mock()
        context = Mock()
        page = Mock()
        
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()
        
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock(return_value=True)
        page.query_selector_all = AsyncMock(return_value=[])
        
        # Test 4K desktop viewport
        device_config = DeviceProfile.DEVICES["Desktop 4K"]
        result = await tester._test_device(
            browser, "http://localhost:3000", "Desktop 4K", device_config
        )
        
        assert result["device"] == "Desktop 4K"
        assert result["viewport"] == (3840, 2160)
        assert result["is_mobile"] is False
    
    async def test_breakpoint_transitions(self):
        """Test breakpoint transitions"""
        config = UITestConfig()
        tester = ResponsiveDesignTester(config)
        
        # Test mobile to tablet transition
        breakpoint = BreakpointTest(
            name="Mobile to Tablet",
            min_width=767,
            max_width=769,
            expected_layout="tablet",
            critical_elements=["sidebar"]
        )
        
        # Mock browser
        browser = Mock()
        context = Mock()
        page = Mock()
        
        browser.new_context = AsyncMock(return_value=context)
        context.new_page = AsyncMock(return_value=page)
        context.close = AsyncMock()
        
        page.goto = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        page.evaluate = AsyncMock(return_value=True)
        
        result = await tester._test_breakpoint(
            browser, "http://localhost:3000", breakpoint
        )
        
        assert result["breakpoint"] == "Mobile to Tablet"
        assert result["range"] == "767px - 769px"
    
    async def test_touch_target_compliance(self):
        """Test touch target size compliance"""
        config = UITestConfig()
        tester = ResponsiveDesignTester(config)
        
        # Mock page
        page = Mock()
        page.evaluate = AsyncMock(return_value=[])  # No non-compliant elements
        
        result = await tester._test_touch_targets(page, has_touch=True)
        
        assert result["passed"] is True
        assert len(result["issues"]) == 0
        
        # Test with non-compliant elements
        page.evaluate = AsyncMock(return_value=[
            {"element": "BUTTON", "width": 30, "height": 30}
        ])
        
        result = await tester._test_touch_targets(page, has_touch=True)
        
        assert result["passed"] is False
        assert "Touch targets too small" in result["issues"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])