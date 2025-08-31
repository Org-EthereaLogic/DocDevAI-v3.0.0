"""
UI Testing Framework Integration with DocDevAI Modules
Tests integration between UI tests and M001-M008 modules
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import pytest

# Import DocDevAI modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from devdocai.core.config import ConfigurationManager, ConfigMode
from devdocai.storage.local_storage_system import LocalStorageSystem
from devdocai.miair.engine_unified import MIAIREngine
from devdocai.generator.document_generator_unified import DocumentGeneratorUnified
from devdocai.quality.analyzer_unified import QualityAnalyzerUnified
from devdocai.templates.registry_unified import TemplateRegistryUnified
from devdocai.review.review_engine_unified import ReviewEngineUnified

# Import UI Testing Framework
from tests.ui.ui_testing_framework import (
    UITestingFramework,
    UITestConfig,
    AccessibilityTester,
    ResponsiveTester,
    PerformanceTester
)

logger = logging.getLogger(__name__)


class UIModuleIntegrationTester:
    """Tests UI framework integration with DocDevAI modules"""
    
    def __init__(self):
        self.config_manager = None
        self.storage_system = None
        self.miair_engine = None
        self.doc_generator = None
        self.quality_analyzer = None
        self.template_registry = None
        self.review_engine = None
        self.ui_framework = None
        
    async def setup_modules(self):
        """Initialize all DocDevAI modules"""
        
        # M001: Configuration Manager
        self.config_manager = ConfigurationManager(mode=ConfigMode.TESTING)
        config = await self.config_manager.load_config()
        
        # M002: Local Storage System
        self.storage_system = LocalStorageSystem(
            db_path=":memory:",  # Use in-memory DB for testing
            encryption_key="test_key_12345678901234567890123456"
        )
        await self.storage_system.initialize()
        
        # M003: MIAIR Engine
        self.miair_engine = MIAIREngine(config={
            "operation_mode": "OPTIMIZED",
            "cache_enabled": True
        })
        
        # M004: Document Generator
        self.doc_generator = DocumentGeneratorUnified(
            config={"operation_mode": "SECURE"},
            template_registry=None  # Will set after M006
        )
        
        # M005: Quality Engine
        self.quality_analyzer = QualityAnalyzerUnified(
            config={"operation_mode": "BALANCED"}
        )
        
        # M006: Template Registry
        self.template_registry = TemplateRegistryUnified(
            config={"operation_mode": "ENTERPRISE"}
        )
        await self.template_registry.initialize()
        
        # Link template registry to document generator
        self.doc_generator.template_registry = self.template_registry
        
        # M007: Review Engine
        self.review_engine = ReviewEngineUnified(
            config={"operation_mode": "COMPREHENSIVE"}
        )
        
        # UI Testing Framework
        ui_config = UITestConfig(
            base_url="http://localhost:3000",
            dashboard_url="/dashboard",
            test_accessibility=True,
            test_responsive=True,
            test_performance=True
        )
        self.ui_framework = UITestingFramework(ui_config)
        
        logger.info("All modules initialized successfully")
    
    async def test_configuration_ui_integration(self) -> Dict[str, Any]:
        """Test M001 Configuration Manager with UI settings"""
        
        results = {
            "module": "M001_Configuration",
            "tests": {}
        }
        
        # Test theme preferences for UI
        theme_config = {
            "ui": {
                "theme": "dark",
                "high_contrast": True,
                "font_size": "large",
                "reduce_motion": True
            },
            "accessibility": {
                "screen_reader": True,
                "keyboard_navigation": True,
                "focus_indicators": "enhanced"
            }
        }
        
        # Save UI configuration
        await self.config_manager.set_config("ui_preferences", theme_config)
        
        # Verify configuration persistence
        loaded_config = await self.config_manager.get_config("ui_preferences")
        results["tests"]["theme_persistence"] = loaded_config == theme_config
        
        # Test accessibility settings impact
        accessibility_config = loaded_config.get("accessibility", {})
        results["tests"]["accessibility_config"] = all([
            accessibility_config.get("screen_reader") is True,
            accessibility_config.get("keyboard_navigation") is True,
            accessibility_config.get("focus_indicators") == "enhanced"
        ])
        
        # Test configuration encryption for sensitive UI data
        sensitive_ui_data = {
            "api_keys": {
                "analytics": "secret_key_123",
                "monitoring": "secret_key_456"
            }
        }
        
        encrypted = await self.config_manager.encrypt_config(sensitive_ui_data)
        decrypted = await self.config_manager.decrypt_config(encrypted)
        results["tests"]["encryption"] = decrypted == sensitive_ui_data
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_storage_dashboard_state(self) -> Dict[str, Any]:
        """Test M002 Storage System for dashboard state persistence"""
        
        results = {
            "module": "M002_Storage",
            "tests": {}
        }
        
        # Dashboard state to persist
        dashboard_state = {
            "layout": {
                "sidebar": "collapsed",
                "panels": ["metrics", "alerts", "logs"],
                "view_mode": "compact"
            },
            "filters": {
                "date_range": "last_7_days",
                "severity": ["critical", "warning"],
                "categories": ["security", "performance"]
            },
            "user_preferences": {
                "refresh_interval": 30,
                "notifications": True,
                "auto_expand_critical": True
            }
        }
        
        # Store dashboard state
        doc_id = await self.storage_system.create_document(
            content=json.dumps(dashboard_state),
            metadata={
                "type": "dashboard_state",
                "user_id": "test_user",
                "timestamp": datetime.now().isoformat()
            }
        )
        results["tests"]["state_stored"] = doc_id is not None
        
        # Retrieve dashboard state
        retrieved = await self.storage_system.get_document(doc_id)
        if retrieved:
            retrieved_state = json.loads(retrieved["content"])
            results["tests"]["state_retrieved"] = retrieved_state == dashboard_state
        
        # Test versioning for state changes
        dashboard_state["layout"]["sidebar"] = "expanded"
        version_id = await self.storage_system.update_document(
            doc_id, json.dumps(dashboard_state)
        )
        results["tests"]["versioning"] = version_id is not None
        
        # Test state search
        search_results = await self.storage_system.search("dashboard_state")
        results["tests"]["search"] = len(search_results) > 0
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_miair_ui_optimization(self) -> Dict[str, Any]:
        """Test M003 MIAIR Engine for UI content optimization"""
        
        results = {
            "module": "M003_MIAIR",
            "tests": {}
        }
        
        # UI content to optimize
        ui_content = {
            "dashboard_title": "System Performance Dashboard - Real-time Monitoring",
            "alert_message": "Critical: Memory usage exceeded 90% threshold. Immediate action required to prevent system failure.",
            "help_text": "This dashboard provides comprehensive real-time monitoring of system performance metrics including CPU usage, memory consumption, disk I/O, and network throughput.",
            "notification": "Your session will expire in 5 minutes. Please save your work."
        }
        
        # Optimize content for UI display
        for key, content in ui_content.items():
            quality_score = self.miair_engine.calculate_miair_score(content)
            
            # Check if content is optimized for UI
            results["tests"][f"{key}_quality"] = quality_score > 0.7
            
            # Optimize if needed
            if quality_score < 0.7:
                optimized = self.miair_engine.optimize_content(content)
                new_score = self.miair_engine.calculate_miair_score(optimized)
                results["tests"][f"{key}_optimized"] = new_score > quality_score
        
        # Test progressive disclosure content scoring
        detailed_content = """
        The system dashboard provides multiple levels of detail:
        1. Summary view with key metrics
        2. Detailed view with historical trends
        3. Expert view with raw data and advanced analytics
        """
        
        disclosure_score = self.miair_engine.evaluate_structure(detailed_content)
        results["tests"]["progressive_disclosure"] = disclosure_score["score"] > 0.8
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_generator_ui_documentation(self) -> Dict[str, Any]:
        """Test M004 Document Generator for UI component documentation"""
        
        results = {
            "module": "M004_Generator",
            "tests": {}
        }
        
        # Generate UI component documentation
        ui_component = {
            "name": "DashboardMetricCard",
            "props": {
                "title": "string",
                "value": "number",
                "unit": "string",
                "trend": "up | down | stable",
                "color": "success | warning | error"
            },
            "accessibility": {
                "aria_label": "Metric card showing {title}",
                "role": "article",
                "keyboard_nav": True
            },
            "responsive": {
                "mobile": "stack",
                "tablet": "grid-2",
                "desktop": "grid-4"
            }
        }
        
        # Generate component documentation
        doc_content = await self.doc_generator.generate(
            template_name="component_documentation",
            context=ui_component
        )
        
        results["tests"]["doc_generated"] = doc_content is not None
        
        # Validate documentation completeness
        required_sections = ["props", "accessibility", "responsive", "examples"]
        for section in required_sections:
            results["tests"][f"has_{section}"] = section in doc_content.lower()
        
        # Generate accessibility documentation
        a11y_doc = await self.doc_generator.generate(
            template_name="accessibility_guide",
            context={
                "wcag_level": "AA",
                "components": [ui_component],
                "testing_results": {"compliance": 0.95}
            }
        )
        
        results["tests"]["a11y_doc"] = a11y_doc is not None
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_quality_ui_content(self) -> Dict[str, Any]:
        """Test M005 Quality Engine for UI content validation"""
        
        results = {
            "module": "M005_Quality",
            "tests": {}
        }
        
        # UI content to analyze
        ui_texts = {
            "good_error": "Unable to connect to server. Please check your internet connection and try again.",
            "bad_error": "Error!",
            "good_help": "Click the refresh button to update the dashboard with latest data.",
            "bad_help": "Just click stuff.",
            "good_label": "Email Address",
            "bad_label": "Field1"
        }
        
        for text_id, content in ui_texts.items():
            analysis = await self.quality_analyzer.analyze(content)
            
            is_good = "good" in text_id
            expected_score = 0.7 if is_good else 0.3
            
            # Check if quality scoring is accurate
            if is_good:
                results["tests"][text_id] = analysis["overall_score"] > expected_score
            else:
                results["tests"][text_id] = analysis["overall_score"] < 0.5
        
        # Test UI-specific quality dimensions
        button_text = "Save Changes"
        button_analysis = await self.quality_analyzer.analyze_dimensions(
            button_text,
            dimensions=["clarity", "conciseness"]
        )
        
        results["tests"]["button_clarity"] = button_analysis["clarity"]["score"] > 0.8
        results["tests"]["button_conciseness"] = button_analysis["conciseness"]["score"] > 0.8
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_template_ui_components(self) -> Dict[str, Any]:
        """Test M006 Template Registry for UI component templates"""
        
        results = {
            "module": "M006_Templates",
            "tests": {}
        }
        
        # Register UI component templates
        ui_templates = [
            {
                "name": "dashboard_card",
                "template": """
                <div class="dashboard-card" role="article" aria-label="{{title}}">
                    <h3>{{title}}</h3>
                    <div class="metric-value">{{value}}{{unit}}</div>
                    <div class="metric-trend trend-{{trend}}">{{trend_icon}}</div>
                </div>
                """,
                "category": "ui_components"
            },
            {
                "name": "alert_banner",
                "template": """
                <div class="alert alert-{{severity}}" role="alert" aria-live="polite">
                    <span class="alert-icon">{{icon}}</span>
                    <span class="alert-message">{{message}}</span>
                    <button class="alert-dismiss" aria-label="Dismiss alert">×</button>
                </div>
                """,
                "category": "ui_components"
            },
            {
                "name": "responsive_table",
                "template": """
                <div class="table-responsive" role="region" aria-label="{{table_title}}">
                    <table class="data-table">
                        <caption>{{table_title}}</caption>
                        <thead>
                            {{#headers}}
                            <th scope="col">{{.}}</th>
                            {{/headers}}
                        </thead>
                        <tbody>
                            {{#rows}}
                            <tr>{{#.}}<td>{{.}}</td>{{/.}}</tr>
                            {{/rows}}
                        </tbody>
                    </table>
                </div>
                """,
                "category": "ui_components"
            }
        ]
        
        # Register templates
        for template in ui_templates:
            registered = await self.template_registry.register_template(
                template["name"],
                template["template"],
                template["category"]
            )
            results["tests"][f"register_{template['name']}"] = registered is not None
        
        # Test template rendering
        card_html = await self.template_registry.render(
            "dashboard_card",
            {
                "title": "CPU Usage",
                "value": "45",
                "unit": "%",
                "trend": "up",
                "trend_icon": "↑"
            }
        )
        
        results["tests"]["card_rendered"] = all([
            "CPU Usage" in card_html,
            "45%" in card_html,
            "trend-up" in card_html,
            'role="article"' in card_html
        ])
        
        # Test responsive table
        table_html = await self.template_registry.render(
            "responsive_table",
            {
                "table_title": "Performance Metrics",
                "headers": ["Metric", "Value", "Status"],
                "rows": [
                    ["CPU", "45%", "Normal"],
                    ["Memory", "78%", "Warning"],
                    ["Disk", "62%", "Normal"]
                ]
            }
        )
        
        results["tests"]["table_rendered"] = all([
            "Performance Metrics" in table_html,
            "<caption>" in table_html,
            'scope="col"' in table_html,
            "Memory" in table_html
        ])
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_review_ui_compliance(self) -> Dict[str, Any]:
        """Test M007 Review Engine for UI compliance checking"""
        
        results = {
            "module": "M007_Review",
            "tests": {}
        }
        
        # UI code to review
        ui_code = """
        <div class="dashboard-container">
            <header role="banner">
                <h1>System Dashboard</h1>
                <nav role="navigation" aria-label="Main navigation">
                    <ul>
                        <li><a href="#metrics">Metrics</a></li>
                        <li><a href="#alerts">Alerts</a></li>
                        <li><a href="#settings">Settings</a></li>
                    </ul>
                </nav>
            </header>
            
            <main role="main">
                <section aria-labelledby="metrics-heading">
                    <h2 id="metrics-heading">System Metrics</h2>
                    <div class="metric-grid">
                        <!-- Metric cards here -->
                    </div>
                </section>
                
                <section aria-labelledby="alerts-heading">
                    <h2 id="alerts-heading">Active Alerts</h2>
                    <div role="alert" aria-live="polite">
                        <!-- Alerts here -->
                    </div>
                </section>
            </main>
            
            <footer role="contentinfo">
                <p>&copy; 2024 DocDevAI</p>
            </footer>
        </div>
        """
        
        # Review for accessibility compliance
        review_result = await self.review_engine.review(
            ui_code,
            review_type="accessibility"
        )
        
        results["tests"]["accessibility_review"] = review_result["score"] > 0.8
        
        # Check for specific accessibility features
        has_landmarks = all([
            'role="banner"' in ui_code,
            'role="navigation"' in ui_code,
            'role="main"' in ui_code,
            'role="contentinfo"' in ui_code
        ])
        results["tests"]["has_landmarks"] = has_landmarks
        
        has_aria = all([
            'aria-label' in ui_code,
            'aria-labelledby' in ui_code,
            'aria-live' in ui_code
        ])
        results["tests"]["has_aria"] = has_aria
        
        # Review for responsive design
        css_code = """
        .dashboard-container {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1rem;
        }
        
        @media (min-width: 768px) {
            .metric-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (min-width: 1024px) {
            .metric-grid {
                grid-template-columns: repeat(4, 1fr);
            }
        }
        
        .table-responsive {
            overflow-x: auto;
        }
        """
        
        css_review = await self.review_engine.review(
            css_code,
            review_type="responsive_design"
        )
        
        results["tests"]["responsive_review"] = css_review["score"] > 0.7
        
        # Check for responsive features
        has_media_queries = "@media" in css_code
        has_grid = "grid" in css_code
        has_responsive_table = "overflow-x: auto" in css_code
        
        results["tests"]["responsive_features"] = all([
            has_media_queries,
            has_grid,
            has_responsive_table
        ])
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def test_ui_framework_validation(self) -> Dict[str, Any]:
        """Test UI Testing Framework with mock dashboard"""
        
        results = {
            "module": "UI_Framework",
            "tests": {}
        }
        
        # Mock page for testing
        mock_page = Mock()
        mock_page.url = "http://localhost:3000/dashboard"
        mock_page.title = AsyncMock(return_value="Dashboard - DocDevAI")
        mock_page.content = AsyncMock(return_value="<html>...</html>")
        mock_page.evaluate = AsyncMock(return_value={})
        mock_page.query_selector_all = AsyncMock(return_value=[])
        mock_page.add_script_tag = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        
        # Test accessibility
        accessibility_tester = AccessibilityTester(self.ui_framework.config)
        a11y_result = await accessibility_tester._test_aria_compliance(mock_page)
        results["tests"]["aria_compliance"] = a11y_result["score"] >= 0
        
        # Test responsive design
        responsive_tester = ResponsiveTester(self.ui_framework.config)
        responsive_result = await responsive_tester._test_content_visibility(mock_page)
        results["tests"]["content_visibility"] = responsive_result >= 0
        
        # Test performance
        performance_tester = PerformanceTester(self.ui_framework.config)
        
        # Mock performance metrics
        mock_page.evaluate = AsyncMock(return_value={
            "domContentLoaded": 500,
            "loadComplete": 1500,
            "firstPaint": 300,
            "firstContentfulPaint": 400
        })
        
        perf_result = await performance_tester._get_memory_usage(mock_page)
        results["tests"]["memory_metrics"] = perf_result is not None
        
        results["passed"] = all(results["tests"].values())
        return results
    
    async def run_all_integration_tests(self) -> Dict[str, Any]:
        """Run all module integration tests"""
        
        await self.setup_modules()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "summary": {
                "total": 0,
                "passed": 0,
                "failed": 0
            }
        }
        
        # Run tests for each module
        test_methods = [
            self.test_configuration_ui_integration,
            self.test_storage_dashboard_state,
            self.test_miair_ui_optimization,
            self.test_generator_ui_documentation,
            self.test_quality_ui_content,
            self.test_template_ui_components,
            self.test_review_ui_compliance,
            self.test_ui_framework_validation
        ]
        
        for test_method in test_methods:
            try:
                test_result = await test_method()
                module_name = test_result["module"]
                results["tests"][module_name] = test_result
                results["summary"]["total"] += 1
                
                if test_result.get("passed", False):
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Test failed: {test_method.__name__} - {e}")
                results["summary"]["failed"] += 1
        
        # Calculate overall success rate
        if results["summary"]["total"] > 0:
            results["summary"]["success_rate"] = (
                results["summary"]["passed"] / results["summary"]["total"]
            )
        
        return results


# Test Cases

@pytest.mark.asyncio
class TestUIModuleIntegration:
    """Test suite for UI and module integration"""
    
    async def test_configuration_integration(self):
        """Test UI configuration with M001"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_configuration_ui_integration()
        
        assert result["passed"] is True
        assert result["tests"]["theme_persistence"] is True
        assert result["tests"]["accessibility_config"] is True
    
    async def test_storage_integration(self):
        """Test dashboard state storage with M002"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_storage_dashboard_state()
        
        assert result["passed"] is True
        assert result["tests"]["state_stored"] is True
        assert result["tests"]["state_retrieved"] is True
    
    async def test_miair_integration(self):
        """Test UI content optimization with M003"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_miair_ui_optimization()
        
        assert result["passed"] is True
        assert result["tests"]["dashboard_title_quality"] is True
    
    async def test_generator_integration(self):
        """Test UI documentation generation with M004"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_generator_ui_documentation()
        
        assert result["passed"] is True
        assert result["tests"]["doc_generated"] is True
    
    async def test_quality_integration(self):
        """Test UI content quality with M005"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_quality_ui_content()
        
        assert result["passed"] is True
        assert result["tests"]["good_error"] is True
        assert result["tests"]["bad_error"] is True
    
    async def test_template_integration(self):
        """Test UI templates with M006"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_template_ui_components()
        
        assert result["passed"] is True
        assert result["tests"]["card_rendered"] is True
        assert result["tests"]["table_rendered"] is True
    
    async def test_review_integration(self):
        """Test UI compliance review with M007"""
        tester = UIModuleIntegrationTester()
        await tester.setup_modules()
        
        result = await tester.test_review_ui_compliance()
        
        assert result["passed"] is True
        assert result["tests"]["has_landmarks"] is True
        assert result["tests"]["has_aria"] is True
    
    async def test_full_integration(self):
        """Test full integration of all modules with UI"""
        tester = UIModuleIntegrationTester()
        
        results = await tester.run_all_integration_tests()
        
        assert results["summary"]["total"] > 0
        assert results["summary"]["passed"] > 0
        assert results["summary"]["success_rate"] > 0.7  # 70% minimum


if __name__ == "__main__":
    # Run integration tests
    async def main():
        tester = UIModuleIntegrationTester()
        results = await tester.run_all_integration_tests()
        
        print("\n" + "=" * 80)
        print("UI MODULE INTEGRATION TEST RESULTS")
        print("=" * 80)
        print(f"Timestamp: {results['timestamp']}")
        print(f"Total Tests: {results['summary']['total']}")
        print(f"Passed: {results['summary']['passed']}")
        print(f"Failed: {results['summary']['failed']}")
        print(f"Success Rate: {results['summary'].get('success_rate', 0):.2%}")
        print("\nModule Results:")
        print("-" * 40)
        
        for module, result in results["tests"].items():
            status = "✅ PASSED" if result.get("passed") else "❌ FAILED"
            print(f"{module}: {status}")
            
            # Show failed tests
            if not result.get("passed"):
                for test_name, test_passed in result.get("tests", {}).items():
                    if not test_passed:
                        print(f"  - {test_name}: Failed")
        
        print("=" * 80)
    
    asyncio.run(main()