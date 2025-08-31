"""
Adversarial Testing Framework for Enhanced PII Detection.

Provides comprehensive adversarial testing against obfuscated PII,
social engineering attempts, evasion techniques, and sophisticated
attack patterns designed to bypass PII detection systems.
"""

import unittest
import logging
import random
import string
import base64
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import re
import hashlib

# Import our enhanced detector
import sys
sys.path.append('/workspaces/DocDevAI-v3.0.0')
from devdocai.storage.enhanced_pii_detector import (
    EnhancedPIIDetector, EnhancedPIIDetectionConfig, PIIMatch
)

logger = logging.getLogger(__name__)


@dataclass
class AdversarialTestCase:
    """Adversarial test case with evasion techniques."""
    text: str
    original_pii: str
    obfuscation_method: str
    expected_detection: bool  # Should this still be detected?
    difficulty_level: str    # easy, medium, hard, extreme
    attack_category: str     # obfuscation, social_engineering, encoding, etc.
    description: str


@dataclass
class AdversarialTestResult:
    """Result of adversarial testing."""
    test_case: AdversarialTestCase
    detected: bool
    detection_count: int
    false_negative: bool  # Should detect but didn't
    false_positive: bool  # Shouldn't detect but did
    evasion_successful: bool


class ObfuscationTechniques:
    """Collection of PII obfuscation and evasion techniques."""
    
    @staticmethod
    def leetspeak_obfuscation(text: str) -> str:
        """Apply leetspeak obfuscation."""
        replacements = {
            'a': '4', 'A': '4',
            'e': '3', 'E': '3', 
            'i': '1', 'I': '1',
            'o': '0', 'O': '0',
            's': '5', 'S': '5',
            't': '7', 'T': '7',
            'g': '9', 'G': '9'
        }
        
        result = text
        for char, replacement in replacements.items():
            if random.random() < 0.7:  # 70% chance to replace
                result = result.replace(char, replacement)
        
        return result
    
    @staticmethod
    def character_insertion(text: str) -> str:
        """Insert random characters to break patterns."""
        result = ""
        for i, char in enumerate(text):
            result += char
            if i > 0 and i < len(text) - 1 and random.random() < 0.2:
                # Insert random character or space
                if random.random() < 0.5:
                    result += random.choice(['-', '_', '.', ' '])
                else:
                    result += random.choice(string.ascii_lowercase)
        
        return result
    
    @staticmethod
    def character_substitution(text: str) -> str:
        """Substitute characters with similar looking ones."""
        substitutions = {
            'a': ['@', 'α'], 'A': ['@', 'Α'],
            'e': ['€', 'ε'], 'E': ['Ε'],
            'i': ['!', '|', 'ι'], 'I': ['!', '|', 'Ι'],
            'o': ['0', 'ο'], 'O': ['0', 'Ο'],
            's': ['$', 'σ'], 'S': ['$', 'Σ'],
            'u': ['υ'], 'U': ['Υ'],
            'n': ['η'], 'N': ['Ν']
        }
        
        result = text
        for char, replacements in substitutions.items():
            if char in result and random.random() < 0.3:
                result = result.replace(char, random.choice(replacements), 1)
        
        return result
    
    @staticmethod
    def word_splitting(text: str) -> str:
        """Split words with various separators."""
        separators = [' ', '-', '_', '.', '|', '/']
        
        result = ""
        for i, char in enumerate(text):
            result += char
            if i > 0 and i < len(text) - 1 and char.isalnum() and random.random() < 0.1:
                result += random.choice(separators)
        
        return result
    
    @staticmethod
    def reverse_obfuscation(text: str) -> str:
        """Reverse parts of the text."""
        if len(text) < 4:
            return text
            
        # Reverse middle portion
        start = len(text) // 4
        end = 3 * len(text) // 4
        
        return text[:start] + text[start:end][::-1] + text[end:]
    
    @staticmethod
    def base64_encoding(text: str) -> str:
        """Encode text in base64."""
        encoded = base64.b64encode(text.encode()).decode()
        return f"base64:{encoded}"
    
    @staticmethod
    def unicode_escaping(text: str) -> str:
        """Use unicode escape sequences."""
        result = ""
        for char in text:
            if random.random() < 0.3 and ord(char) > 127:
                result += f"\\u{ord(char):04x}"
            else:
                result += char
        return result
    
    @staticmethod
    def homograph_attack(text: str) -> str:
        """Use homograph characters (visually similar)."""
        homographs = {
            'a': 'а',  # Cyrillic а
            'e': 'е',  # Cyrillic е
            'o': 'о',  # Cyrillic о
            'p': 'р',  # Cyrillic р
            'c': 'с',  # Cyrillic с
            'x': 'х',  # Cyrillic х
        }
        
        result = text
        for latin, cyrillic in homographs.items():
            if latin in result and random.random() < 0.4:
                result = result.replace(latin, cyrillic, 1)
        
        return result


