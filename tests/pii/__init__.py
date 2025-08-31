"""
Enhanced PII Testing Framework for DocDevAI v3.0.0

Comprehensive testing framework extending M002 Local Storage System's PII detection
with enterprise-grade validation, compliance testing, and performance benchmarking.

Key Components:
- Enhanced PII Detector with GDPR/CCPA compliance (27 EU countries + California)
- Comprehensive accuracy testing framework (≥95% F1-score target)
- Performance benchmarking suite (≥1000 words/second target)
- Multi-language support testing (15+ languages)
- Adversarial testing against obfuscated PII and evasion techniques
- M001 Configuration Manager integration for centralized settings

Framework Structure:
├── accuracy/           - F1-score measurement, false positive/negative rate testing
├── performance/        - Speed validation, memory efficiency, scalability testing
├── multilang/          - Multi-language datasets, character set validation
├── adversarial/        - Obfuscation, social engineering, encoding evasion tests
├── integration/        - M001 configuration integration, environment profiles
├── gdpr/              - GDPR compliance testing (27 EU countries)
├── ccpa/              - CCPA compliance testing (California Civil Code)
└── utils/             - Shared utilities and helper functions

Quality Targets:
- Overall Accuracy: ≥95% F1-score (precision and recall)
- False Positive Rate: <5%
- False Negative Rate: <5%
- Processing Speed: ≥1000 words/second
- Multi-language Support: 15+ languages with validation
- Compliance Coverage: 100% GDPR + CCPA requirements
- Adversarial Robustness: ≥80% resistance to evasion attempts
"""

from devdocai.storage.enhanced_pii_detector import (
    EnhancedPIIDetector,
    EnhancedPIIDetectionConfig,
    AccuracyMetrics,
    GDPRCountry,
    CCPACategory,
    EnhancedPIIType
)

from tests.pii.accuracy.test_accuracy_framework import (
    AccuracyTestFramework,
    GroundTruthGenerator,
    TestResults
)

from tests.pii.performance.benchmark_pii_performance import (
    PerformanceBenchmark,
    PerformanceMetrics,
    BenchmarkResult
)

from tests.pii.multilang.test_multilang_datasets import (
    MultiLanguageDatasetGenerator,
    MultiLanguageAccuracyTester,
    LanguageProfile
)

from tests.pii.adversarial.test_adversarial_pii import (
    AdversarialTester,
    AdversarialTestCase,
    ObfuscationTechniques,
    SocialEngineeringPatterns
)

from tests.pii.integration.test_m001_integration import (
    IntegratedPIITestingFramework,
    PIIConfigurationManager,
    PIISensitivityProfile
)

__version__ = "1.0.0"
__author__ = "DocDevAI Development Team"
__description__ = "Enhanced PII Testing Framework with GDPR/CCPA compliance"

# Framework capabilities
SUPPORTED_LANGUAGES = [
    'de', 'fr', 'it', 'es', 'nl', 'pl', 'pt', 'se', 'no', 'dk', 
    'fi', 'cz', 'hu', 'el', 'ru', 'en'
]

SUPPORTED_GDPR_COUNTRIES = [country.value for country in GDPRCountry]

SUPPORTED_CCPA_CATEGORIES = [category.value for category in CCPACategory]

# Quality targets
QUALITY_TARGETS = {
    'f1_score_minimum': 0.95,
    'false_positive_rate_maximum': 0.05,
    'false_negative_rate_maximum': 0.05,
    'performance_minimum_wps': 1000,
    'adversarial_robustness_minimum': 0.80,
    'multilang_support_minimum': 15
}

def create_enhanced_detector(environment: str = 'balanced') -> EnhancedPIIDetector:
    """
    Create an enhanced PII detector configured for the specified environment.
    
    Args:
        environment: Environment profile ('development', 'production', 'enterprise', etc.)
    
    Returns:
        Configured EnhancedPIIDetector instance
    """
    # Import here to avoid circular imports
    from devdocai.core.config import ConfigurationManager
    from tests.pii.integration.test_m001_integration import PIIConfigurationManager
    
    config_manager = ConfigurationManager()
    pii_config_manager = PIIConfigurationManager(config_manager)
    
    pii_config = pii_config_manager.get_pii_config_for_environment(environment)
    
    return EnhancedPIIDetector(pii_config)

def run_comprehensive_pii_validation(environment: str = 'balanced') -> dict:
    """
    Run comprehensive PII validation suite for specified environment.
    
    Args:
        environment: Environment profile to test
    
    Returns:
        Dictionary containing complete validation results
    """
    from devdocai.core.config import ConfigurationManager
    from tests.pii.integration.test_m001_integration import IntegratedPIITestingFramework
    
    config_manager = ConfigurationManager()
    framework = IntegratedPIITestingFramework(config_manager)
    
    return framework.run_comprehensive_testing_suite(environment)

__all__ = [
    'EnhancedPIIDetector',
    'EnhancedPIIDetectionConfig',
    'AccuracyMetrics',
    'AccuracyTestFramework',
    'PerformanceBenchmark',
    'MultiLanguageDatasetGenerator',
    'MultiLanguageAccuracyTester',
    'AdversarialTester',
    'IntegratedPIITestingFramework',
    'PIIConfigurationManager',
    'PIISensitivityProfile',
    'create_enhanced_detector',
    'run_comprehensive_pii_validation',
    'SUPPORTED_LANGUAGES',
    'SUPPORTED_GDPR_COUNTRIES',
    'SUPPORTED_CCPA_CATEGORIES',
    'QUALITY_TARGETS'
]