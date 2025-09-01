"""
Threat Intelligence Engine for M010 Security Module
Integrates with threat feeds, implements correlation, and provides threat hunting capabilities.
"""

import json
import re
import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import threading
import logging
from collections import defaultdict, deque
import yara
import requests
from urllib.parse import urlparse
import numpy as np
from sklearn.ensemble import IsolationForest
import pickle

logger = logging.getLogger(__name__)


class ThreatSeverity(Enum):
    """Threat severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ThreatType(Enum):
    """Types of threats."""
    MALWARE = "malware"
    PHISHING = "phishing"
    VULNERABILITY = "vulnerability"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"
    DATA_EXFILTRATION = "data_exfiltration"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DENIAL_OF_SERVICE = "dos"
    SUPPLY_CHAIN = "supply_chain"


@dataclass
class ThreatIndicator:
    """Represents a threat indicator from intelligence feeds."""
    indicator_id: str
    type: str  # IP, domain, hash, URL, email, etc.
    value: str
    severity: ThreatSeverity
    confidence: float
    source: str
    first_seen: datetime
    last_seen: datetime
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThreatEvent:
    """Represents a detected threat event."""
    event_id: str
    timestamp: datetime
    threat_type: ThreatType
    severity: ThreatSeverity
    confidence: float
    indicators: List[ThreatIndicator]
    affected_resources: List[str]
    description: str
    recommended_actions: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class ThreatIntelligenceEngine:
    """
    Advanced threat intelligence engine with feed integration and correlation.
    
    Features:
    - MISP and OTX format support
    - Real-time threat correlation
    - Behavioral anomaly detection
    - YARA rule-based threat hunting
    - Statistical anomaly detection
    """
    
    def __init__(self, feeds_config: Optional[Dict[str, Any]] = None):
        """Initialize the threat intelligence engine."""
        self.feeds_config = feeds_config or {}
        
        # Threat intelligence storage
        self._indicators: Dict[str, ThreatIndicator] = {}
        self._indicator_index: Dict[str, Set[str]] = defaultdict(set)
        self._events: deque = deque(maxlen=10000)
        
        # YARA rules
        self._yara_rules: Optional[yara.Rules] = None
        self._yara_rules_path = Path.home() / '.devdocai' / 'yara_rules'
        self._yara_rules_path.mkdir(parents=True, exist_ok=True)
        
        # Anomaly detection models
        self._anomaly_detector: Optional[IsolationForest] = None
        self._behavior_baselines: Dict[str, Any] = {}
        
        # Correlation engine
        self._correlation_rules: List[Dict[str, Any]] = []
        self._correlation_window = timedelta(minutes=5)
        
        # Performance optimization
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Circuit breaker for external feeds
        self._circuit_breaker = {
            'failures': 0,
            'last_failure': None,
            'is_open': False,
            'threshold': 5,
            'timeout': 60
        }
        
        # Initialize components
        self._initialize_yara_rules()
        self._initialize_anomaly_detection()
        self._load_correlation_rules()
    
    def _initialize_yara_rules(self):
        """Initialize YARA rules for threat hunting."""
        try:
            # Default YARA rules for common threats
            default_rules = """
            rule SuspiciousBase64
            {
                meta:
                    description = "Detects suspicious base64 encoded content"
                    severity = "medium"
                strings:
                    $a = /[A-Za-z0-9+\\/]{100,}={0,2}/
                condition:
                    $a
            }
            
            rule PotentialSQLInjection
            {
                meta:
                    description = "Detects potential SQL injection attempts"
                    severity = "high"
                strings:
                    $a = /(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b.*\bwhere\b)/i
                    $b = /(\bdrop\b.*\btable\b|\bdelete\b.*\bfrom\b)/i
                    $c = "1=1" nocase
                    $d = "' or '" nocase
                condition:
                    any of them
            }
            
            rule SuspiciousCommandExecution
            {
                meta:
                    description = "Detects suspicious command execution patterns"
                    severity = "critical"
                strings:
                    $a = /\b(eval|exec|system|passthru|shell_exec)\s*\(/
                    $b = /\$\(.*\)|`.*`/
                    $c = "cmd.exe" nocase
                    $d = "/bin/sh" nocase
                condition:
                    any of them
            }
            
            rule CryptoMinerSignature
            {
                meta:
                    description = "Detects cryptocurrency mining patterns"
                    severity = "high"
                strings:
                    $a = "stratum+tcp://"
                    $b = "monero" nocase
                    $c = "xmrig" nocase
                    $d = /\b(cryptonight|randomx|kawpow)\b/i
                condition:
                    any of them
            }
            """
            
            # Save default rules
            rules_file = self._yara_rules_path / 'default.yar'
            rules_file.write_text(default_rules)
            
            # Compile rules
            self._yara_rules = yara.compile(filepath=str(rules_file))
            logger.info("YARA rules initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize YARA rules: {e}")
    
    def _initialize_anomaly_detection(self):
        """Initialize anomaly detection models."""
        try:
            # Initialize Isolation Forest for anomaly detection
            self._anomaly_detector = IsolationForest(
                n_estimators=100,
                contamination=0.1,
                random_state=42
            )
            
            # Load or create baseline model
            model_path = Path.home() / '.devdocai' / 'anomaly_model.pkl'
            if model_path.exists():
                with open(model_path, 'rb') as f:
                    self._anomaly_detector = pickle.load(f)
            
            logger.info("Anomaly detection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize anomaly detection: {e}")
    
    def _load_correlation_rules(self):
        """Load threat correlation rules."""
        # Default correlation rules
        self._correlation_rules = [
            {
                'name': 'Brute Force Attack',
                'conditions': [
                    {'type': 'count', 'field': 'failed_login', 'threshold': 5, 'window': 60},
                    {'type': 'unique', 'field': 'source_ip', 'value': 1}
                ],
                'severity': ThreatSeverity.HIGH,
                'threat_type': ThreatType.UNAUTHORIZED_ACCESS
            },
            {
                'name': 'Data Exfiltration',
                'conditions': [
                    {'type': 'sum', 'field': 'bytes_out', 'threshold': 1000000000, 'window': 300},
                    {'type': 'pattern', 'field': 'destination', 'pattern': 'external'}
                ],
                'severity': ThreatSeverity.CRITICAL,
                'threat_type': ThreatType.DATA_EXFILTRATION
            },
            {
                'name': 'Suspicious Process Chain',
                'conditions': [
                    {'type': 'sequence', 'events': ['cmd.exe', 'powershell.exe', 'net.exe']},
                    {'type': 'timeframe', 'window': 30}
                ],
                'severity': ThreatSeverity.HIGH,
                'threat_type': ThreatType.SUSPICIOUS_BEHAVIOR
            }
        ]
    
    async def fetch_threat_feed(self, feed_url: str, feed_type: str = 'misp') -> List[ThreatIndicator]:
        """
        Fetch threat indicators from external feeds.
        
        Args:
            feed_url: URL of the threat feed
            feed_type: Type of feed (misp, otx, custom)
        
        Returns:
            List of threat indicators
        """
        # Check circuit breaker
        if self._is_circuit_open():
            logger.warning("Circuit breaker is open, skipping feed fetch")
            return []
        
        indicators = []
        try:
            # Fetch feed data with timeout
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(feed_url, timeout=10)
            )
            response.raise_for_status()
            
            data = response.json()
            
            if feed_type == 'misp':
                indicators = self._parse_misp_feed(data)
            elif feed_type == 'otx':
                indicators = self._parse_otx_feed(data)
            else:
                indicators = self._parse_custom_feed(data)
            
            # Reset circuit breaker on success
            self._reset_circuit_breaker()
            
            logger.info(f"Fetched {len(indicators)} indicators from {feed_url}")
        except Exception as e:
            logger.error(f"Failed to fetch threat feed: {e}")
            self._record_circuit_failure()
        
        return indicators
    
    def _parse_misp_feed(self, data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Parse MISP format threat feed."""
        indicators = []
        
        for event in data.get('response', []):
            for attribute in event.get('Event', {}).get('Attribute', []):
                indicator = ThreatIndicator(
                    indicator_id=attribute.get('uuid', ''),
                    type=attribute.get('type', ''),
                    value=attribute.get('value', ''),
                    severity=self._map_severity(attribute.get('threat_level_id', 3)),
                    confidence=float(attribute.get('confidence', 50)) / 100,
                    source='MISP',
                    first_seen=datetime.fromisoformat(attribute.get('first_seen', '')),
                    last_seen=datetime.fromisoformat(attribute.get('last_seen', '')),
                    tags=[tag.get('name') for tag in attribute.get('Tag', [])],
                    metadata=attribute.get('meta', {})
                )
                indicators.append(indicator)
        
        return indicators
    
    def _parse_otx_feed(self, data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Parse AlienVault OTX format threat feed."""
        indicators = []
        
        for pulse in data.get('results', []):
            for indicator in pulse.get('indicators', []):
                ind = ThreatIndicator(
                    indicator_id=indicator.get('id', ''),
                    type=indicator.get('type', ''),
                    value=indicator.get('indicator', ''),
                    severity=self._map_otx_severity(pulse.get('severity', 'medium')),
                    confidence=0.7,  # Default confidence for OTX
                    source='OTX',
                    first_seen=datetime.fromisoformat(indicator.get('created', '')),
                    last_seen=datetime.fromisoformat(indicator.get('modified', '')),
                    tags=pulse.get('tags', []),
                    metadata={'pulse_id': pulse.get('id')}
                )
                indicators.append(ind)
        
        return indicators
    
    def _parse_custom_feed(self, data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Parse custom format threat feed."""
        # Implement custom parsing logic
        return []
    
    def _map_severity(self, level: int) -> ThreatSeverity:
        """Map threat level to severity enum."""
        mapping = {
            1: ThreatSeverity.CRITICAL,
            2: ThreatSeverity.HIGH,
            3: ThreatSeverity.MEDIUM,
            4: ThreatSeverity.LOW,
            5: ThreatSeverity.INFO
        }
        return mapping.get(level, ThreatSeverity.MEDIUM)
    
    def _map_otx_severity(self, severity: str) -> ThreatSeverity:
        """Map OTX severity to enum."""
        mapping = {
            'critical': ThreatSeverity.CRITICAL,
            'high': ThreatSeverity.HIGH,
            'medium': ThreatSeverity.MEDIUM,
            'low': ThreatSeverity.LOW,
            'info': ThreatSeverity.INFO
        }
        return mapping.get(severity.lower(), ThreatSeverity.MEDIUM)
    
    def add_indicator(self, indicator: ThreatIndicator):
        """Add a threat indicator to the engine."""
        with self._lock:
            self._indicators[indicator.indicator_id] = indicator
            self._indicator_index[indicator.type].add(indicator.indicator_id)
            self._indicator_index[indicator.value].add(indicator.indicator_id)
            
            # Clear cache
            self._cache.clear()
    
    def check_indicator(self, value: str) -> Optional[ThreatIndicator]:
        """Check if a value matches any threat indicator."""
        with self._lock:
            # Check cache
            if value in self._cache:
                cache_entry = self._cache[value]
                if datetime.utcnow().timestamp() - cache_entry['timestamp'] < self._cache_ttl:
                    return cache_entry['result']
            
            # Search indicators
            indicator_ids = self._indicator_index.get(value, set())
            if indicator_ids:
                indicator = self._indicators.get(next(iter(indicator_ids)))
                # Cache result
                self._cache[value] = {
                    'result': indicator,
                    'timestamp': datetime.utcnow().timestamp()
                }
                return indicator
            
            return None
    
    def hunt_threats(self, data: str) -> List[Dict[str, Any]]:
        """
        Hunt for threats using YARA rules.
        
        Args:
            data: Data to scan
        
        Returns:
            List of matched threats
        """
        if not self._yara_rules:
            return []
        
        matches = []
        try:
            yara_matches = self._yara_rules.match(data=data)
            
            for match in yara_matches:
                threat = {
                    'rule': match.rule,
                    'severity': match.meta.get('severity', 'medium'),
                    'description': match.meta.get('description', ''),
                    'strings': [
                        {
                            'offset': s[0],
                            'identifier': s[1],
                            'data': s[2].decode('utf-8', errors='ignore') if isinstance(s[2], bytes) else s[2]
                        }
                        for s in match.strings
                    ],
                    'tags': match.tags
                }
                matches.append(threat)
        except Exception as e:
            logger.error(f"YARA scanning failed: {e}")
        
        return matches
    
    def detect_anomalies(self, features: List[float]) -> Tuple[bool, float]:
        """
        Detect anomalies using machine learning.
        
        Args:
            features: Feature vector for analysis
        
        Returns:
            Tuple of (is_anomaly, anomaly_score)
        """
        if not self._anomaly_detector:
            return False, 0.0
        
        try:
            # Reshape features
            X = np.array(features).reshape(1, -1)
            
            # Predict anomaly
            prediction = self._anomaly_detector.predict(X)[0]
            score = self._anomaly_detector.score_samples(X)[0]
            
            # -1 indicates anomaly in IsolationForest
            is_anomaly = prediction == -1
            
            # Normalize score to 0-1 range
            anomaly_score = max(0, min(1, -score))
            
            return is_anomaly, anomaly_score
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return False, 0.0
    
    def correlate_events(self, events: List[Dict[str, Any]]) -> List[ThreatEvent]:
        """
        Correlate security events to identify complex threats.
        
        Args:
            events: List of security events
        
        Returns:
            List of correlated threat events
        """
        threat_events = []
        
        for rule in self._correlation_rules:
            if self._evaluate_correlation_rule(rule, events):
                threat_event = ThreatEvent(
                    event_id=hashlib.sha256(
                        f"{rule['name']}{datetime.utcnow()}".encode()
                    ).hexdigest()[:16],
                    timestamp=datetime.utcnow(),
                    threat_type=rule['threat_type'],
                    severity=rule['severity'],
                    confidence=0.8,
                    indicators=[],
                    affected_resources=self._extract_resources(events),
                    description=f"Detected: {rule['name']}",
                    recommended_actions=self._get_recommended_actions(rule['threat_type']),
                    metadata={'rule': rule['name'], 'events': len(events)}
                )
                threat_events.append(threat_event)
        
        return threat_events
    
    def _evaluate_correlation_rule(
        self, 
        rule: Dict[str, Any], 
        events: List[Dict[str, Any]]
    ) -> bool:
        """Evaluate if events match a correlation rule."""
        for condition in rule['conditions']:
            if condition['type'] == 'count':
                count = sum(1 for e in events if e.get(condition['field']))
                if count < condition['threshold']:
                    return False
            
            elif condition['type'] == 'unique':
                unique_values = set(e.get(condition['field']) for e in events if e.get(condition['field']))
                if len(unique_values) != condition['value']:
                    return False
            
            elif condition['type'] == 'sum':
                total = sum(e.get(condition['field'], 0) for e in events)
                if total < condition['threshold']:
                    return False
            
            elif condition['type'] == 'pattern':
                if not any(condition['pattern'] in str(e.get(condition['field'], '')) for e in events):
                    return False
            
            elif condition['type'] == 'sequence':
                # Check for sequence of events
                sequence = condition['events']
                event_types = [e.get('type') for e in events]
                
                # Simple sequence matching
                for i in range(len(event_types) - len(sequence) + 1):
                    if event_types[i:i+len(sequence)] == sequence:
                        return True
                return False
        
        return True
    
    def _extract_resources(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract affected resources from events."""
        resources = set()
        for event in events:
            if 'resource' in event:
                resources.add(event['resource'])
            if 'target' in event:
                resources.add(event['target'])
            if 'file' in event:
                resources.add(event['file'])
        return list(resources)
    
    def _get_recommended_actions(self, threat_type: ThreatType) -> List[str]:
        """Get recommended actions for a threat type."""
        actions = {
            ThreatType.MALWARE: [
                "Isolate affected system",
                "Run full antivirus scan",
                "Check for persistence mechanisms",
                "Review system logs"
            ],
            ThreatType.UNAUTHORIZED_ACCESS: [
                "Reset affected credentials",
                "Review access logs",
                "Enable MFA",
                "Check for privilege escalation"
            ],
            ThreatType.DATA_EXFILTRATION: [
                "Block suspicious connections",
                "Review data access logs",
                "Check for data staging",
                "Implement DLP policies"
            ],
            ThreatType.SUSPICIOUS_BEHAVIOR: [
                "Monitor process activity",
                "Review command history",
                "Check scheduled tasks",
                "Analyze network connections"
            ]
        }
        return actions.get(threat_type, ["Investigate and monitor"])
    
    def update_model(self, training_data: List[List[float]], labels: List[int]):
        """Update the anomaly detection model with new training data."""
        try:
            # Retrain model
            X = np.array(training_data)
            self._anomaly_detector.fit(X)
            
            # Save model
            model_path = Path.home() / '.devdocai' / 'anomaly_model.pkl'
            with open(model_path, 'wb') as f:
                pickle.dump(self._anomaly_detector, f)
            
            logger.info("Anomaly detection model updated successfully")
        except Exception as e:
            logger.error(f"Failed to update model: {e}")
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        cb = self._circuit_breaker
        if cb['is_open']:
            if cb['last_failure']:
                elapsed = (datetime.utcnow() - cb['last_failure']).total_seconds()
                if elapsed > cb['timeout']:
                    # Try to close circuit
                    cb['is_open'] = False
                    cb['failures'] = 0
                    return False
            return True
        return False
    
    def _record_circuit_failure(self):
        """Record a circuit breaker failure."""
        cb = self._circuit_breaker
        cb['failures'] += 1
        cb['last_failure'] = datetime.utcnow()
        
        if cb['failures'] >= cb['threshold']:
            cb['is_open'] = True
            logger.warning("Circuit breaker opened due to repeated failures")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker after success."""
        cb = self._circuit_breaker
        cb['failures'] = 0
        cb['is_open'] = False
        cb['last_failure'] = None
    
    def get_threat_statistics(self) -> Dict[str, Any]:
        """Get threat intelligence statistics."""
        with self._lock:
            severity_counts = defaultdict(int)
            type_counts = defaultdict(int)
            
            for indicator in self._indicators.values():
                severity_counts[indicator.severity.value] += 1
                type_counts[indicator.type] += 1
            
            return {
                'total_indicators': len(self._indicators),
                'total_events': len(self._events),
                'severity_distribution': dict(severity_counts),
                'type_distribution': dict(type_counts),
                'cache_size': len(self._cache),
                'circuit_breaker_status': 'open' if self._circuit_breaker['is_open'] else 'closed'
            }