class SocialEngineeringPatterns:
    """Social engineering and context manipulation patterns."""
    
    @staticmethod
    def fake_disclaimer(pii: str) -> str:
        """Wrap PII in fake disclaimer."""
        disclaimers = [
            "This is not real personal information: {pii}",
            "Example only (not real): {pii}",
            "Fake data for testing: {pii}",
            "Sample information: {pii}",
            "Not actual PII: {pii}",
            "Placeholder data: {pii}",
        ]
        
        return random.choice(disclaimers).format(pii=pii)
    
    @staticmethod
    def context_poisoning(pii: str) -> str:
        """Add misleading context."""
        contexts = [
            "The API key is definitely not {pii}",
            "Don't use {pii} as your password",
            "Never share information like {pii}",
            "Avoid using {pii} in production",
            "This example shows bad practice: {pii}",
            "Security tip: Never expose {pii}",
        ]
        
        return random.choice(contexts).format(pii=pii)
    
    @staticmethod
    def authority_impersonation(pii: str) -> str:
        """Impersonate authority to make PII seem legitimate."""
        authorities = [
            "According to government records: {pii}",
            "Official documentation shows: {pii}",
            "Legal requirement states: {pii}",
            "Corporate policy mandates: {pii}",
            "System administrator note: {pii}",
            "Security team approved: {pii}",
        ]
        
        return random.choice(authorities).format(pii=pii)
    
    @staticmethod
    def urgency_manipulation(pii: str) -> str:
        """Create false urgency to bypass scrutiny."""
        urgent = [
            "URGENT: Please verify {pii} immediately",
            "TIME SENSITIVE: Confirm {pii} within 24 hours",
            "CRITICAL: Update {pii} before system lockout",
            "IMMEDIATE ACTION: Validate {pii} or lose access",
            "EMERGENCY: Verify {pii} to prevent account closure",
        ]
        
        return random.choice(urgent).format(pii=pii)
    
    @staticmethod
    def technical_jargon(pii: str) -> str:
        """Bury PII in technical jargon."""
        technical = [
            "Initialize authentication vector with {pii}",
            "Set cryptographic seed to {pii}",
            "Configure identity hash as {pii}",
            "Primary key constraint: {pii}",
            "Session token derives from {pii}",
            "Checksum validation against {pii}",
        ]
        
        return random.choice(technical).format(pii=pii)


