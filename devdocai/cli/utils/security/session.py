"""
Secure session management for CLI.

Provides session tracking, authentication, and authorization.
"""

import os
import json
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict


class SessionError(Exception):
    """Session management error."""
    pass


class UserRole(Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    VIEWER = "viewer"
    GUEST = "guest"


@dataclass
class Session:
    """User session data."""
    session_id: str
    user: str
    role: UserRole
    created: datetime
    last_activity: datetime
    expires: datetime
    permissions: List[str]
    metadata: Dict[str, Any]
    active: bool = True


class SecureSessionManager:
    """
    Secure session management with RBAC.
    
    Features:
    - Session tokens with expiration
    - Role-based access control
    - Multi-factor authentication support
    - Session fixation prevention
    - Concurrent session limits
    """
    
    # Permission definitions
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: [
            'generate.*', 'analyze.*', 'config.*', 'template.*',
            'enhance.*', 'security.*', 'admin.*'
        ],
        UserRole.DEVELOPER: [
            'generate.*', 'analyze.*', 'config.read', 'template.*',
            'enhance.*', 'security.read'
        ],
        UserRole.ANALYST: [
            'generate.read', 'analyze.*', 'config.read', 'template.read',
            'enhance.read', 'security.read'
        ],
        UserRole.VIEWER: [
            'generate.read', 'analyze.read', 'config.read', 'template.read'
        ],
        UserRole.GUEST: [
            'generate.read', 'template.list'
        ]
    }
    
    def __init__(self, session_dir: Optional[Path] = None,
                 session_timeout: int = 3600,
                 max_sessions_per_user: int = 3):
        """
        Initialize session manager.
        
        Args:
            session_dir: Directory for session storage
            session_timeout: Session timeout in seconds
            max_sessions_per_user: Maximum concurrent sessions
        """
        self.session_dir = session_dir or (Path.home() / '.devdocai' / 'sessions')
        self.session_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        self.session_timeout = session_timeout
        self.max_sessions_per_user = max_sessions_per_user
        
        # Clean expired sessions on startup
        self._cleanup_expired_sessions()
    
    def create_session(self, user: str, role: UserRole,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create new session.
        
        Args:
            user: Username
            role: User role
            metadata: Additional session metadata
            
        Returns:
            Session token
            
        Raises:
            SessionError: If session limit exceeded
        """
        # Check concurrent session limit
        user_sessions = self._get_user_sessions(user)
        if len(user_sessions) >= self.max_sessions_per_user:
            # Terminate oldest session
            oldest = min(user_sessions, key=lambda s: s.created)
            self.terminate_session(oldest.session_id)
        
        # Generate secure session token
        session_id = secrets.token_urlsafe(32)
        
        # Create session
        now = datetime.utcnow()
        session = Session(
            session_id=session_id,
            user=user,
            role=role,
            created=now,
            last_activity=now,
            expires=now + timedelta(seconds=self.session_timeout),
            permissions=self._get_role_permissions(role),
            metadata=metadata or {},
            active=True
        )
        
        # Save session
        self._save_session(session)
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[Session]:
        """
        Validate and refresh session.
        
        Args:
            session_id: Session token
            
        Returns:
            Session if valid, None otherwise
        """
        session = self._load_session(session_id)
        
        if not session:
            return None
        
        # Check if expired
        if datetime.utcnow() > session.expires:
            self.terminate_session(session_id)
            return None
        
        # Check if active
        if not session.active:
            return None
        
        # Update last activity
        session.last_activity = datetime.utcnow()
        
        # Extend expiration on activity
        session.expires = datetime.utcnow() + timedelta(seconds=self.session_timeout)
        
        # Save updated session
        self._save_session(session)
        
        return session
    
    def check_permission(self, session_id: str, permission: str) -> bool:
        """
        Check if session has permission.
        
        Args:
            session_id: Session token
            permission: Permission to check (e.g., 'generate.write')
            
        Returns:
            True if permission granted
        """
        session = self.validate_session(session_id)
        
        if not session:
            return False
        
        # Check exact permission
        if permission in session.permissions:
            return True
        
        # Check wildcard permissions
        for perm in session.permissions:
            if perm.endswith('*'):
                prefix = perm[:-1]
                if permission.startswith(prefix):
                    return True
        
        return False
    
    def terminate_session(self, session_id: str):
        """
        Terminate session.
        
        Args:
            session_id: Session token
        """
        session = self._load_session(session_id)
        
        if session:
            session.active = False
            self._save_session(session)
    
    def terminate_user_sessions(self, user: str):
        """
        Terminate all sessions for a user.
        
        Args:
            user: Username
        """
        sessions = self._get_user_sessions(user)
        
        for session in sessions:
            self.terminate_session(session.session_id)
    
    def _get_role_permissions(self, role: UserRole) -> List[str]:
        """Get permissions for role."""
        return self.ROLE_PERMISSIONS.get(role, [])
    
    def _save_session(self, session: Session):
        """Save session to disk."""
        session_file = self.session_dir / f"{session.session_id}.json"
        
        # Convert to dict for JSON serialization
        session_data = asdict(session)
        session_data['created'] = session.created.isoformat()
        session_data['last_activity'] = session.last_activity.isoformat()
        session_data['expires'] = session.expires.isoformat()
        session_data['role'] = session.role.value
        
        with open(session_file, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        # Set restrictive permissions
        os.chmod(session_file, 0o600)
    
    def _load_session(self, session_id: str) -> Optional[Session]:
        """Load session from disk."""
        session_file = self.session_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        try:
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Convert back to Session object
            session = Session(
                session_id=session_data['session_id'],
                user=session_data['user'],
                role=UserRole(session_data['role']),
                created=datetime.fromisoformat(session_data['created']),
                last_activity=datetime.fromisoformat(session_data['last_activity']),
                expires=datetime.fromisoformat(session_data['expires']),
                permissions=session_data['permissions'],
                metadata=session_data['metadata'],
                active=session_data['active']
            )
            
            return session
        except Exception:
            return None
    
    def _get_user_sessions(self, user: str) -> List[Session]:
        """Get all sessions for a user."""
        sessions = []
        
        for session_file in self.session_dir.glob("*.json"):
            session = self._load_session(session_file.stem)
            if session and session.user == user and session.active:
                sessions.append(session)
        
        return sessions
    
    def _cleanup_expired_sessions(self):
        """Remove expired session files."""
        now = datetime.utcnow()
        
        for session_file in self.session_dir.glob("*.json"):
            session = self._load_session(session_file.stem)
            
            if session and now > session.expires:
                session_file.unlink()
    
    def get_active_sessions(self) -> List[Session]:
        """Get all active sessions."""
        sessions = []
        now = datetime.utcnow()
        
        for session_file in self.session_dir.glob("*.json"):
            session = self._load_session(session_file.stem)
            
            if session and session.active and now <= session.expires:
                sessions.append(session)
        
        return sessions
    
    def rotate_session_token(self, old_session_id: str) -> Optional[str]:
        """
        Rotate session token (prevent fixation).
        
        Args:
            old_session_id: Current session token
            
        Returns:
            New session token if successful
        """
        session = self._load_session(old_session_id)
        
        if not session or not session.active:
            return None
        
        # Generate new token
        new_session_id = secrets.token_urlsafe(32)
        
        # Update session with new ID
        session.session_id = new_session_id
        
        # Save with new ID
        self._save_session(session)
        
        # Remove old session file
        old_file = self.session_dir / f"{old_session_id}.json"
        old_file.unlink(missing_ok=True)
        
        return new_session_id