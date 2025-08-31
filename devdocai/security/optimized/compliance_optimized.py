"""
M010 Security Module - Optimized Compliance Reporter

Performance optimizations:
- Cached compliance states
- Incremental updates for changed controls only
- Parallel standard checking
- Efficient report generation with templates
- Pre-computed compliance scores
"""

import time
import json
import hashlib
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
from functools import lru_cache
from collections import defaultdict
from enum import Enum
import pickle


class ComplianceStatus(Enum):
    """Compliance status levels"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"


@dataclass
class ComplianceControl:
    """Represents a compliance control"""
    control_id: str
    standard: str
    category: str
    description: str
    status: ComplianceStatus = ComplianceStatus.PENDING
    evidence: List[str] = field(default_factory=list)
    last_checked: float = 0
    score: float = 0.0
    
    def __hash__(self):
        return hash(self.control_id)


@dataclass
class ComplianceStandard:
    """Represents a compliance standard"""
    name: str
    version: str
    controls: List[ComplianceControl]
    categories: Dict[str, List[str]]
    total_score: float = 0.0
    compliance_percentage: float = 0.0


class ComplianceCache:
    """High-performance compliance state cache"""
    
    def __init__(self, ttl: int = 3600):
        self.cache = {}
        self.ttl = ttl
        self.checksums = {}
        
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['data']
        return None
    
    def set(self, key: str, value: Any):
        """Set cache value with timestamp"""
        self.cache[key] = {
            'timestamp': time.time(),
            'data': value
        }
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""
        if pattern:
            self.cache = {k: v for k, v in self.cache.items() if pattern not in k}
        else:
            self.cache.clear()
    
    def has_changed(self, key: str, checksum: str) -> bool:
        """Check if data has changed based on checksum"""
        if key not in self.checksums:
            self.checksums[key] = checksum
            return True
        
        if self.checksums[key] != checksum:
            self.checksums[key] = checksum
            return True
        
        return False


class OptimizedComplianceReporter:
    """
    Optimized compliance reporting with caching and incremental updates.
    
    Performance improvements:
    - Cached compliance states reduce redundant checks
    - Incremental updates only for changed controls
    - Parallel standard evaluation
    - Pre-computed scores with memoization
    """
    
    def __init__(self, workers: int = None):
        self.workers = workers or mp.cpu_count()
        
        # Initialize compliance standards
        self.standards = self._load_standards()
        
        # Cache for compliance states
        self.cache = ComplianceCache(ttl=3600)
        
        # Control evaluation cache
        self.control_cache = {}
        
        # Pre-computed compliance matrices
        self.compliance_matrix = {}
        
        # Statistics
        self.stats = {
            'assessments_run': 0,
            'controls_evaluated': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'avg_assessment_time': 0
        }
    
    def _load_standards(self) -> Dict[str, ComplianceStandard]:
        """Load compliance standards with controls"""
        standards = {}
        
        # GDPR
        standards['GDPR'] = ComplianceStandard(
            name='GDPR',
            version='2016/679',
            controls=self._generate_gdpr_controls(),
            categories={
                'Data Protection': ['gdpr-1', 'gdpr-2', 'gdpr-3'],
                'User Rights': ['gdpr-4', 'gdpr-5', 'gdpr-6'],
                'Security': ['gdpr-7', 'gdpr-8', 'gdpr-9'],
                'Breach Response': ['gdpr-10', 'gdpr-11']
            }
        )
        
        # CCPA
        standards['CCPA'] = ComplianceStandard(
            name='CCPA',
            version='2018',
            controls=self._generate_ccpa_controls(),
            categories={
                'Consumer Rights': ['ccpa-1', 'ccpa-2', 'ccpa-3'],
                'Data Collection': ['ccpa-4', 'ccpa-5'],
                'Data Sale': ['ccpa-6', 'ccpa-7']
            }
        )
        
        # HIPAA
        standards['HIPAA'] = ComplianceStandard(
            name='HIPAA',
            version='1996',
            controls=self._generate_hipaa_controls(),
            categories={
                'Administrative': ['hipaa-1', 'hipaa-2', 'hipaa-3'],
                'Physical': ['hipaa-4', 'hipaa-5'],
                'Technical': ['hipaa-6', 'hipaa-7', 'hipaa-8']
            }
        )
        
        # SOC2
        standards['SOC2'] = ComplianceStandard(
            name='SOC2',
            version='Type II',
            controls=self._generate_soc2_controls(),
            categories={
                'Security': ['soc2-1', 'soc2-2'],
                'Availability': ['soc2-3', 'soc2-4'],
                'Confidentiality': ['soc2-5', 'soc2-6'],
                'Privacy': ['soc2-7', 'soc2-8']
            }
        )
        
        # ISO 27001
        standards['ISO27001'] = ComplianceStandard(
            name='ISO27001',
            version='2013',
            controls=self._generate_iso27001_controls(),
            categories={
                'Information Security': ['iso-1', 'iso-2', 'iso-3'],
                'Access Control': ['iso-4', 'iso-5'],
                'Cryptography': ['iso-6', 'iso-7'],
                'Incident Management': ['iso-8', 'iso-9']
            }
        )
        
        return standards
    
    def _generate_gdpr_controls(self) -> List[ComplianceControl]:
        """Generate GDPR compliance controls"""
        return [
            ComplianceControl('gdpr-1', 'GDPR', 'Data Protection', 'Lawful basis for processing'),
            ComplianceControl('gdpr-2', 'GDPR', 'Data Protection', 'Data minimization'),
            ComplianceControl('gdpr-3', 'GDPR', 'Data Protection', 'Purpose limitation'),
            ComplianceControl('gdpr-4', 'GDPR', 'User Rights', 'Right to access'),
            ComplianceControl('gdpr-5', 'GDPR', 'User Rights', 'Right to erasure'),
            ComplianceControl('gdpr-6', 'GDPR', 'User Rights', 'Right to portability'),
            ComplianceControl('gdpr-7', 'GDPR', 'Security', 'Encryption at rest'),
            ComplianceControl('gdpr-8', 'GDPR', 'Security', 'Encryption in transit'),
            ComplianceControl('gdpr-9', 'GDPR', 'Security', 'Access controls'),
            ComplianceControl('gdpr-10', 'GDPR', 'Breach Response', '72-hour notification'),
            ComplianceControl('gdpr-11', 'GDPR', 'Breach Response', 'Breach documentation')
        ]
    
    def _generate_ccpa_controls(self) -> List[ComplianceControl]:
        """Generate CCPA compliance controls"""
        return [
            ComplianceControl('ccpa-1', 'CCPA', 'Consumer Rights', 'Right to know'),
            ComplianceControl('ccpa-2', 'CCPA', 'Consumer Rights', 'Right to delete'),
            ComplianceControl('ccpa-3', 'CCPA', 'Consumer Rights', 'Right to opt-out'),
            ComplianceControl('ccpa-4', 'CCPA', 'Data Collection', 'Notice at collection'),
            ComplianceControl('ccpa-5', 'CCPA', 'Data Collection', 'Privacy policy'),
            ComplianceControl('ccpa-6', 'CCPA', 'Data Sale', 'Do not sell option'),
            ComplianceControl('ccpa-7', 'CCPA', 'Data Sale', 'Financial incentives disclosure')
        ]
    
    def _generate_hipaa_controls(self) -> List[ComplianceControl]:
        """Generate HIPAA compliance controls"""
        return [
            ComplianceControl('hipaa-1', 'HIPAA', 'Administrative', 'Risk assessment'),
            ComplianceControl('hipaa-2', 'HIPAA', 'Administrative', 'Workforce training'),
            ComplianceControl('hipaa-3', 'HIPAA', 'Administrative', 'Business associate agreements'),
            ComplianceControl('hipaa-4', 'HIPAA', 'Physical', 'Facility access controls'),
            ComplianceControl('hipaa-5', 'HIPAA', 'Physical', 'Workstation security'),
            ComplianceControl('hipaa-6', 'HIPAA', 'Technical', 'Access authorization'),
            ComplianceControl('hipaa-7', 'HIPAA', 'Technical', 'Audit controls'),
            ComplianceControl('hipaa-8', 'HIPAA', 'Technical', 'Transmission security')
        ]
    
    def _generate_soc2_controls(self) -> List[ComplianceControl]:
        """Generate SOC2 compliance controls"""
        return [
            ComplianceControl('soc2-1', 'SOC2', 'Security', 'Logical access controls'),
            ComplianceControl('soc2-2', 'SOC2', 'Security', 'System monitoring'),
            ComplianceControl('soc2-3', 'SOC2', 'Availability', 'Performance monitoring'),
            ComplianceControl('soc2-4', 'SOC2', 'Availability', 'Incident response'),
            ComplianceControl('soc2-5', 'SOC2', 'Confidentiality', 'Data classification'),
            ComplianceControl('soc2-6', 'SOC2', 'Confidentiality', 'Encryption controls'),
            ComplianceControl('soc2-7', 'SOC2', 'Privacy', 'Personal information protection'),
            ComplianceControl('soc2-8', 'SOC2', 'Privacy', 'Data retention and disposal')
        ]
    
    def _generate_iso27001_controls(self) -> List[ComplianceControl]:
        """Generate ISO 27001 compliance controls"""
        return [
            ComplianceControl('iso-1', 'ISO27001', 'Information Security', 'Security policy'),
            ComplianceControl('iso-2', 'ISO27001', 'Information Security', 'Risk management'),
            ComplianceControl('iso-3', 'ISO27001', 'Information Security', 'Asset management'),
            ComplianceControl('iso-4', 'ISO27001', 'Access Control', 'User access management'),
            ComplianceControl('iso-5', 'ISO27001', 'Access Control', 'Privileged access'),
            ComplianceControl('iso-6', 'ISO27001', 'Cryptography', 'Cryptographic controls'),
            ComplianceControl('iso-7', 'ISO27001', 'Cryptography', 'Key management'),
            ComplianceControl('iso-8', 'ISO27001', 'Incident Management', 'Incident response plan'),
            ComplianceControl('iso-9', 'ISO27001', 'Incident Management', 'Evidence collection')
        ]
    
    def generate_report(self, standards: List[str], 
                       incremental: bool = True) -> Dict[str, Any]:
        """
        Generate compliance report with optimizations.
        
        Target: <1000ms for full assessment.
        """
        start = time.perf_counter()
        
        # Check cache first
        cache_key = f"report:{':'.join(sorted(standards))}"
        if incremental:
            cached_report = self.cache.get(cache_key)
            if cached_report:
                self.stats['cache_hits'] += 1
                return cached_report
        
        self.stats['cache_misses'] += 1
        
        # Parallel assessment of multiple standards
        if len(standards) > 1:
            report = self._assess_parallel(standards)
        else:
            report = self._assess_sequential(standards)
        
        # Calculate overall compliance
        report['overall_compliance'] = self._calculate_overall_compliance(report)
        
        # Add metadata
        report['metadata'] = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'standards_assessed': standards,
            'incremental': incremental,
            'assessment_time_ms': (time.perf_counter() - start) * 1000
        }
        
        # Cache report
        self.cache.set(cache_key, report)
        
        # Update statistics
        self.stats['assessments_run'] += 1
        elapsed = (time.perf_counter() - start) * 1000
        self.stats['avg_assessment_time'] = (
            (self.stats['avg_assessment_time'] * (self.stats['assessments_run'] - 1) + elapsed) /
            self.stats['assessments_run']
        )
        
        return report
    
    def _assess_sequential(self, standards: List[str]) -> Dict:
        """Sequential assessment (fallback)"""
        results = {}
        for standard_name in standards:
            if standard_name in self.standards:
                results[standard_name] = self._assess_standard(
                    self.standards[standard_name]
                )
        return {'standards': results}
    
    def _assess_parallel(self, standards: List[str]) -> Dict:
        """Parallel assessment of multiple standards"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {}
            
            for standard_name in standards:
                if standard_name in self.standards:
                    future = executor.submit(
                        self._assess_standard,
                        self.standards[standard_name]
                    )
                    futures[future] = standard_name
            
            for future in as_completed(futures):
                standard_name = futures[future]
                try:
                    results[standard_name] = future.result(timeout=5)
                except Exception as e:
                    results[standard_name] = {'error': str(e)}
        
        return {'standards': results}
    
    @lru_cache(maxsize=1000)
    def _assess_standard(self, standard: ComplianceStandard) -> Dict:
        """
        Assess compliance with a standard.
        
        Uses caching and incremental updates.
        """
        # Check if we need to re-evaluate
        standard_hash = self._calculate_standard_hash(standard)
        cache_key = f"standard:{standard.name}"
        
        if not self.cache.has_changed(cache_key, standard_hash):
            # Use cached assessment
            cached = self.control_cache.get(standard.name)
            if cached:
                return cached
        
        assessment = {
            'standard': standard.name,
            'version': standard.version,
            'controls': {},
            'by_category': {},
            'compliance_score': 0,
            'compliance_percentage': 0,
            'status': ComplianceStatus.PENDING.value
        }
        
        compliant_count = 0
        total_count = len(standard.controls)
        
        # Evaluate each control
        for control in standard.controls:
            control_result = self._evaluate_control(control)
            assessment['controls'][control.control_id] = control_result
            
            if control_result['status'] == ComplianceStatus.COMPLIANT.value:
                compliant_count += 1
            
            # Group by category
            if control.category not in assessment['by_category']:
                assessment['by_category'][control.category] = {
                    'controls': [],
                    'compliance_percentage': 0
                }
            assessment['by_category'][control.category]['controls'].append(control_result)
        
        # Calculate compliance percentages
        assessment['compliance_percentage'] = (compliant_count / total_count * 100) if total_count > 0 else 0
        assessment['compliance_score'] = assessment['compliance_percentage'] / 100
        
        # Determine overall status
        if assessment['compliance_percentage'] >= 95:
            assessment['status'] = ComplianceStatus.COMPLIANT.value
        elif assessment['compliance_percentage'] >= 70:
            assessment['status'] = ComplianceStatus.PARTIAL.value
        else:
            assessment['status'] = ComplianceStatus.NON_COMPLIANT.value
        
        # Calculate category percentages
        for category in assessment['by_category']:
            category_controls = assessment['by_category'][category]['controls']
            compliant = sum(1 for c in category_controls if c['status'] == ComplianceStatus.COMPLIANT.value)
            assessment['by_category'][category]['compliance_percentage'] = (
                (compliant / len(category_controls) * 100) if category_controls else 0
            )
        
        # Cache result
        self.control_cache[standard.name] = assessment
        
        return assessment
    
    def _evaluate_control(self, control: ComplianceControl) -> Dict:
        """
        Evaluate individual control with caching.
        
        Simulates control evaluation (would check actual implementation in production).
        """
        # Check cache
        cache_key = f"control:{control.control_id}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Simulate control evaluation
        # In production, this would check actual system state
        evaluation = {
            'control_id': control.control_id,
            'category': control.category,
            'description': control.description,
            'status': ComplianceStatus.COMPLIANT.value,  # Simulated
            'score': 1.0,
            'evidence': [
                f'Automated check passed at {datetime.now(timezone.utc).isoformat()}',
                'Security controls verified',
                'Documentation available'
            ],
            'last_checked': time.time()
        }
        
        # Apply some variance for simulation
        import random
        if random.random() < 0.1:  # 10% non-compliant
            evaluation['status'] = ComplianceStatus.NON_COMPLIANT.value
            evaluation['score'] = 0.0
            evaluation['evidence'].append('Control gap identified')
        elif random.random() < 0.2:  # 20% partial
            evaluation['status'] = ComplianceStatus.PARTIAL.value
            evaluation['score'] = 0.5
            evaluation['evidence'].append('Partial implementation')
        
        # Cache result
        self.cache.set(cache_key, evaluation)
        self.stats['controls_evaluated'] += 1
        
        return evaluation
    
    def _calculate_standard_hash(self, standard: ComplianceStandard) -> str:
        """Calculate hash for standard state"""
        data = f"{standard.name}:{standard.version}:{len(standard.controls)}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _calculate_overall_compliance(self, report: Dict) -> Dict:
        """Calculate overall compliance across all standards"""
        if 'standards' not in report or not report['standards']:
            return {'score': 0, 'percentage': 0, 'status': ComplianceStatus.PENDING.value}
        
        total_score = 0
        count = 0
        
        for standard_name, assessment in report['standards'].items():
            if 'compliance_score' in assessment:
                total_score += assessment['compliance_score']
                count += 1
        
        avg_score = total_score / count if count > 0 else 0
        percentage = avg_score * 100
        
        if percentage >= 95:
            status = ComplianceStatus.COMPLIANT.value
        elif percentage >= 70:
            status = ComplianceStatus.PARTIAL.value
        else:
            status = ComplianceStatus.NON_COMPLIANT.value
        
        return {
            'score': avg_score,
            'percentage': percentage,
            'status': status,
            'standards_assessed': count
        }
    
    def generate_gap_analysis(self, standards: List[str]) -> Dict:
        """
        Generate gap analysis report.
        
        Identifies non-compliant controls and remediation steps.
        """
        report = self.generate_report(standards)
        gaps = {
            'total_gaps': 0,
            'critical_gaps': [],
            'by_standard': {},
            'remediation_plan': []
        }
        
        for standard_name, assessment in report['standards'].items():
            standard_gaps = []
            
            for control_id, control in assessment['controls'].items():
                if control['status'] != ComplianceStatus.COMPLIANT.value:
                    gap = {
                        'control_id': control_id,
                        'description': control['description'],
                        'status': control['status'],
                        'category': control['category'],
                        'remediation': self._get_remediation(control_id)
                    }
                    standard_gaps.append(gap)
                    gaps['total_gaps'] += 1
                    
                    if control['status'] == ComplianceStatus.NON_COMPLIANT.value:
                        gaps['critical_gaps'].append(gap)
            
            gaps['by_standard'][standard_name] = {
                'gaps': standard_gaps,
                'count': len(standard_gaps),
                'compliance_percentage': assessment['compliance_percentage']
            }
        
        # Generate remediation plan
        gaps['remediation_plan'] = self._generate_remediation_plan(gaps['critical_gaps'])
        
        return gaps
    
    def _get_remediation(self, control_id: str) -> str:
        """Get remediation steps for control"""
        remediation_map = {
            'gdpr-4': 'Implement data subject access request functionality',
            'gdpr-5': 'Add data deletion capabilities',
            'gdpr-7': 'Enable encryption at rest for all data stores',
            'ccpa-3': 'Add opt-out mechanism for data sale',
            'hipaa-6': 'Implement role-based access control',
            'soc2-1': 'Configure logical access controls',
            'iso-8': 'Create incident response plan'
        }
        
        return remediation_map.get(control_id, 'Review control requirements and implement necessary changes')
    
    def _generate_remediation_plan(self, critical_gaps: List[Dict]) -> List[Dict]:
        """Generate prioritized remediation plan"""
        plan = []
        
        # Group by category for efficiency
        by_category = defaultdict(list)
        for gap in critical_gaps:
            by_category[gap['category']].append(gap)
        
        # Create remediation tasks
        priority = 1
        for category, gaps in by_category.items():
            plan.append({
                'priority': priority,
                'category': category,
                'tasks': [g['remediation'] for g in gaps],
                'estimated_effort': f'{len(gaps) * 8} hours',
                'impact': 'High'
            })
            priority += 1
        
        return plan
    
    def export_report(self, report: Dict, format: str = 'json') -> str:
        """Export report in various formats"""
        if format == 'json':
            return json.dumps(report, indent=2)
        elif format == 'html':
            return self._generate_html_report(report)
        elif format == 'pdf':
            # Would use reportlab or similar in production
            return "PDF generation not implemented"
        else:
            return str(report)
    
    def _generate_html_report(self, report: Dict) -> str:
        """Generate HTML compliance report"""
        html = f"""
        <html>
        <head>
            <title>Compliance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .compliant {{ color: green; }}
                .partial {{ color: orange; }}
                .non-compliant {{ color: red; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Compliance Assessment Report</h1>
            <p>Generated: {report['metadata']['generated_at']}</p>
            <h2>Overall Compliance: {report['overall_compliance']['percentage']:.1f}%</h2>
            <table>
                <tr>
                    <th>Standard</th>
                    <th>Compliance %</th>
                    <th>Status</th>
                </tr>
        """
        
        for standard, assessment in report['standards'].items():
            status_class = assessment['status'].replace('_', '-')
            html += f"""
                <tr>
                    <td>{standard}</td>
                    <td>{assessment['compliance_percentage']:.1f}%</td>
                    <td class="{status_class}">{assessment['status']}</td>
                </tr>
            """
        
        html += """
            </table>
        </body>
        </html>
        """
        
        return html
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        cache_hit_rate = 0
        if self.stats['cache_hits'] + self.stats['cache_misses'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / (
                self.stats['cache_hits'] + self.stats['cache_misses']
            )
        
        return {
            'assessments_run': self.stats['assessments_run'],
            'controls_evaluated': self.stats['controls_evaluated'],
            'avg_assessment_time_ms': self.stats['avg_assessment_time'],
            'cache_hit_rate': cache_hit_rate,
            'cached_standards': len(self.control_cache)
        }
    
    def clear_cache(self):
        """Clear all caches"""
        self.cache.invalidate()
        self.control_cache.clear()
        self.compliance_matrix.clear()