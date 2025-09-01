"""
Security Orchestration, Automation and Response (SOAR) for M010 Security Module
Implements automated incident response, security playbooks, and tool integration.
"""

import json
import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import threading
import logging
from collections import defaultdict, deque
import yaml
import uuid

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


class IncidentStatus(Enum):
    """Incident lifecycle status."""
    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    CONTAINED = "contained"
    REMEDIATED = "remediated"
    CLOSED = "closed"


class PlaybookStatus(Enum):
    """Playbook execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class SecurityIncident:
    """Represents a security incident."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    
    # Incident details
    incident_type: str
    affected_assets: List[str]
    indicators: List[Dict[str, Any]]
    
    # Response tracking
    assigned_to: Optional[str] = None
    playbook_id: Optional[str] = None
    response_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Timeline
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybookStep:
    """Represents a step in a security playbook."""
    step_id: str
    name: str
    action: str  # Action type (block_ip, isolate_host, send_alert, etc.)
    parameters: Dict[str, Any]
    conditions: List[Dict[str, Any]] = field(default_factory=list)
    on_success: Optional[str] = None  # Next step ID
    on_failure: Optional[str] = None  # Fallback step ID
    timeout: int = 300  # seconds
    retry_count: int = 3
    manual_approval: bool = False


@dataclass
class SecurityPlaybook:
    """Represents an automated security response playbook."""
    playbook_id: str
    name: str
    description: str
    version: str
    
    # Trigger conditions
    triggers: List[Dict[str, Any]]
    
    # Workflow
    steps: List[PlaybookStep]
    entry_point: str  # First step ID
    
    # Configuration
    enabled: bool = True
    priority: int = 5
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SecurityOrchestrator:
    """
    Security Orchestration, Automation and Response (SOAR) system.
    
    Features:
    - Automated incident response workflows
    - Security playbook execution
    - Integration with security tools
    - Incident lifecycle management
    - Response action coordination
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the security orchestrator."""
        self.config = config or {}
        
        # Incident management
        self._incidents: Dict[str, SecurityIncident] = {}
        self._incident_queue: deque = deque()
        
        # Playbook management
        self._playbooks: Dict[str, SecurityPlaybook] = {}
        self._playbook_executions: Dict[str, Dict[str, Any]] = {}
        
        # Action handlers
        self._action_handlers: Dict[str, Callable] = {}
        self._register_default_actions()
        
        # Integration points
        self._integrations: Dict[str, Any] = {}
        
        # Metrics and monitoring
        self._metrics = defaultdict(int)
        self._execution_history: deque = deque(maxlen=1000)
        
        # Async event loop for orchestration
        self._loop = None
        self._tasks: Dict[str, asyncio.Task] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Storage
        self.storage_path = Path.home() / '.devdocai' / 'soar'
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load default playbooks
        self._load_default_playbooks()
    
    def _register_default_actions(self):
        """Register default action handlers."""
        self._action_handlers = {
            'block_ip': self._action_block_ip,
            'isolate_host': self._action_isolate_host,
            'quarantine_file': self._action_quarantine_file,
            'disable_account': self._action_disable_account,
            'send_alert': self._action_send_alert,
            'collect_evidence': self._action_collect_evidence,
            'run_scan': self._action_run_scan,
            'update_firewall': self._action_update_firewall,
            'revoke_access': self._action_revoke_access,
            'create_ticket': self._action_create_ticket,
            'execute_script': self._action_execute_script,
            'wait': self._action_wait,
            'manual_review': self._action_manual_review
        }
    
    def _load_default_playbooks(self):
        """Load default security playbooks."""
        # Malware response playbook
        malware_playbook = SecurityPlaybook(
            playbook_id='playbook_malware_response',
            name='Malware Incident Response',
            description='Automated response to malware detection',
            version='1.0.0',
            triggers=[
                {'type': 'incident_type', 'value': 'malware'},
                {'type': 'severity', 'min': IncidentSeverity.HIGH.value}
            ],
            steps=[
                PlaybookStep(
                    step_id='isolate',
                    name='Isolate Affected Host',
                    action='isolate_host',
                    parameters={'method': 'network'},
                    on_success='collect',
                    on_failure='alert'
                ),
                PlaybookStep(
                    step_id='collect',
                    name='Collect Evidence',
                    action='collect_evidence',
                    parameters={'types': ['memory', 'disk', 'network']},
                    on_success='quarantine',
                    on_failure='alert'
                ),
                PlaybookStep(
                    step_id='quarantine',
                    name='Quarantine Malware',
                    action='quarantine_file',
                    parameters={'action': 'move_to_quarantine'},
                    on_success='scan',
                    on_failure='alert'
                ),
                PlaybookStep(
                    step_id='scan',
                    name='Full System Scan',
                    action='run_scan',
                    parameters={'scan_type': 'full', 'engines': ['av', 'edr']},
                    on_success='remediate',
                    on_failure='alert'
                ),
                PlaybookStep(
                    step_id='remediate',
                    name='Remediate System',
                    action='execute_script',
                    parameters={'script': 'remediate_malware.py'},
                    on_success='verify',
                    on_failure='manual'
                ),
                PlaybookStep(
                    step_id='verify',
                    name='Verify Remediation',
                    action='run_scan',
                    parameters={'scan_type': 'quick'},
                    on_success='restore',
                    on_failure='manual'
                ),
                PlaybookStep(
                    step_id='restore',
                    name='Restore Network Access',
                    action='isolate_host',
                    parameters={'method': 'restore'},
                    on_success='complete',
                    on_failure='manual'
                ),
                PlaybookStep(
                    step_id='alert',
                    name='Send Alert',
                    action='send_alert',
                    parameters={'priority': 'high', 'recipients': ['soc-team']},
                    on_success='manual'
                ),
                PlaybookStep(
                    step_id='manual',
                    name='Manual Review Required',
                    action='manual_review',
                    parameters={'assignee': 'security-analyst'},
                    manual_approval=True
                ),
                PlaybookStep(
                    step_id='complete',
                    name='Complete Incident',
                    action='create_ticket',
                    parameters={'type': 'incident_report'}
                )
            ],
            entry_point='isolate'
        )
        self._playbooks[malware_playbook.playbook_id] = malware_playbook
        
        # Brute force response playbook
        bruteforce_playbook = SecurityPlaybook(
            playbook_id='playbook_bruteforce_response',
            name='Brute Force Attack Response',
            description='Automated response to brute force attacks',
            version='1.0.0',
            triggers=[
                {'type': 'incident_type', 'value': 'brute_force'},
                {'type': 'threshold', 'failed_attempts': 5, 'time_window': 60}
            ],
            steps=[
                PlaybookStep(
                    step_id='block',
                    name='Block Source IP',
                    action='block_ip',
                    parameters={'duration': 3600, 'scope': 'perimeter'},
                    on_success='disable',
                    timeout=60
                ),
                PlaybookStep(
                    step_id='disable',
                    name='Disable Targeted Account',
                    action='disable_account',
                    parameters={'duration': 1800},
                    on_success='notify'
                ),
                PlaybookStep(
                    step_id='notify',
                    name='Notify User',
                    action='send_alert',
                    parameters={'template': 'account_locked', 'channel': 'email'},
                    on_success='investigate'
                ),
                PlaybookStep(
                    step_id='investigate',
                    name='Collect Login Attempts',
                    action='collect_evidence',
                    parameters={'log_types': ['auth', 'access']},
                    on_success='complete'
                ),
                PlaybookStep(
                    step_id='complete',
                    name='Create Incident Report',
                    action='create_ticket',
                    parameters={'type': 'security_incident', 'auto_close': True}
                )
            ],
            entry_point='block'
        )
        self._playbooks[bruteforce_playbook.playbook_id] = bruteforce_playbook
        
        # Data exfiltration response
        exfil_playbook = SecurityPlaybook(
            playbook_id='playbook_data_exfiltration',
            name='Data Exfiltration Response',
            description='Response to potential data exfiltration',
            version='1.0.0',
            triggers=[
                {'type': 'incident_type', 'value': 'data_exfiltration'},
                {'type': 'data_volume', 'threshold_gb': 10}
            ],
            steps=[
                PlaybookStep(
                    step_id='block_transfer',
                    name='Block Data Transfer',
                    action='update_firewall',
                    parameters={'action': 'block_outbound', 'immediate': True},
                    on_success='revoke',
                    retry_count=1
                ),
                PlaybookStep(
                    step_id='revoke',
                    name='Revoke User Access',
                    action='revoke_access',
                    parameters={'scope': 'all_systems'},
                    on_success='preserve'
                ),
                PlaybookStep(
                    step_id='preserve',
                    name='Preserve Evidence',
                    action='collect_evidence',
                    parameters={'priority': 'forensic', 'chain_of_custody': True},
                    on_success='alert',
                    timeout=600
                ),
                PlaybookStep(
                    step_id='alert',
                    name='Executive Alert',
                    action='send_alert',
                    parameters={'recipients': ['ciso', 'legal'], 'priority': 'critical'},
                    on_success='manual'
                ),
                PlaybookStep(
                    step_id='manual',
                    name='Incident Commander Review',
                    action='manual_review',
                    parameters={'role': 'incident_commander'},
                    manual_approval=True
                )
            ],
            entry_point='block_transfer',
            priority=1
        )
        self._playbooks[exfil_playbook.playbook_id] = exfil_playbook
    
    def create_incident(
        self,
        title: str,
        description: str,
        incident_type: str,
        severity: IncidentSeverity,
        affected_assets: List[str],
        indicators: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a new security incident.
        
        Returns:
            Incident ID
        """
        with self._lock:
            incident_id = f"INC-{uuid.uuid4().hex[:8]}"
            
            incident = SecurityIncident(
                incident_id=incident_id,
                title=title,
                description=description,
                severity=severity,
                status=IncidentStatus.NEW,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                incident_type=incident_type,
                affected_assets=affected_assets,
                indicators=indicators or []
            )
            
            # Add to timeline
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'incident_created',
                'details': f"Incident {incident_id} created"
            })
            
            self._incidents[incident_id] = incident
            self._incident_queue.append(incident_id)
            
            # Trigger automatic response
            asyncio.create_task(self._trigger_playbooks(incident))
            
            self._metrics['incidents_created'] += 1
            
            logger.info(f"Created incident {incident_id}: {title}")
            return incident_id
    
    async def _trigger_playbooks(self, incident: SecurityIncident):
        """Trigger applicable playbooks for an incident."""
        triggered = []
        
        for playbook_id, playbook in self._playbooks.items():
            if not playbook.enabled:
                continue
            
            if self._match_triggers(incident, playbook.triggers):
                await self.execute_playbook(playbook_id, incident.incident_id)
                triggered.append(playbook_id)
        
        if triggered:
            logger.info(
                f"Triggered {len(triggered)} playbooks for incident {incident.incident_id}"
            )
    
    def _match_triggers(
        self, 
        incident: SecurityIncident, 
        triggers: List[Dict[str, Any]]
    ) -> bool:
        """Check if incident matches playbook triggers."""
        for trigger in triggers:
            if trigger['type'] == 'incident_type':
                if incident.incident_type != trigger['value']:
                    return False
            
            elif trigger['type'] == 'severity':
                if 'min' in trigger and incident.severity.value > trigger['min']:
                    return False
                if 'max' in trigger and incident.severity.value < trigger['max']:
                    return False
            
            elif trigger['type'] == 'tag':
                if trigger['value'] not in incident.tags:
                    return False
        
        return True
    
    async def execute_playbook(
        self, 
        playbook_id: str, 
        incident_id: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Execute a security playbook for an incident.
        
        Returns:
            Execution ID
        """
        with self._lock:
            if playbook_id not in self._playbooks:
                raise ValueError(f"Playbook {playbook_id} not found")
            
            if incident_id not in self._incidents:
                raise ValueError(f"Incident {incident_id} not found")
            
            playbook = self._playbooks[playbook_id]
            incident = self._incidents[incident_id]
            
            # Create execution context
            execution_id = f"EXEC-{uuid.uuid4().hex[:8]}"
            execution = {
                'execution_id': execution_id,
                'playbook_id': playbook_id,
                'incident_id': incident_id,
                'status': PlaybookStatus.RUNNING,
                'started_at': datetime.utcnow(),
                'current_step': playbook.entry_point,
                'parameters': parameters or {},
                'results': {},
                'errors': []
            }
            
            self._playbook_executions[execution_id] = execution
            
            # Update incident
            incident.playbook_id = playbook_id
            incident.status = IncidentStatus.IN_PROGRESS
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'playbook_started',
                'details': f"Started playbook {playbook.name}"
            })
            
            # Start execution
            task = asyncio.create_task(
                self._execute_playbook_steps(execution_id, playbook, incident)
            )
            self._tasks[execution_id] = task
            
            self._metrics['playbooks_executed'] += 1
            
            logger.info(f"Started playbook execution {execution_id}")
            return execution_id
    
    async def _execute_playbook_steps(
        self,
        execution_id: str,
        playbook: SecurityPlaybook,
        incident: SecurityIncident
    ):
        """Execute playbook steps sequentially."""
        execution = self._playbook_executions[execution_id]
        current_step_id = playbook.entry_point
        
        while current_step_id:
            # Find step
            step = next((s for s in playbook.steps if s.step_id == current_step_id), None)
            if not step:
                execution['errors'].append(f"Step {current_step_id} not found")
                break
            
            # Check conditions
            if not self._evaluate_conditions(step.conditions, incident, execution):
                current_step_id = step.on_failure
                continue
            
            # Check for manual approval
            if step.manual_approval:
                execution['status'] = PlaybookStatus.PAUSED
                await self._wait_for_approval(execution_id, step.step_id)
                execution['status'] = PlaybookStatus.RUNNING
            
            # Execute step
            try:
                result = await self._execute_step(step, incident, execution)
                execution['results'][step.step_id] = result
                
                # Update incident timeline
                incident.timeline.append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'action': f"playbook_step_{step.name}",
                    'result': 'success',
                    'details': result
                })
                
                # Move to next step
                current_step_id = step.on_success
                
            except Exception as e:
                logger.error(f"Step {step.step_id} failed: {e}")
                execution['errors'].append(f"Step {step.step_id}: {str(e)}")
                
                # Retry logic
                if hasattr(step, '_retry_count'):
                    step._retry_count += 1
                else:
                    step._retry_count = 1
                
                if step._retry_count < step.retry_count:
                    await asyncio.sleep(5 * step._retry_count)  # Exponential backoff
                    continue  # Retry same step
                
                # Move to failure step
                current_step_id = step.on_failure
        
        # Complete execution
        execution['status'] = PlaybookStatus.COMPLETED if not execution['errors'] else PlaybookStatus.FAILED
        execution['completed_at'] = datetime.utcnow()
        
        # Update incident status
        if execution['status'] == PlaybookStatus.COMPLETED:
            incident.status = IncidentStatus.REMEDIATED
        
        self._execution_history.append(execution)
        self._metrics['playbooks_completed'] += 1
    
    async def _execute_step(
        self,
        step: PlaybookStep,
        incident: SecurityIncident,
        execution: Dict[str, Any]
    ) -> Any:
        """Execute a single playbook step."""
        if step.action not in self._action_handlers:
            raise ValueError(f"Unknown action: {step.action}")
        
        handler = self._action_handlers[step.action]
        
        # Prepare context
        context = {
            'incident': incident,
            'execution': execution,
            'parameters': step.parameters
        }
        
        # Execute with timeout
        try:
            result = await asyncio.wait_for(
                handler(context),
                timeout=step.timeout
            )
            return result
        except asyncio.TimeoutError:
            raise TimeoutError(f"Step {step.name} timed out after {step.timeout}s")
    
    def _evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        incident: SecurityIncident,
        execution: Dict[str, Any]
    ) -> bool:
        """Evaluate step conditions."""
        if not conditions:
            return True
        
        for condition in conditions:
            # Implement condition evaluation logic
            # This is simplified - expand based on needs
            if condition.get('type') == 'previous_success':
                step_id = condition.get('step_id')
                if step_id not in execution['results']:
                    return False
        
        return True
    
    async def _wait_for_approval(self, execution_id: str, step_id: str):
        """Wait for manual approval."""
        # In production, integrate with ticketing system
        # For now, simulate approval after delay
        await asyncio.sleep(5)
        logger.info(f"Manual approval granted for {execution_id}:{step_id}")
    
    # Action handlers
    async def _action_block_ip(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Block IP address action."""
        params = context['parameters']
        ip = context['incident'].metadata.get('source_ip', params.get('ip'))
        duration = params.get('duration', 3600)
        
        # Simulate firewall update
        logger.info(f"Blocking IP {ip} for {duration} seconds")
        
        return {
            'action': 'block_ip',
            'ip': ip,
            'duration': duration,
            'status': 'success'
        }
    
    async def _action_isolate_host(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Isolate host from network."""
        params = context['parameters']
        hosts = context['incident'].affected_assets
        method = params.get('method', 'network')
        
        results = []
        for host in hosts:
            # Simulate host isolation
            logger.info(f"Isolating host {host} using {method}")
            results.append({'host': host, 'isolated': True})
        
        return {
            'action': 'isolate_host',
            'hosts': results,
            'method': method,
            'status': 'success'
        }
    
    async def _action_quarantine_file(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Quarantine malicious file."""
        params = context['parameters']
        
        # Simulate file quarantine
        logger.info("Quarantining malicious files")
        
        return {
            'action': 'quarantine_file',
            'files_quarantined': len(context['incident'].indicators),
            'status': 'success'
        }
    
    async def _action_disable_account(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Disable user account."""
        params = context['parameters']
        duration = params.get('duration', 1800)
        
        # Simulate account disable
        logger.info(f"Disabling account for {duration} seconds")
        
        return {
            'action': 'disable_account',
            'duration': duration,
            'status': 'success'
        }
    
    async def _action_send_alert(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send alert notification."""
        params = context['parameters']
        recipients = params.get('recipients', ['soc-team'])
        priority = params.get('priority', 'medium')
        
        # Simulate alert
        logger.info(f"Sending {priority} alert to {recipients}")
        
        return {
            'action': 'send_alert',
            'recipients': recipients,
            'priority': priority,
            'status': 'sent'
        }
    
    async def _action_collect_evidence(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect forensic evidence."""
        params = context['parameters']
        types = params.get('types', ['logs'])
        
        # Simulate evidence collection
        evidence = []
        for evidence_type in types:
            logger.info(f"Collecting {evidence_type} evidence")
            evidence.append({
                'type': evidence_type,
                'size': '100MB',
                'hash': hashlib.sha256(f"{evidence_type}".encode()).hexdigest()[:16]
            })
        
        return {
            'action': 'collect_evidence',
            'evidence': evidence,
            'status': 'success'
        }
    
    async def _action_run_scan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run security scan."""
        params = context['parameters']
        scan_type = params.get('scan_type', 'quick')
        
        # Simulate scan
        await asyncio.sleep(2)  # Simulate scan time
        logger.info(f"Running {scan_type} scan")
        
        return {
            'action': 'run_scan',
            'scan_type': scan_type,
            'threats_found': 0,
            'status': 'clean'
        }
    
    async def _action_update_firewall(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update firewall rules."""
        params = context['parameters']
        action = params.get('action', 'block')
        
        # Simulate firewall update
        logger.info(f"Updating firewall: {action}")
        
        return {
            'action': 'update_firewall',
            'rule_action': action,
            'status': 'success'
        }
    
    async def _action_revoke_access(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Revoke user access."""
        params = context['parameters']
        scope = params.get('scope', 'affected_systems')
        
        # Simulate access revocation
        logger.info(f"Revoking access: {scope}")
        
        return {
            'action': 'revoke_access',
            'scope': scope,
            'status': 'success'
        }
    
    async def _action_create_ticket(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create support/incident ticket."""
        params = context['parameters']
        ticket_type = params.get('type', 'incident')
        
        # Simulate ticket creation
        ticket_id = f"TKT-{uuid.uuid4().hex[:8]}"
        logger.info(f"Created {ticket_type} ticket: {ticket_id}")
        
        return {
            'action': 'create_ticket',
            'ticket_id': ticket_id,
            'type': ticket_type,
            'status': 'created'
        }
    
    async def _action_execute_script(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute remediation script."""
        params = context['parameters']
        script = params.get('script', 'default.py')
        
        # Simulate script execution
        await asyncio.sleep(3)
        logger.info(f"Executing script: {script}")
        
        return {
            'action': 'execute_script',
            'script': script,
            'exit_code': 0,
            'status': 'success'
        }
    
    async def _action_wait(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for specified duration."""
        params = context['parameters']
        duration = params.get('duration', 5)
        
        await asyncio.sleep(duration)
        
        return {
            'action': 'wait',
            'duration': duration,
            'status': 'completed'
        }
    
    async def _action_manual_review(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Request manual review."""
        params = context['parameters']
        assignee = params.get('assignee', 'security-analyst')
        
        # Simulate manual review request
        logger.info(f"Manual review requested from {assignee}")
        
        return {
            'action': 'manual_review',
            'assignee': assignee,
            'status': 'pending'
        }
    
    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get incident details."""
        return self._incidents.get(incident_id)
    
    def update_incident_status(
        self, 
        incident_id: str, 
        status: IncidentStatus,
        notes: Optional[str] = None
    ):
        """Update incident status."""
        with self._lock:
            if incident_id not in self._incidents:
                raise ValueError(f"Incident {incident_id} not found")
            
            incident = self._incidents[incident_id]
            incident.status = status
            incident.updated_at = datetime.utcnow()
            
            incident.timeline.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': 'status_update',
                'old_status': incident.status.value,
                'new_status': status.value,
                'notes': notes
            })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get SOAR statistics."""
        with self._lock:
            active_incidents = sum(
                1 for i in self._incidents.values() 
                if i.status not in [IncidentStatus.CLOSED, IncidentStatus.REMEDIATED]
            )
            
            running_playbooks = sum(
                1 for e in self._playbook_executions.values()
                if e['status'] == PlaybookStatus.RUNNING
            )
            
            return {
                'total_incidents': len(self._incidents),
                'active_incidents': active_incidents,
                'total_playbooks': len(self._playbooks),
                'running_executions': running_playbooks,
                'metrics': dict(self._metrics),
                'execution_history_size': len(self._execution_history)
            }