class AdversarialTestGenerator:
    """Generate comprehensive adversarial test cases."""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed."""
        random.seed(seed)
        self.obfuscator = ObfuscationTechniques()
        self.social_engineer = SocialEngineeringPatterns()
    
    def generate_obfuscation_tests(self, count: int = 200) -> List[AdversarialTestCase]:
        """Generate obfuscation-based test cases."""
        test_cases = []
        
        # Base PII samples
        pii_samples = {
            'email': ['john.doe@example.com', 'admin@company.org', 'user123@gmail.com'],
            'ssn': ['123-45-6789', '987-65-4321', '555-12-3456'],
            'phone': ['+1-555-123-4567', '(555) 987-6543', '555.111.2222'],
            'credit_card': ['4532-1234-5678-9012', '5555-4444-3333-2222', '4111-1111-1111-1111'],
            'api_key': ['sk_live_123456789abcdef', 'ak_test_987654321fedcba', 'key_prod_abcdef123456']
        }
        
        obfuscation_methods = [
            ('leetspeak', self.obfuscator.leetspeak_obfuscation, True, 'medium'),
            ('character_insertion', self.obfuscator.character_insertion, False, 'hard'),
            ('character_substitution', self.obfuscator.character_substitution, True, 'hard'),
            ('word_splitting', self.obfuscator.word_splitting, False, 'hard'),
            ('reverse_obfuscation', self.obfuscator.reverse_obfuscation, False, 'extreme'),
            ('base64_encoding', self.obfuscator.base64_encoding, False, 'extreme'),
            ('unicode_escaping', self.obfuscator.unicode_escaping, True, 'medium'),
            ('homograph_attack', self.obfuscator.homograph_attack, True, 'extreme')
        ]
        
        for i in range(count):
            # Select PII type and sample
            pii_type = random.choice(list(pii_samples.keys()))
            original_pii = random.choice(pii_samples[pii_type])
            
            # Select obfuscation method
            method_name, method_func, should_detect, difficulty = random.choice(obfuscation_methods)
            
            # Apply obfuscation
            try:
                obfuscated = method_func(original_pii)
                text = f"Contact information: {obfuscated}"
                
                test_cases.append(AdversarialTestCase(
                    text=text,
                    original_pii=original_pii,
                    obfuscation_method=method_name,
                    expected_detection=should_detect,
                    difficulty_level=difficulty,
                    attack_category='obfuscation',
                    description=f"{method_name} obfuscation of {pii_type}"
                ))
                
            except Exception as e:
                logger.warning(f"Failed to apply {method_name} to {original_pii}: {e}")
        
        return test_cases
    
    def generate_social_engineering_tests(self, count: int = 100) -> List[AdversarialTestCase]:
        """Generate social engineering test cases."""
        test_cases = []
        
        pii_samples = {
            'ssn': ['123-45-6789', '987-65-4321'],
            'api_key': ['sk_live_abcdef123456', 'key_prod_987654'],
            'email': ['admin@company.com', 'support@example.org'],
            'phone': ['+1-555-123-4567', '(555) 987-6543']
        }
        
        se_methods = [
            ('fake_disclaimer', self.social_engineer.fake_disclaimer, False, 'medium'),
            ('context_poisoning', self.social_engineer.context_poisoning, True, 'hard'),
            ('authority_impersonation', self.social_engineer.authority_impersonation, True, 'hard'),
            ('urgency_manipulation', self.social_engineer.urgency_manipulation, True, 'medium'),
            ('technical_jargon', self.social_engineer.technical_jargon, True, 'hard')
        ]
        
        for i in range(count):
            pii_type = random.choice(list(pii_samples.keys()))
            original_pii = random.choice(pii_samples[pii_type])
            
            method_name, method_func, should_detect, difficulty = random.choice(se_methods)
            
            try:
                text = method_func(original_pii)
                
                test_cases.append(AdversarialTestCase(
                    text=text,
                    original_pii=original_pii,
                    obfuscation_method=method_name,
                    expected_detection=should_detect,
                    difficulty_level=difficulty,
                    attack_category='social_engineering',
                    description=f"{method_name} social engineering with {pii_type}"
                ))
                
            except Exception as e:
                logger.warning(f"Failed to apply {method_name} to {original_pii}: {e}")
        
        return test_cases
    
    def generate_encoding_tests(self, count: int = 50) -> List[AdversarialTestCase]:
        """Generate encoding-based evasion tests."""
        test_cases = []
        
        pii_samples = ['john@example.com', '123-45-6789', '+1-555-123-4567']
        
        for i in range(count):
            original_pii = random.choice(pii_samples)
            
            # Various encoding methods
            if i % 4 == 0:
                # URL encoding
                encoded = ''.join(f'%{ord(c):02x}' if c in '@.-' else c for c in original_pii)
                text = f"URL parameter: user={encoded}"
                should_detect = False
                method = 'url_encoding'
                
            elif i % 4 == 1:
                # HTML entities
                encoded = original_pii.replace('@', '&#64;').replace('.', '&#46;')
                text = f"HTML content: {encoded}"
                should_detect = False
                method = 'html_encoding'
                
            elif i % 4 == 2:
                # Hex encoding
                hex_encoded = ''.join(f'\\x{ord(c):02x}' for c in original_pii)
                text = f"Hex data: {hex_encoded}"
                should_detect = False
                method = 'hex_encoding'
                
            else:
                # Binary representation
                binary = ' '.join(f'{ord(c):08b}' for c in original_pii)
                text = f"Binary: {binary}"
                should_detect = False
                method = 'binary_encoding'
            
            test_cases.append(AdversarialTestCase(
                text=text,
                original_pii=original_pii,
                obfuscation_method=method,
                expected_detection=should_detect,
                difficulty_level='extreme',
                attack_category='encoding',
                description=f"{method} of {original_pii}"
            ))
        
        return test_cases
    
    def generate_context_manipulation_tests(self, count: int = 75) -> List[AdversarialTestCase]:
        """Generate context manipulation tests."""
        test_cases = []
        
        for i in range(count):
            # Create PII embedded in misleading contexts
            if i % 3 == 0:
                # Hidden in long text
                pii = "admin@secretcorp.com"
                filler = " ".join([f"word{j}" for j in range(50)])
                text = f"Long document: {filler[:100]} {pii} {filler[100:200]}"
                should_detect = True
                method = 'text_flooding'
                
            elif i % 3 == 1:
                # Multiple similar patterns
                real_pii = "123-45-6789"
                fake_patterns = ["000-00-0000", "111-11-1111", "999-99-9999"]
                all_patterns = fake_patterns + [real_pii]
                random.shuffle(all_patterns)
                text = "SSN candidates: " + ", ".join(all_patterns)
                should_detect = True
                method = 'pattern_noise'
                
            else:
                # Nested in technical context
                pii = "sk_live_abcdef123456"
                text = f"// TODO: Replace {pii} with production key"
                should_detect = True
                method = 'code_context'
            
            test_cases.append(AdversarialTestCase(
                text=text,
                original_pii=pii if 'pii' in locals() else real_pii,
                obfuscation_method=method,
                expected_detection=should_detect,
                difficulty_level='hard',
                attack_category='context_manipulation',
                description=f"{method} context manipulation"
            ))
        
        return test_cases
    
    def generate_comprehensive_adversarial_suite(self) -> List[AdversarialTestCase]:
        """Generate comprehensive adversarial test suite."""
        logger.info("Generating comprehensive adversarial test suite...")
        
        all_tests = []
        
        # Different attack categories
        all_tests.extend(self.generate_obfuscation_tests(200))
        all_tests.extend(self.generate_social_engineering_tests(100))
        all_tests.extend(self.generate_encoding_tests(50))
        all_tests.extend(self.generate_context_manipulation_tests(75))
        
        logger.info(f"Generated {len(all_tests)} adversarial test cases")
        
        # Shuffle to randomize test order
        random.shuffle(all_tests)
        
        return all_tests


class AdversarialTester:
    """Execute adversarial tests against PII detector."""
    
    def __init__(self, detector: EnhancedPIIDetector):
        """Initialize with enhanced detector."""
        self.detector = detector
        self.generator = AdversarialTestGenerator()
        
    def run_adversarial_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive adversarial test suite."""
        logger.info("Running adversarial test suite...")
        
        # Generate test cases
        test_cases = self.generator.generate_comprehensive_adversarial_suite()
        
        results = {
            'total_tests': len(test_cases),
            'by_category': {},
            'by_difficulty': {},
            'evasion_success_rate': {},
            'detailed_results': []
        }
        
        category_stats = {}
        difficulty_stats = {}
        evasion_stats = {}
        
        for test_case in test_cases:
            # Run detection
            detected_matches = self.detector.enhanced_detect(test_case.text)
            
            # Analyze results
            detected = len(detected_matches) > 0
            false_negative = test_case.expected_detection and not detected
            false_positive = not test_case.expected_detection and detected
            evasion_successful = not test_case.expected_detection and not detected
            
            test_result = AdversarialTestResult(
                test_case=test_case,
                detected=detected,
                detection_count=len(detected_matches),
                false_negative=false_negative,
                false_positive=false_positive,
                evasion_successful=evasion_successful
            )
            
            # Update statistics
            category = test_case.attack_category
            if category not in category_stats:
                category_stats[category] = {'total': 0, 'evasions': 0, 'false_negatives': 0, 'false_positives': 0}
            
            category_stats[category]['total'] += 1
            if evasion_successful:
                category_stats[category]['evasions'] += 1
            if false_negative:
                category_stats[category]['false_negatives'] += 1
            if false_positive:
                category_stats[category]['false_positives'] += 1
            
            # Difficulty statistics
            difficulty = test_case.difficulty_level
            if difficulty not in difficulty_stats:
                difficulty_stats[difficulty] = {'total': 0, 'evasions': 0}
            
            difficulty_stats[difficulty]['total'] += 1
            if evasion_successful:
                difficulty_stats[difficulty]['evasions'] += 1
            
            # Evasion method statistics
            method = test_case.obfuscation_method
            if method not in evasion_stats:
                evasion_stats[method] = {'total': 0, 'evasions': 0}
            
            evasion_stats[method]['total'] += 1
            if evasion_successful:
                evasion_stats[method]['evasions'] += 1
            
            # Store detailed result
            results['detailed_results'].append({
                'text': test_case.text[:100] + '...' if len(test_case.text) > 100 else test_case.text,
                'original_pii': test_case.original_pii,
                'method': test_case.obfuscation_method,
                'category': test_case.attack_category,
                'difficulty': test_case.difficulty_level,
                'expected_detection': test_case.expected_detection,
                'actually_detected': detected,
                'detection_count': len(detected_matches),
                'false_negative': false_negative,
                'false_positive': false_positive,
                'evasion_successful': evasion_successful
            })
        
        # Calculate summary statistics
        for category, stats in category_stats.items():
            evasion_rate = stats['evasions'] / stats['total'] if stats['total'] > 0 else 0
            results['by_category'][category] = {
                'total_tests': stats['total'],
                'evasions': stats['evasions'],
                'false_negatives': stats['false_negatives'],
                'false_positives': stats['false_positives'],
                'evasion_rate': evasion_rate
            }
        
        for difficulty, stats in difficulty_stats.items():
            evasion_rate = stats['evasions'] / stats['total'] if stats['total'] > 0 else 0
            results['by_difficulty'][difficulty] = {
                'total_tests': stats['total'],
                'evasions': stats['evasions'],
                'evasion_rate': evasion_rate
            }
        
        for method, stats in evasion_stats.items():
            evasion_rate = stats['evasions'] / stats['total'] if stats['total'] > 0 else 0
            results['evasion_success_rate'][method] = {
                'total_tests': stats['total'],
                'evasions': stats['evasions'],
                'success_rate': evasion_rate
            }
        
        # Overall statistics
        total_evasions = sum(stats['evasions'] for stats in category_stats.values())
        overall_evasion_rate = total_evasions / len(test_cases) if test_cases else 0
        
        results['summary'] = {
            'total_tests': len(test_cases),
            'total_evasions': total_evasions,
            'overall_evasion_rate': overall_evasion_rate,
            'robustness_score': 1 - overall_evasion_rate,  # Higher is better
            'categories_tested': len(category_stats),
            'most_effective_attack': max(results['evasion_success_rate'].items(), 
                                       key=lambda x: x[1]['success_rate'])[0] if results['evasion_success_rate'] else 'None'
        }
        
        return results
    
    def analyze_evasion_patterns(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns in successful evasions."""
        logger.info("Analyzing evasion patterns...")
        
        successful_evasions = [
            r for r in results['detailed_results'] 
            if r['evasion_successful']
        ]
        
        # Group by various attributes
        by_method = {}
        by_category = {}
        by_difficulty = {}
        
        for evasion in successful_evasions:
            # By method
            method = evasion['method']
            if method not in by_method:
                by_method[method] = []
            by_method[method].append(evasion)
            
            # By category
            category = evasion['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(evasion)
            
            # By difficulty
            difficulty = evasion['difficulty']
            if difficulty not in by_difficulty:
                by_difficulty[difficulty] = []
            by_difficulty[difficulty].append(evasion)
        
        analysis = {
            'total_successful_evasions': len(successful_evasions),
            'most_successful_methods': sorted(
                [(method, len(evasions)) for method, evasions in by_method.items()],
                key=lambda x: x[1], reverse=True
            )[:5],
            'most_vulnerable_categories': sorted(
                [(category, len(evasions)) for category, evasions in by_category.items()],
                key=lambda x: x[1], reverse=True
            ),
            'evasions_by_difficulty': {
                difficulty: len(evasions) 
                for difficulty, evasions in by_difficulty.items()
            },
            'recommendations': self._generate_hardening_recommendations(by_method, by_category)
        }
        
        return analysis
    
    def _generate_hardening_recommendations(self, by_method: Dict, by_category: Dict) -> List[str]:
        """Generate recommendations for hardening against evasions."""
        recommendations = []
        
        # Method-specific recommendations
        if 'leetspeak' in by_method:
            recommendations.append("Implement character normalization to handle leetspeak obfuscation")
        
        if 'homograph_attack' in by_method:
            recommendations.append("Add Unicode homograph detection and normalization")
        
        if 'base64_encoding' in by_method:
            recommendations.append("Include base64 decoding in preprocessing pipeline")
        
        if 'character_insertion' in by_method:
            recommendations.append("Implement fuzzy matching for character-inserted patterns")
        
        # Category-specific recommendations
        if 'encoding' in by_category:
            recommendations.append("Expand encoding detection to include URL, HTML, hex, and binary")
        
        if 'social_engineering' in by_category:
            recommendations.append("Enhance context analysis to detect social engineering patterns")
        
        if 'obfuscation' in by_category:
            recommendations.append("Implement multi-pass detection with deobfuscation preprocessing")
        
        # General recommendations
        recommendations.extend([
            "Consider machine learning approaches for pattern-agnostic detection",
            "Implement confidence adjustment based on context analysis",
            "Add preprocessing stage for common obfuscation techniques",
            "Create feedback loop for adversarial training"
        ])
        
        return recommendations


class TestAdversarialPII(unittest.TestCase):
    """Unit tests for adversarial PII detection."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = EnhancedPIIDetectionConfig(
            gdpr_enabled=True,
            ccpa_enabled=True,
            multilang_enabled=True,
            context_analysis=True,
            min_confidence=0.70
        )
        self.detector = EnhancedPIIDetector(config)
        self.generator = AdversarialTestGenerator()
        self.tester = AdversarialTester(self.detector)
    
    def test_obfuscation_generation(self):
        """Test obfuscation test case generation."""
        test_cases = self.generator.generate_obfuscation_tests(50)
        self.assertEqual(len(test_cases), 50)
        
        # Verify structure
        for case in test_cases[:5]:
            self.assertIsInstance(case, AdversarialTestCase)
            self.assertIn('obfuscation', case.attack_category)
            self.assertIsInstance(case.expected_detection, bool)
    
    def test_social_engineering_generation(self):
        """Test social engineering test case generation."""
        test_cases = self.generator.generate_social_engineering_tests(25)
        self.assertEqual(len(test_cases), 25)
        
        for case in test_cases:
            self.assertEqual(case.attack_category, 'social_engineering')
    
    def test_encoding_evasion(self):
        """Test encoding-based evasion techniques."""
        test_cases = self.generator.generate_encoding_tests(20)
        self.assertEqual(len(test_cases), 20)
        
        # Most encoding tests should not be detectable
        expected_non_detectable = sum(1 for case in test_cases if not case.expected_detection)
        self.assertGreater(expected_non_detectable, len(test_cases) * 0.8,
                          "Most encoding tests should be evasive")
    
    def test_adversarial_suite_execution(self):
        """Test execution of adversarial test suite."""
        # Run smaller suite for unit testing
        original_method = self.generator.generate_comprehensive_adversarial_suite
        
        def small_suite():
            tests = []
            tests.extend(self.generator.generate_obfuscation_tests(20))
            tests.extend(self.generator.generate_social_engineering_tests(10))
            return tests
        
        self.generator.generate_comprehensive_adversarial_suite = small_suite
        
        results = self.tester.run_adversarial_test_suite()
        
        # Verify results structure
        self.assertIn('summary', results)
        self.assertIn('by_category', results)
        self.assertIn('evasion_success_rate', results)
        self.assertEqual(results['total_tests'], 30)
        
        # Should have some statistics
        self.assertGreater(len(results['by_category']), 0)
    
    def test_evasion_pattern_analysis(self):
        """Test evasion pattern analysis."""
        # Create mock results
        mock_results = {
            'detailed_results': [
                {
                    'method': 'leetspeak',
                    'category': 'obfuscation',
                    'difficulty': 'medium',
                    'evasion_successful': True
                },
                {
                    'method': 'base64_encoding',
                    'category': 'encoding',
                    'difficulty': 'extreme',
                    'evasion_successful': True
                },
                {
                    'method': 'fake_disclaimer',
                    'category': 'social_engineering',
                    'difficulty': 'medium',
                    'evasion_successful': False
                }
            ]
        }
        
        analysis = self.tester.analyze_evasion_patterns(mock_results)
        
        self.assertIn('total_successful_evasions', analysis)
        self.assertIn('most_successful_methods', analysis)
        self.assertIn('recommendations', analysis)
        self.assertEqual(analysis['total_successful_evasions'], 2)
    
    def test_obfuscation_techniques(self):
        """Test individual obfuscation techniques."""
        obfuscator = ObfuscationTechniques()
        
        original = "john@example.com"
        
        # Test leetspeak
        leetspeak = obfuscator.leetspeak_obfuscation(original)
        self.assertNotEqual(original, leetspeak)
        
        # Test character substitution
        substituted = obfuscator.character_substitution(original)
        # May or may not change (random), so just check it returns a string
        self.assertIsInstance(substituted, str)
        
        # Test base64
        encoded = obfuscator.base64_encoding(original)
        self.assertIn('base64:', encoded)


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create enhanced detector
    config = EnhancedPIIDetectionConfig(
        gdpr_enabled=True,
        ccpa_enabled=True,
        multilang_enabled=True,
        context_analysis=True,
        min_confidence=0.70
    )
    
    detector = EnhancedPIIDetector(config)
    tester = AdversarialTester(detector)
    
    print("🛡️ Enhanced PII Detection Adversarial Testing Framework")
    print("=" * 68)
    print("Testing against obfuscation, social engineering, and evasion techniques")
    print()
    
    # Run comprehensive adversarial test suite
    print("🔥 Running Adversarial Test Suite...")
    results = tester.run_adversarial_test_suite()
    
    # Display summary results
    print("\n📊 ADVERSARIAL TEST RESULTS")
    print("=" * 35)
    print(f"Total Tests: {results['summary']['total_tests']}")
    print(f"Total Evasions: {results['summary']['total_evasions']}")
    print(f"Overall Evasion Rate: {results['summary']['overall_evasion_rate']:.3f}")
    print(f"Robustness Score: {results['summary']['robustness_score']:.3f} (Higher is better)")
    print(f"Most Effective Attack: {results['summary']['most_effective_attack']}")
    
    # Results by category
    print("\n🎯 RESULTS BY ATTACK CATEGORY")
    print("=" * 40)
    for category, stats in results['by_category'].items():
        print(f"{category.upper()}: {stats['evasions']}/{stats['total_tests']} evasions ({stats['evasion_rate']:.3f})")
    
    # Results by difficulty
    print("\n⚡ RESULTS BY DIFFICULTY LEVEL")
    print("=" * 35)
    for difficulty, stats in results['by_difficulty'].items():
        print(f"{difficulty.upper()}: {stats['evasions']}/{stats['total_tests']} evasions ({stats['evasion_rate']:.3f})")
    
    # Top evasion methods
    print("\n🔴 MOST SUCCESSFUL EVASION METHODS")
    print("=" * 40)
    top_methods = sorted(results['evasion_success_rate'].items(), 
                        key=lambda x: x[1]['success_rate'], reverse=True)[:5]
    
    for method, stats in top_methods:
        print(f"{method}: {stats['success_rate']:.3f} success rate ({stats['evasions']}/{stats['total_tests']})")
    
    # Analyze evasion patterns
    print("\n🔍 EVASION PATTERN ANALYSIS")
    print("=" * 30)
    analysis = tester.analyze_evasion_patterns(results)
    
    print(f"Total Successful Evasions: {analysis['total_successful_evasions']}")
    print("\nMost Successful Methods:")
    for method, count in analysis['most_successful_methods']:
        print(f"  - {method}: {count} successful evasions")
    
    print(f"\nEvasions by Difficulty:")
    for difficulty, count in analysis['evasions_by_difficulty'].items():
        print(f"  - {difficulty}: {count}")
    
    # Hardening recommendations
    print("\n💡 HARDENING RECOMMENDATIONS")
    print("=" * 30)
    for i, recommendation in enumerate(analysis['recommendations'], 1):
        print(f"{i}. {recommendation}")
    
    # Security assessment
    robustness = results['summary']['robustness_score']
    if robustness >= 0.9:
        security_grade = "A+ (Excellent)"
    elif robustness >= 0.8:
        security_grade = "A (Very Good)"
    elif robustness >= 0.7:
        security_grade = "B (Good)"
    elif robustness >= 0.6:
        security_grade = "C (Fair)"
    else:
        security_grade = "D (Needs Improvement)"
    
    print(f"\n🔒 SECURITY ASSESSMENT")
    print("=" * 25)
    print(f"Robustness Grade: {security_grade}")
    print(f"Recommendation: {'Ready for production' if robustness >= 0.8 else 'Needs hardening before production'}")
    
    # Save detailed results
    results_file = Path('/workspaces/DocDevAI-v3.0.0/tests/pii/adversarial/adversarial_results.json')
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    comprehensive_results = {
        'test_results': results,
        'pattern_analysis': analysis,
        'security_assessment': {
            'robustness_score': robustness,
            'security_grade': security_grade,
            'production_ready': robustness >= 0.8
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(comprehensive_results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Run unit tests
    print("\n🔬 Running Unit Tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)